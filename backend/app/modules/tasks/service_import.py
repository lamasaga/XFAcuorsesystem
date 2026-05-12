"""
========================================
教学任务数据导入服务（基于 BaseImporter 统一框架）
========================================

核心字段：
- 教师姓名、班级名称、科目名称（作为关联标识）
- 周课时、是否连堂、连堂节数、优先时段、备注
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
from app.modules.tasks import crud
from app.modules.tasks.schemas import TeachingTaskCreate
from app.modules.teachers.models import Teacher
from app.modules.classes.models import Class
from app.modules.subjects.models import Subject


TASK_IMPORT_FIELDS: List[ImportField] = [
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
        key="teacher_name",
        header="教师姓名",
        required=True,
        field_type="str",
        max_length=50,
        description="教师姓名（必须与系统中已存在的教师匹配）",
        example="郭金莉",
    ),
    ImportField(
        key="class_name",
        header="班级名称",
        required=True,
        field_type="str",
        max_length=20,
        description="班级名称（如 IG1-1, NG2-1）",
        example="IG1-1",
    ),
    ImportField(
        key="subject_name",
        header="科目名称",
        required=True,
        field_type="str",
        max_length=50,
        description="科目名称（必须与系统中已存在的科目匹配）",
        example="语文",
    ),
    ImportField(
        key="weekly_hours",
        header="周课时",
        required=False,
        field_type="int",
        min_value=1,
        max_value=10,
        default=2,
        description="每周课时数",
        example=2,
    ),
    ImportField(
        key="is_continuous",
        header="是否连堂",
        required=False,
        field_type="bool",
        default=False,
        description="是否安排连堂课",
        example="否",
    ),
    ImportField(
        key="continuous_count",
        header="连堂节数",
        required=False,
        field_type="int",
        min_value=2,
        max_value=4,
        default=2,
        description="连堂课的节数（仅连堂时有效）",
        example=2,
    ),
    ImportField(
        key="preferred_period",
        header="优先时段",
        required=False,
        field_type="enum",
        enum_values=["MORNING", "AFTERNOON"],
        enum_display=["上午", "下午"],
        description="优先安排的时段",
        example="MORNING",
    ),
    ImportField(
        key="note",
        header="备注",
        required=False,
        field_type="str",
        max_length=200,
        description="备注信息",
        example="",
    ),
]

importer = BaseImporter(
    fields=TASK_IMPORT_FIELDS,
    sheet_name="教学任务导入模板",
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


def import_tasks_from_rows(db: Session, rows: List[ImportRow]) -> ImportResult:
    """
    将解析后的行数据导入数据库
    
    根据教师姓名、班级名称、科目名称查找对应ID，然后创建教学任务。
    """
    result = ImportResult()
    
    # 预加载所有教师、班级、科目映射（名称 -> ID）
    teacher_map = {t.name: t.id for t in db.query(Teacher).filter(Teacher.is_deleted == False).all()}
    class_map = {c.name: c.id for c in db.query(Class).filter(Class.is_deleted == False).all()}
    subject_map = {s.name: s.id for s in db.query(Subject).filter(Subject.is_deleted == False).all()}
    
    for row in rows:
        if row.action == "SKIP":
            result.skipped += 1
            continue
        
        d = row.data
        teacher_name = d.get("teacher_name")
        class_name = d.get("class_name")
        subject_name = d.get("subject_name")
        
        # 查找关联ID
        teacher_id = teacher_map.get(teacher_name)
        class_id = class_map.get(class_name)
        subject_id = subject_map.get(subject_name)
        
        if not teacher_id:
            result.failed += 1
            result.errors.append(ImportErrorItem(
                row_number=row.row_number,
                identifier=f"{teacher_name}/{class_name}/{subject_name}",
                message=f"教师不存在: {teacher_name}"
            ))
            continue
        
        if not class_id:
            result.failed += 1
            result.errors.append(ImportErrorItem(
                row_number=row.row_number,
                identifier=f"{teacher_name}/{class_name}/{subject_name}",
                message=f"班级不存在: {class_name}"
            ))
            continue
        
        if not subject_id:
            result.failed += 1
            result.errors.append(ImportErrorItem(
                row_number=row.row_number,
                identifier=f"{teacher_name}/{class_name}/{subject_name}",
                message=f"科目不存在: {subject_name}"
            ))
            continue
        
        # 检查任务是否已存在
        existing = crud.check_task_exists(db, teacher_id, class_id, subject_id)
        if existing:
            result.skipped += 1
            continue
        
        try:
            task_data = TeachingTaskCreate(
                teacher_id=teacher_id,
                class_id=class_id,
                subject_id=subject_id,
                weekly_hours=d.get("weekly_hours", 2),
                is_continuous=d.get("is_continuous", False),
                continuous_count=d.get("continuous_count", 2),
                preferred_period=d.get("preferred_period"),
                note=d.get("note"),
            )
            crud.create_task(db, task_data)
            result.created += 1
        except Exception as e:
            result.failed += 1
            result.errors.append(ImportErrorItem(
                row_number=row.row_number,
                identifier=f"{teacher_name}/{class_name}/{subject_name}",
                message=str(e)
            ))
    
    return result
