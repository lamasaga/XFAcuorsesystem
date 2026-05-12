"""
========================================
教师数据导入服务（基于 BaseImporter 统一框架）
========================================

提供教师信息的 Excel/CSV 模板生成与批量导入功能。
与 students/classes/subjects/venues 等模块保持一致的体验。

核心字段：
- 姓名、导入标记、教师类型、学部
- 任教科目、标签、每周最大课时、教研组
"""

from typing import List, Optional, Tuple
from sqlalchemy.orm import Session

from app.core.importer import (
    BaseImporter,
    ImportField,
    ImportRow,
    ImportErrorItem,
    ImportResult,
    create_import_response,
)
from app.modules.teachers import crud
from app.modules.teachers.models import ResearchGroup
from app.modules.teachers.schemas import TeacherCreate, TeacherUpdate


# ── 字段定义 ───────────────────────────────────────────

TEACHER_IMPORT_FIELDS: List[ImportField] = [
    ImportField(
        key="action",
        header="导入标记",
        required=False,
        field_type="str",
        default="IMPORT",
        description="IMPORT=导入/更新，SKIP=跳过该行",
        example="IMPORT",
    ),
    ImportField(
        key="name",
        header="姓名",
        required=True,
        field_type="str",
        max_length=50,
        description="教师姓名（唯一标识，重名时请用SKIP标记排除旧记录）",
        example="张三",
    ),
    ImportField(
        key="type",
        header="教师类型",
        required=False,
        field_type="enum",
        enum_values=["CN", "EN"],
        enum_display=["中教", "外教"],
        default="CN",
        description="教师类型",
        example="CN",
    ),
    ImportField(
        key="department",
        header="学部",
        required=False,
        field_type="enum",
        enum_values=["PRIMARY", "SECONDARY", "BOTH"],
        enum_display=["小学部", "中学部", "小中贯通"],
        default="PRIMARY",
        description="所属学部",
        example="PRIMARY",
    ),
    ImportField(
        key="subjects",
        header="任教科目",
        required=False,
        field_type="list",
        description="任教科目列表，多个科目用英文逗号分隔",
        example="语文,数学",
    ),
    ImportField(
        key="tags",
        header="标签",
        required=False,
        field_type="list",
        description="教师标签，多个标签用英文逗号分隔。可用：PRIMARY_ADMIN, SECONDARY_ADMIN, ASSISTANT_HOMEROOM 等",
        example="PRIMARY_ADMIN",
    ),
    ImportField(
        key="max_weekly_hours",
        header="每周最大课时",
        required=False,
        field_type="int",
        min_value=1,
        max_value=40,
        default=25,
        description="每周最大可排课时数",
        example=25,
    ),
    ImportField(
        key="research_group_name",
        header="教研组",
        required=False,
        field_type="str",
        max_length=50,
        description="所属教研组名称（不存在则自动创建）",
        example="数学教研组",
    ),
]

# ── 导入器实例 ─────────────────────────────────────────

_teacher_importer = BaseImporter(
    fields=TEACHER_IMPORT_FIELDS,
    sheet_name="教师导入模板",
    id_field_key="name",
)


# ── 模板生成 ───────────────────────────────────────────


def build_template_xlsx() -> bytes:
    """生成教师导入 Excel 模板（含表头说明、枚举值提示、示例数据）"""
    return _teacher_importer.build_template_xlsx()


def build_template_csv() -> bytes:
    """生成教师导入 CSV 模板"""
    return _teacher_importer.build_template_csv()


# ── 文件解析 ───────────────────────────────────────────


def parse_import_file(filename: str, content: bytes) -> Tuple[List[ImportRow], List[ImportErrorItem]]:
    """解析教师导入文件"""
    return _teacher_importer.parse_file(filename, content)


def validate_duplicate_names(rows: List[ImportRow]) -> List[ImportErrorItem]:
    """
    重名规则：同名出现多行时，必须且只能有 1 行为 IMPORT，其余全部为 SKIP
    """
    errors: List[ImportErrorItem] = []
    by_name: dict[str, List[ImportRow]] = {}
    for r in rows:
        name = r.raw_identifier or r.data.get("name", "")
        by_name.setdefault(name, []).append(r)

    for name, group in by_name.items():
        if len(group) <= 1:
            continue
        import_rows = [r for r in group if r.action == "IMPORT"]
        skip_rows = [r for r in group if r.action == "SKIP"]
        if len(import_rows) == 1 and len(skip_rows) == (len(group) - 1):
            continue
        row_nums = ",".join(str(r.row_number) for r in group)
        errors.append(ImportErrorItem(
            row_number=import_rows[0].row_number if import_rows else group[0].row_number,
            identifier=name,
            message=f"同名教师在文件中出现多行（行 {row_nums}），请将要排除的行标记为 SKIP，只保留 1 行 IMPORT",
        ))
    return errors


# ── 批量导入 ───────────────────────────────────────────


def import_teachers_from_rows(db: Session, rows: List[ImportRow]) -> ImportResult:
    """将解析后的数据批量导入数据库"""
    result = ImportResult()

    for r in rows:
        if r.action == "SKIP":
            result.skipped += 1
            continue

        data = dict(r.data)
        name = data.get("name", r.raw_identifier or "")

        # 处理教研组名称 → 教研组ID
        group_name = data.pop("research_group_name", None)
        if group_name:
            try:
                data["research_group_id"] = _get_or_create_research_group_id(db, group_name)
            except Exception:
                result.failed += 1
                result.errors.append(ImportErrorItem(
                    row_number=r.row_number,
                    identifier=name,
                    message="教研组创建/查询失败",
                ))
                continue

        # 查重：以 name 唯一
        existing = crud.get_teacher_by_name(db, name)

        if existing:
            # 更新（排除空值字段，不覆盖已有数据）
            try:
                update_model = TeacherUpdate(**data)
            except Exception as e:
                result.failed += 1
                result.errors.append(ImportErrorItem(
                    row_number=r.row_number,
                    identifier=name,
                    message=f"数据校验失败：{str(e)}",
                ))
                continue

            updated = crud.update_teacher(db, existing.id, update_model)
            if updated:
                result.updated += 1
            else:
                result.failed += 1
                result.errors.append(ImportErrorItem(
                    row_number=r.row_number,
                    identifier=name,
                    message="更新失败：教师不存在",
                ))
        else:
            # 创建：允许大部分为空，使用默认值
            try:
                create_model = TeacherCreate(name=name, **data)
            except Exception as e:
                result.failed += 1
                result.errors.append(ImportErrorItem(
                    row_number=r.row_number,
                    identifier=name,
                    message=f"数据校验失败：{str(e)}",
                ))
                continue

            try:
                crud.create_teacher(db, create_model)
                result.created += 1
            except Exception as e:
                result.failed += 1
                result.errors.append(ImportErrorItem(
                    row_number=r.row_number,
                    identifier=name,
                    message=f"创建失败：{str(e)}",
                ))

    return result


def _get_or_create_research_group_id(db: Session, group_name: str) -> int:
    """根据名称获取或创建教研组"""
    name = group_name.strip()
    group = (
        db.query(ResearchGroup)
        .filter(ResearchGroup.is_deleted == False, ResearchGroup.name == name)
        .first()
    )
    if group:
        return int(group.id)
    group = ResearchGroup(name=name)
    db.add(group)
    db.commit()
    db.refresh(group)
    return int(group.id)
