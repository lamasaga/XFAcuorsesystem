"""
========================================
课程班数据导入服务（基于 BaseImporter 统一框架）
========================================

核心字段：
- A-Level 科目名称、教师姓名、课程班名称
- 最大容量、学年、学期、状态
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
from app.modules.course_classes import crud
from app.modules.course_classes.schemas import CourseClassCreate
from app.modules.alevel_subjects.models import AlevelSubject
from app.modules.teachers.models import Teacher


COURSE_CLASS_IMPORT_FIELDS: List[ImportField] = [
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
        key="name",
        header="课程班名称",
        required=True,
        field_type="str",
        max_length=100,
        description="课程班名称（如：数学进阶班）",
        example="数学进阶班",
    ),
    ImportField(
        key="subject_name",
        header="AL科目名称",
        required=True,
        field_type="str",
        max_length=50,
        description="A-Level 科目名称（必须与系统中已存在的科目匹配）",
        example="数学",
    ),
    ImportField(
        key="teacher_name",
        header="教师姓名",
        required=False,
        field_type="str",
        max_length=50,
        description="授课教师姓名",
        example="马昕光",
    ),
    ImportField(
        key="max_capacity",
        header="最大容量",
        required=False,
        field_type="int",
        min_value=1,
        max_value=100,
        default=20,
        description="课程班最大容纳学生数",
        example=20,
    ),
    ImportField(
        key="academic_year",
        header="学年",
        required=False,
        field_type="str",
        max_length=20,
        default="2025-2026",
        description="学年，如 2025-2026",
        example="2025-2026",
    ),
    ImportField(
        key="semester",
        header="学期",
        required=False,
        field_type="enum",
        enum_values=["FALL", "SPRING"],
        enum_display=["秋季", "春季"],
        default="FALL",
        description="学期",
        example="FALL",
    ),
    ImportField(
        key="status",
        header="状态",
        required=False,
        field_type="enum",
        enum_values=["ACTIVE", "CLOSED", "PENDING"],
        enum_display=["进行中", "已关闭", "待定"],
        default="ACTIVE",
        description="课程班状态",
        example="ACTIVE",
    ),
]

importer = BaseImporter(
    fields=COURSE_CLASS_IMPORT_FIELDS,
    sheet_name="课程班导入模板",
    id_field_key="name",
)


def build_template_xlsx() -> bytes:
    return importer.build_template_xlsx()


def build_template_csv() -> str:
    return importer.build_template_csv()


def parse_import_file(filename: str, content: bytes) -> Tuple[List[ImportRow], List[ImportErrorItem]]:
    return importer.parse_file(filename, content)


def import_course_classes_from_rows(db: Session, rows: List[ImportRow]) -> ImportResult:
    result = ImportResult()
    
    subject_map = {s.name: s.id for s in db.query(AlevelSubject).all()}
    teacher_map = {t.name: t.id for t in db.query(Teacher).filter(Teacher.is_deleted == False).all()}
    
    for row in rows:
        if row.action == "SKIP":
            result.skipped += 1
            continue
        
        d = row.data
        name = d.get("name")
        subject_name = d.get("subject_name")
        teacher_name = d.get("teacher_name")
        
        subject_id = subject_map.get(subject_name)
        if not subject_id:
            result.failed += 1
            result.errors.append(ImportErrorItem(
                row_number=row.row_number,
                identifier=name,
                message=f"AL科目不存在: {subject_name}"
            ))
            continue
        
        teacher_id = teacher_map.get(teacher_name) if teacher_name else None
        
        try:
            class_data = CourseClassCreate(
                name=name,
                alevel_subject_id=subject_id,
                teacher_id=teacher_id,
                max_capacity=d.get("max_capacity", 20),
                academic_year=d.get("academic_year", "2025-2026"),
                semester=d.get("semester", "FALL"),
                status=d.get("status", "ACTIVE"),
            )
            crud.create_course_class(db, class_data)
            result.created += 1
        except Exception as e:
            result.failed += 1
            result.errors.append(ImportErrorItem(
                row_number=row.row_number,
                identifier=name,
                message=str(e)
            ))
    
    return result
