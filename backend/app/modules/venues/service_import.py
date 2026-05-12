"""
========================================
场地数据导入服务
========================================

提供场地资源的 Excel/CSV 模板生成与批量导入功能。

核心字段（保持简洁）：
- 场地名称、容量
- 关联科目、适用年级、备注
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
from app.modules.venues import crud, models, schemas


# ── 字段定义 ───────────────────────────────────────────

VENUE_IMPORT_FIELDS: List[ImportField] = [
    ImportField(
        key="name",
        header="场地名称",
        required=True,
        field_type="str",
        max_length=100,
        description="场地名称，如 体育场、钢琴教室",
        example="体育场",
    ),
    ImportField(
        key="capacity",
        header="容量",
        required=False,
        field_type="int",
        min_value=1,
        max_value=100,
        default=1,
        description="同时能容纳的班级数",
        example=2,
    ),
    ImportField(
        key="subjects",
        header="关联科目",
        required=True,
        field_type="list",
        description="关联科目名称列表，逗号分隔",
        example="体育,轮滑",
    ),
    ImportField(
        key="applicable_grades",
        header="适用年级",
        required=False,
        field_type="list",
        description="适用年级，逗号分隔，留空表示全部适用",
        example="KG,G1,G2",
    ),
    ImportField(
        key="description",
        header="备注",
        required=False,
        field_type="str",
        max_length=500,
        description="场地备注信息",
        example="室外场地，雨天不可用",
    ),
]

# ── 导入器实例 ─────────────────────────────────────────

_venue_importer = BaseImporter(
    fields=VENUE_IMPORT_FIELDS,
    sheet_name="场地导入模板",
    id_field_key="name",
)


# ── 模板生成 ───────────────────────────────────────────


def build_template_xlsx() -> bytes:
    return _venue_importer.build_template_xlsx()


def build_template_csv() -> bytes:
    return _venue_importer.build_template_csv()


# ── 文件解析 ───────────────────────────────────────────


def parse_import_file(filename: str, content: bytes) -> Tuple[List[ImportRow], List[ImportErrorItem]]:
    return _venue_importer.parse_file(filename, content)


def validate_unique_venues(rows: List[ImportRow]) -> List[ImportErrorItem]:
    return _venue_importer.validate_unique_in_file(rows, "name")


# ── 批量导入 ───────────────────────────────────────────


def import_venues_from_rows(db: Session, rows: List[ImportRow]) -> ImportResult:
    result = ImportResult()

    for r in rows:
        if r.action == "SKIP":
            result.skipped += 1
            continue

        data = dict(r.data)
        name = data.get("name")

        # 检查是否已存在同名场地
        existing = db.query(models.Venue).filter(models.Venue.name == name).first()

        if existing:
            try:
                update_model = schemas.VenueUpdate(**data)
            except Exception as e:
                result.failed += 1
                result.errors.append(ImportErrorItem(
                    row_number=r.row_number,
                    identifier=name,
                    message=f"数据校验失败：{str(e)}"
                ))
                continue

            updated = crud.update_venue(db, existing.id, update_model)
            if updated:
                result.updated += 1
            else:
                result.failed += 1
                result.errors.append(ImportErrorItem(
                    row_number=r.row_number,
                    identifier=name,
                    message="更新失败：场地不存在"
                ))
        else:
            try:
                create_model = schemas.VenueCreate(**data)
            except Exception as e:
                result.failed += 1
                result.errors.append(ImportErrorItem(
                    row_number=r.row_number,
                    identifier=name,
                    message=f"数据校验失败：{str(e)}"
                ))
                continue

            try:
                crud.create_venue(db, create_model)
                result.created += 1
            except Exception as e:
                result.failed += 1
                result.errors.append(ImportErrorItem(
                    row_number=r.row_number,
                    identifier=name,
                    message=f"创建失败：{str(e)}"
                ))

    return result
