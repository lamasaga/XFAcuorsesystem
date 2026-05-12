"""
========================================
科目数据导入服务
========================================

提供科目信息的 Excel/CSV 模板生成与批量导入功能。

核心字段（保持简洁）：
- 科目代码（唯一标识）、科目名称
- 分类、是否主科、显示颜色
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
from app.modules.subjects import crud
from app.modules.subjects.schemas import SubjectCreate, SubjectUpdate


# ── 字段定义 ───────────────────────────────────────────

SUBJECT_IMPORT_FIELDS: List[ImportField] = [
    ImportField(
        key="code",
        header="科目代码",
        required=True,
        field_type="str",
        max_length=20,
        description="科目唯一代码，建议用英文大写",
        example="MATH",
    ),
    ImportField(
        key="name",
        header="科目名称",
        required=True,
        field_type="str",
        max_length=50,
        description="科目中文名称",
        example="数学",
    ),
    ImportField(
        key="category",
        header="分类",
        required=False,
        field_type="enum",
        enum_values=["文化课", "艺术", "体育", "综合"],
        default="文化课",
        description="科目分类",
        example="文化课",
    ),
    ImportField(
        key="is_main",
        header="是否主科",
        required=False,
        field_type="bool",
        default=False,
        description="语数英等主科填 是",
        example="否",
    ),
    ImportField(
        key="color",
        header="显示颜色",
        required=False,
        field_type="str",
        max_length=10,
        default="#3b82f6",
        description="十六进制颜色代码，如 #3b82f6",
        example="#3b82f6",
    ),
    ImportField(
        key="applicable_grades",
        header="适用年级",
        required=False,
        field_type="list",
        description="适用年级列表，逗号分隔，如 G1,G2,G3",
        example="G1,G2,G3",
    ),
    ImportField(
        key="applicable_class_types",
        header="适用班型",
        required=False,
        field_type="list",
        description="适用班型，逗号分隔，如 INTERNATIONAL,COMPREHENSIVE",
        example="INTERNATIONAL",
    ),
]

# ── 导入器实例 ─────────────────────────────────────────

_subject_importer = BaseImporter(
    fields=SUBJECT_IMPORT_FIELDS,
    sheet_name="科目导入模板",
    id_field_key="code",
)


# ── 模板生成 ───────────────────────────────────────────


def build_template_xlsx() -> bytes:
    return _subject_importer.build_template_xlsx()


def build_template_csv() -> bytes:
    return _subject_importer.build_template_csv()


# ── 文件解析 ───────────────────────────────────────────


def parse_import_file(filename: str, content: bytes) -> Tuple[List[ImportRow], List[ImportErrorItem]]:
    return _subject_importer.parse_file(filename, content)


def validate_unique_subjects(rows: List[ImportRow]) -> List[ImportErrorItem]:
    return _subject_importer.validate_unique_in_file(rows, "code")


# ── 批量导入 ───────────────────────────────────────────


def import_subjects_from_rows(db: Session, rows: List[ImportRow]) -> ImportResult:
    result = ImportResult()

    for r in rows:
        if r.action == "SKIP":
            result.skipped += 1
            continue

        data = dict(r.data)
        code = data.get("code")
        name = data.get("name")

        existing = crud.get_subject_by_code(db, code) if code else None

        if existing:
            try:
                update_model = SubjectUpdate(**data)
            except Exception as e:
                result.failed += 1
                result.errors.append(ImportErrorItem(
                    row_number=r.row_number,
                    identifier=code or name,
                    message=f"数据校验失败：{str(e)}"
                ))
                continue

            # 检查 code 是否与其他科目冲突
            if "code" in data:
                conflict = crud.get_subject_by_code(db, data["code"])
                if conflict and conflict.id != existing.id:
                    result.failed += 1
                    result.errors.append(ImportErrorItem(
                        row_number=r.row_number,
                        identifier=code,
                        message=f"科目代码 '{data['code']}' 已被使用"
                    ))
                    continue

            updated = crud.update_subject(db, existing.id, update_model)
            if updated:
                result.updated += 1
            else:
                result.failed += 1
                result.errors.append(ImportErrorItem(
                    row_number=r.row_number,
                    identifier=code or name,
                    message="更新失败：科目不存在"
                ))
        else:
            try:
                create_model = SubjectCreate(**data)
            except Exception as e:
                result.failed += 1
                result.errors.append(ImportErrorItem(
                    row_number=r.row_number,
                    identifier=code or name,
                    message=f"数据校验失败：{str(e)}"
                ))
                continue

            try:
                crud.create_subject(db, create_model)
                result.created += 1
            except Exception as e:
                result.failed += 1
                result.errors.append(ImportErrorItem(
                    row_number=r.row_number,
                    identifier=code or name,
                    message=f"创建失败：{str(e)}"
                ))

    return result
