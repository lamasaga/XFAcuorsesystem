"""
========================================
A-Level 科目数据导入服务
========================================

提供 A-Level 科目信息的 Excel/CSV 模板生成与批量导入功能。

核心字段（保持简洁）：
- 科目名称、考试局、级别
- 每周课时、最大容量
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
from app.modules.alevel_subjects import crud
from app.modules.alevel_subjects.schemas import AlevelSubjectCreate, AlevelSubjectUpdate


# ── 字段定义 ───────────────────────────────────────────

ALEVEL_SUBJECT_IMPORT_FIELDS: List[ImportField] = [
    ImportField(
        key="name",
        header="科目名称",
        required=True,
        field_type="str",
        max_length=100,
        description="A-Level 科目名称",
        example="Physics",
    ),
    ImportField(
        key="exam_board",
        header="考试局",
        required=True,
        field_type="enum",
        enum_values=["CAIE", "Edexcel", "AQA"],
        description="考试局代码",
        example="CAIE",
    ),
    ImportField(
        key="level",
        header="级别",
        required=True,
        field_type="enum",
        enum_values=["AS", "A2"],
        enum_display=["AS（第一年）", "A2（第二年）"],
        description="AS 或 A2",
        example="AS",
    ),
    ImportField(
        key="module_code",
        header="模块代码",
        required=False,
        field_type="str",
        max_length=30,
        description="模块代码，如 9702/12",
        example="9702/12",
    ),
    ImportField(
        key="weekly_hours",
        header="每周课时",
        required=False,
        field_type="int",
        min_value=1,
        max_value=20,
        default=4,
        description="每周课时数",
        example=4,
    ),
    ImportField(
        key="max_students",
        header="最大容量",
        required=False,
        field_type="int",
        min_value=1,
        max_value=100,
        default=20,
        description="该科目最大学生人数",
        example=20,
    ),
    ImportField(
        key="is_active",
        header="是否启用",
        required=False,
        field_type="bool",
        default=True,
        description="是否启用该科目",
        example="是",
    ),
    ImportField(
        key="description",
        header="描述",
        required=False,
        field_type="str",
        max_length=500,
        description="科目描述（可选）",
        example="A-Level Physics - Mechanics",
    ),
]

# ── 导入器实例 ─────────────────────────────────────────

_alevel_importer = BaseImporter(
    fields=ALEVEL_SUBJECT_IMPORT_FIELDS,
    sheet_name="A-Level科目导入模板",
    id_field_key="name",
)


# ── 模板生成 ───────────────────────────────────────────


def build_template_xlsx() -> bytes:
    return _alevel_importer.build_template_xlsx()


def build_template_csv() -> bytes:
    return _alevel_importer.build_template_csv()


# ── 文件解析 ───────────────────────────────────────────


def parse_import_file(filename: str, content: bytes) -> Tuple[List[ImportRow], List[ImportErrorItem]]:
    return _alevel_importer.parse_file(filename, content)


def validate_unique_names(rows: List[ImportRow]) -> List[ImportErrorItem]:
    return _alevel_importer.validate_unique_in_file(rows, "name")


# ── 批量导入 ───────────────────────────────────────────


def import_alevel_subjects_from_rows(db: Session, rows: List[ImportRow]) -> ImportResult:
    result = ImportResult()

    for r in rows:
        if r.action == "SKIP":
            result.skipped += 1
            continue

        data = dict(r.data)
        name = data.get("name")

        # A-Level 科目通过 name + exam_board + level 组合唯一
        # 先检查是否有完全相同的组合
        existing = None
        from app.modules.alevel_subjects.models import AlevelSubject
        existing_query = db.query(AlevelSubject).filter(
            AlevelSubject.is_deleted == False,
            AlevelSubject.name == name
        )
        if data.get("exam_board"):
            existing_query = existing_query.filter(AlevelSubject.exam_board == data["exam_board"])
        if data.get("level"):
            existing_query = existing_query.filter(AlevelSubject.level == data["level"])
        existing = existing_query.first()

        if existing:
            try:
                update_model = AlevelSubjectUpdate(**data)
            except Exception as e:
                result.failed += 1
                result.errors.append(ImportErrorItem(
                    row_number=r.row_number,
                    identifier=name,
                    message=f"数据校验失败：{str(e)}"
                ))
                continue

            updated = crud.update_alevel_subject(db, existing.id, update_model)
            if updated:
                result.updated += 1
            else:
                result.failed += 1
                result.errors.append(ImportErrorItem(
                    row_number=r.row_number,
                    identifier=name,
                    message="更新失败：科目不存在"
                ))
        else:
            try:
                create_model = AlevelSubjectCreate(**data)
            except Exception as e:
                result.failed += 1
                result.errors.append(ImportErrorItem(
                    row_number=r.row_number,
                    identifier=name,
                    message=f"数据校验失败：{str(e)}"
                ))
                continue

            try:
                crud.create_alevel_subject(db, create_model)
                result.created += 1
            except Exception as e:
                result.failed += 1
                result.errors.append(ImportErrorItem(
                    row_number=r.row_number,
                    identifier=name,
                    message=f"创建失败：{str(e)}"
                ))

    return result
