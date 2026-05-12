"""
========================================
学生数据导入服务
========================================

提供学生信息的 Excel/CSV 模板生成与批量导入功能。

核心字段（保持简洁）：
- 姓名、学号、年级、状态
- 行政班名称（通过名称自动匹配班级ID）
"""

from typing import List, Optional, Tuple
from sqlalchemy.orm import Session

from app.core.importer import (
    BaseImporter,
    ImportField,
    ImportRow,
    ImportErrorItem,
    ImportResult,
)
from app.modules.students import crud
from app.modules.students.schemas import StudentCreate, StudentUpdate
from app.modules.classes.models import Class


# ── 字段定义 ───────────────────────────────────────────

STUDENT_IMPORT_FIELDS: List[ImportField] = [
    ImportField(
        key="name",
        header="姓名",
        required=True,
        field_type="str",
        max_length=50,
        description="学生姓名",
        example="张三",
    ),
    ImportField(
        key="student_no",
        header="学号",
        required=True,
        field_type="str",
        max_length=30,
        description="学号（唯一标识）",
        example="AL2025001",
    ),
    ImportField(
        key="grade",
        header="年级",
        required=True,
        field_type="enum",
        enum_values=["G10", "G11", "G12"],
        enum_display=["G10（十年级）", "G11（十一年级）", "G12（十二年级）"],
        description="年级",
        example="G10",
    ),
    ImportField(
        key="class_name",
        header="行政班",
        required=False,
        field_type="str",
        max_length=20,
        description="行政班名称（如 IG3-1），留空则不关联班级",
        example="IG3-1",
    ),
    ImportField(
        key="status",
        header="状态",
        required=False,
        field_type="enum",
        enum_values=["ACTIVE", "INACTIVE", "GRADUATED"],
        enum_display=["在读", "休学", "毕业"],
        default="ACTIVE",
        description="学生状态",
        example="ACTIVE",
    ),
]

# ── 导入器实例 ─────────────────────────────────────────

_student_importer = BaseImporter(
    fields=STUDENT_IMPORT_FIELDS,
    sheet_name="学生导入模板",
    id_field_key="student_no",
)


# ── 模板生成 ───────────────────────────────────────────


def build_template_xlsx() -> bytes:
    """生成学生导入 Excel 模板"""
    return _student_importer.build_template_xlsx()


def build_template_csv() -> bytes:
    """生成学生导入 CSV 模板"""
    return _student_importer.build_template_csv()


# ── 文件解析 ───────────────────────────────────────────


def parse_import_file(filename: str, content: bytes) -> Tuple[List[ImportRow], List[ImportErrorItem]]:
    """解析学生导入文件"""
    return _student_importer.parse_file(filename, content)


def validate_unique_students(rows: List[ImportRow]) -> List[ImportErrorItem]:
    """检查学号重复"""
    return _student_importer.validate_unique_in_file(rows, "student_no")


# ── 批量导入 ───────────────────────────────────────────


def import_students_from_rows(db: Session, rows: List[ImportRow]) -> ImportResult:
    """将解析后的数据批量导入数据库"""
    result = ImportResult()

    # 预加载所有班级名称→ID 映射
    class_map: dict[str, int] = {}
    for cls in db.query(Class).filter(Class.is_deleted == False).all():
        if cls.name:
            class_map[cls.name.strip()] = int(cls.id)

    for r in rows:
        if r.action == "SKIP":
            result.skipped += 1
            continue

        data = dict(r.data)
        student_no = data.get("student_no")
        name = data.get("name")

        # 处理行政班名称 → 班级ID
        class_name = data.pop("class_name", None)
        if class_name:
            matched_id = class_map.get(class_name.strip())
            if matched_id:
                data["class_id"] = matched_id
            else:
                result.failed += 1
                result.errors.append(ImportErrorItem(
                    row_number=r.row_number,
                    identifier=student_no or name,
                    message=f"行政班 '{class_name}' 不存在，请先创建班级"
                ))
                continue

        # 查找已存在的学生（按学号）
        existing = crud.get_student_by_no(db, student_no) if student_no else None

        if existing:
            # 更新（排除空值字段，不覆盖已有数据）
            try:
                update_model = StudentUpdate(**data)
            except Exception as e:
                result.failed += 1
                result.errors.append(ImportErrorItem(
                    row_number=r.row_number,
                    identifier=student_no or name,
                    message=f"数据校验失败：{str(e)}"
                ))
                continue

            # 检查学号是否与其他学生冲突
            if "student_no" in data:
                conflict = crud.get_student_by_no(db, data["student_no"])
                if conflict and conflict.id != existing.id:
                    result.failed += 1
                    result.errors.append(ImportErrorItem(
                        row_number=r.row_number,
                        identifier=student_no,
                        message=f"学号 '{data['student_no']}' 已被其他学生使用"
                    ))
                    continue

            updated = crud.update_student(db, existing.id, update_model)
            if updated:
                result.updated += 1
            else:
                result.failed += 1
                result.errors.append(ImportErrorItem(
                    row_number=r.row_number,
                    identifier=student_no or name,
                    message="更新失败：学生不存在"
                ))
        else:
            # 创建新学生
            try:
                create_model = StudentCreate(**data)
            except Exception as e:
                result.failed += 1
                result.errors.append(ImportErrorItem(
                    row_number=r.row_number,
                    identifier=student_no or name,
                    message=f"数据校验失败：{str(e)}"
                ))
                continue

            try:
                crud.create_student(db, create_model)
                result.created += 1
            except Exception as e:
                result.failed += 1
                result.errors.append(ImportErrorItem(
                    row_number=r.row_number,
                    identifier=student_no or name,
                    message=f"创建失败：{str(e)}"
                ))

    return result
