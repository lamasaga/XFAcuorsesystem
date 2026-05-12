"""
========================================
班级数据导入服务
========================================

提供班级信息的 Excel/CSV 模板生成与批量导入功能。

核心字段（保持简洁）：
- 班级名称、类型、年级、学部
- 班号（同年级内序号）
- 班主任（通过教师姓名匹配）
"""

from typing import List, Tuple
from sqlalchemy.orm import Session

from app.core.importer import (
    BaseImporter,
    ImportField,
    ImportRow,
    ImportErrorItem,
    ImportResult,
)
from app.modules.classes import crud
from app.modules.classes.schemas import ClassCreate, ClassUpdate
from app.modules.teachers.models import Teacher


# ── 字段定义 ───────────────────────────────────────────

CLASS_IMPORT_FIELDS: List[ImportField] = [
    ImportField(
        key="name",
        header="班级名称",
        required=True,
        field_type="str",
        max_length=20,
        description="班级名称，如 IG3-1、NG2-1",
        example="IG3-1",
    ),
    ImportField(
        key="type",
        header="班级类型",
        required=True,
        field_type="enum",
        enum_values=["I", "N"],
        enum_display=["国际班", "综素班"],
        description="I=国际班，N=综素班",
        example="I",
    ),
    ImportField(
        key="grade",
        header="年级",
        required=True,
        field_type="str",
        max_length=10,
        description="年级代码：PK/KG/G1-G12",
        example="G3",
    ),
    ImportField(
        key="department",
        header="学部",
        required=False,
        field_type="enum",
        enum_values=["PRIMARY", "SECONDARY"],
        enum_display=["小学部", "中学部"],
        default="PRIMARY",
        description="PRIMARY=小学部，SECONDARY=中学部",
        example="PRIMARY",
    ),
    ImportField(
        key="class_no",
        header="班号",
        required=False,
        field_type="int",
        min_value=1,
        max_value=10,
        default=1,
        description="同年级内序号",
        example=1,
    ),
    ImportField(
        key="homeroom_cn_name",
        header="中教班主任",
        required=False,
        field_type="str",
        max_length=50,
        description="中教班主任姓名（通过姓名匹配）",
        example="张三",
    ),
    ImportField(
        key="homeroom_en_name",
        header="外教班主任",
        required=False,
        field_type="str",
        max_length=50,
        description="外教班主任姓名（通过姓名匹配）",
        example="John Smith",
    ),
]

# ── 导入器实例 ─────────────────────────────────────────

_class_importer = BaseImporter(
    fields=CLASS_IMPORT_FIELDS,
    sheet_name="班级导入模板",
    id_field_key="name",
)


# ── 模板生成 ───────────────────────────────────────────


def build_template_xlsx() -> bytes:
    return _class_importer.build_template_xlsx()


def build_template_csv() -> bytes:
    return _class_importer.build_template_csv()


# ── 文件解析 ───────────────────────────────────────────


def parse_import_file(filename: str, content: bytes) -> Tuple[List[ImportRow], List[ImportErrorItem]]:
    return _class_importer.parse_file(filename, content)


def validate_unique_classes(rows: List[ImportRow]) -> List[ImportErrorItem]:
    return _class_importer.validate_unique_in_file(rows, "name")


# ── 批量导入 ───────────────────────────────────────────


def import_classes_from_rows(db: Session, rows: List[ImportRow]) -> ImportResult:
    result = ImportResult()

    # 预加载教师姓名→ID 映射
    teacher_map: dict[str, int] = {}
    for t in db.query(Teacher).filter(Teacher.is_deleted == False).all():
        if t.name:
            teacher_map[t.name.strip()] = int(t.id)

    for r in rows:
        if r.action == "SKIP":
            result.skipped += 1
            continue

        data = dict(r.data)
        name = data.get("name")

        # 处理班主任姓名 → 教师ID
        cn_name = data.pop("homeroom_cn_name", None)
        en_name = data.pop("homeroom_en_name", None)

        if cn_name:
            cn_id = teacher_map.get(cn_name.strip())
            if cn_id:
                data["homeroom_cn_id"] = cn_id
            else:
                result.failed += 1
                result.errors.append(ImportErrorItem(
                    row_number=r.row_number,
                    identifier=name,
                    message=f"中教班主任 '{cn_name}' 不存在，请先创建教师"
                ))
                continue

        if en_name:
            en_id = teacher_map.get(en_name.strip())
            if en_id:
                data["homeroom_en_id"] = en_id
            else:
                result.failed += 1
                result.errors.append(ImportErrorItem(
                    row_number=r.row_number,
                    identifier=name,
                    message=f"外教班主任 '{en_name}' 不存在，请先创建教师"
                ))
                continue

        # 查找已存在的班级（按名称）
        existing = crud.get_class_by_name(db, name) if name else None

        if existing:
            try:
                update_model = ClassUpdate(**data)
            except Exception as e:
                result.failed += 1
                result.errors.append(ImportErrorItem(
                    row_number=r.row_number,
                    identifier=name,
                    message=f"数据校验失败：{str(e)}"
                ))
                continue

            # 检查名称是否与其他班级冲突
            if "name" in data:
                conflict = crud.get_class_by_name(db, data["name"])
                if conflict and conflict.id != existing.id:
                    result.failed += 1
                    result.errors.append(ImportErrorItem(
                        row_number=r.row_number,
                        identifier=name,
                        message=f"班级名称 '{data['name']}' 已被使用"
                    ))
                    continue

            updated = crud.update_class(db, existing.id, update_model)
            if updated:
                result.updated += 1
            else:
                result.failed += 1
                result.errors.append(ImportErrorItem(
                    row_number=r.row_number,
                    identifier=name,
                    message="更新失败：班级不存在"
                ))
        else:
            try:
                create_model = ClassCreate(**data)
            except Exception as e:
                result.failed += 1
                result.errors.append(ImportErrorItem(
                    row_number=r.row_number,
                    identifier=name,
                    message=f"数据校验失败：{str(e)}"
                ))
                continue

            try:
                crud.create_class(db, create_model)
                result.created += 1
            except Exception as e:
                result.failed += 1
                result.errors.append(ImportErrorItem(
                    row_number=r.row_number,
                    identifier=name,
                    message=f"创建失败：{str(e)}"
                ))

    return result
