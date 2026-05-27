"""
========================================
分层/合班课程数据导入服务（基于 BaseImporter 统一框架）
========================================

核心字段：
- 课程类型、科目名称、适用年级、周课时
- 教师姓名列表（分层模式每层一个）、班级名称列表（合班模式）
- 是否连堂、备注
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
from app.modules.layers import crud
from app.modules.layers.schemas import LayerGroupCreate
from app.modules.layers.sync_tasks import sync_layer_tasks
from app.modules.subjects.models import Subject
from app.modules.teachers.models import Teacher
from app.modules.classes.models import Class


LAYER_IMPORT_FIELDS: List[ImportField] = [
    ImportField(
        key="action",
        header="导入标记",
        required=False,
        field_type="str",
        default="IMPORT",
        description="IMPORT=导入，SKIP=跳过该行",
        example="IMPORT",
    ),
    ImportField(
        key="group_type",
        header="课程类型",
        required=False,
        field_type="enum",
        enum_values=["LAYER", "COMBINE"],
        enum_display=["分层", "合班"],
        default="LAYER",
        description="LAYER=同年级内分层上课，COMBINE=多个班级合并上课",
        example="LAYER",
    ),
    ImportField(
        key="subject_name",
        header="科目名称",
        required=True,
        field_type="str",
        max_length=50,
        description="科目名称（必须与系统中已存在的科目匹配）",
        example="数学",
    ),
    ImportField(
        key="layer_scope",
        header="分层类型",
        required=False,
        field_type="enum",
        enum_values=["GRADE", "CROSS_GRADE", "SINGLE_CLASS"],
        enum_display=["同年级分层", "跨年级分层", "单一班级分层"],
        default="GRADE",
        description="仅分层模式；单班分层时班级名称列表只能填一个班",
        example="同年级分层",
    ),
    ImportField(
        key="grades",
        header="适用年级",
        required=True,
        field_type="list",
        description="适用年级列表，多个年级用英文逗号分隔，如 G6,G7,G8",
        example="G6,G7",
    ),
    ImportField(
        key="class_names",
        header="班级名称",
        required=False,
        field_type="list",
        description="合班模式下指定的班级名称列表，多个班级用英文逗号分隔",
        example="IG6-1,IG6-2",
    ),
    ImportField(
        key="layer_count",
        header="分层数量",
        required=False,
        field_type="int",
        min_value=1,
        max_value=10,
        default=2,
        description="分层模式下的分层数量（合班模式固定为1）",
        example=2,
    ),
    ImportField(
        key="teacher_names",
        header="教师姓名",
        required=False,
        field_type="list",
        description="教师姓名列表，多个教师用英文逗号分隔。分层模式：每层一个教师；合班模式：只需一个教师",
        example="马昕光,张红娟",
    ),
    ImportField(
        key="weekly_hours",
        header="周课时",
        required=True,
        field_type="int",
        min_value=1,
        max_value=10,
        description="每周课时数",
        example=2,
    ),
    ImportField(
        key="needs_continuous",
        header="是否连堂",
        required=False,
        field_type="bool",
        default=False,
        description="是否需要安排连堂课",
        example="否",
    ),
    ImportField(
        key="description",
        header="备注",
        required=False,
        field_type="str",
        max_length=200,
        description="备注说明",
        example="",
    ),
]

importer = BaseImporter(
    fields=LAYER_IMPORT_FIELDS,
    sheet_name="分层课程导入模板",
    id_field_key=None,
)


def build_template_xlsx() -> bytes:
    """生成 Excel 导入模板"""
    return importer.build_template_xlsx()


def build_template_csv() -> str:
    """生成 CSV 导入模板"""
    return importer.build_template_csv()


def parse_import_file(filename: str, content: bytes) -> Tuple[List[ImportRow], List[ImportErrorItem]]:
    """解析导入文件"""
    return importer.parse_file(filename, content)


def import_layers_from_rows(db: Session, rows: List[ImportRow]) -> ImportResult:
    """
    将解析后的行数据导入数据库
    
    根据科目名称、教师姓名、班级名称查找对应ID，然后创建分层课程。
    """
    result = ImportResult()
    
    # 预加载所有映射
    subject_map = {s.name: s.id for s in db.query(Subject).filter(Subject.is_deleted == False).all()}
    teacher_map = {t.name: t.id for t in db.query(Teacher).filter(Teacher.is_deleted == False).all()}
    class_map = {c.name: c.id for c in db.query(Class).filter(Class.is_deleted == False).all()}
    
    for row in rows:
        if row.action == "SKIP":
            result.skipped += 1
            continue
        
        d = row.data
        subject_name = d.get("subject_name")
        subject_id = subject_map.get(subject_name)
        
        if not subject_id:
            result.failed += 1
            result.errors.append(ImportErrorItem(
                row_number=row.row_number,
                identifier=subject_name,
                message=f"科目不存在: {subject_name}"
            ))
            continue
        
        # 解析教师ID
        teacher_names = d.get("teacher_names") or []
        teacher_ids = []
        missing_teachers = []
        for name in teacher_names:
            tid = teacher_map.get(name)
            if tid:
                teacher_ids.append(tid)
            else:
                missing_teachers.append(name)
        
        if missing_teachers:
            result.failed += 1
            result.errors.append(ImportErrorItem(
                row_number=row.row_number,
                identifier=subject_name,
                message=f"教师不存在: {', '.join(missing_teachers)}"
            ))
            continue
        
        # 解析班级ID（合班模式）
        class_names = d.get("class_names") or []
        class_ids = []
        missing_classes = []
        for name in class_names:
            cid = class_map.get(name)
            if cid:
                class_ids.append(cid)
            else:
                missing_classes.append(name)
        
        if missing_classes:
            result.failed += 1
            result.errors.append(ImportErrorItem(
                row_number=row.row_number,
                identifier=subject_name,
                message=f"班级不存在: {', '.join(missing_classes)}"
            ))
            continue
        
        grades = d.get("grades") or []
        group_type = d.get("group_type", "LAYER")
        layer_count = d.get("layer_count", 2 if group_type == "LAYER" else 1)
        layer_scope = d.get("layer_scope") or "GRADE"

        if group_type == "LAYER" and layer_scope == "SINGLE_CLASS":
            if len(class_ids) != 1:
                result.failed += 1
                result.errors.append(ImportErrorItem(
                    row_number=row.row_number,
                    identifier=subject_name,
                    message="单一班级分层须在「班级名称」列填写且仅填写一个班级",
                ))
                continue

        try:
            group_data = LayerGroupCreate(
                group_type=group_type,
                subject_id=subject_id,
                grades=grades,
                class_ids=class_ids,
                layer_count=layer_count,
                teacher_ids=teacher_ids,
                layer_scope=layer_scope,
                weekly_hours=d.get("weekly_hours", 2),
                needs_continuous=d.get("needs_continuous", False),
                description=d.get("description"),
            )
            new_group = crud.create_layer_group(db, group_data)
            sync_layer_tasks(db, new_group)
            result.created += 1
        except Exception as e:
            result.failed += 1
            result.errors.append(ImportErrorItem(
                row_number=row.row_number,
                identifier=subject_name,
                message=str(e)
            ))
    
    return result
