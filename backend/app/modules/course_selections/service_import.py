"""
========================================
选课数据导入服务（基于 BaseImporter 统一框架）
========================================

核心字段：
- 学生学号、AL科目名称、优先级
- 学年、学期、状态
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
from app.modules.course_selections import crud
from app.modules.course_selections.schemas import CourseSelectionCreate, SelectionItem
from app.modules.students.models import Student
from app.modules.alevel_subjects.models import AlevelSubject


SELECTION_IMPORT_FIELDS: List[ImportField] = [
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
        key="student_no",
        header="学生学号",
        required=True,
        field_type="str",
        max_length=30,
        description="学生学号（唯一标识）",
        example="202501001",
    ),
    ImportField(
        key="subject_name",
        header="AL科目名称",
        required=True,
        field_type="str",
        max_length=50,
        description="A-Level 科目名称",
        example="数学",
    ),
    ImportField(
        key="priority",
        header="优先级",
        required=False,
        field_type="int",
        min_value=1,
        max_value=10,
        default=1,
        description="选课优先级（1-10，数字越小优先级越高）",
        example=1,
    ),
    ImportField(
        key="academic_year",
        header="学年",
        required=False,
        field_type="str",
        max_length=20,
        default="2025-2026",
        description="学年",
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
        enum_values=["DRAFT", "SUBMITTED", "APPROVED", "REJECTED"],
        enum_display=["草稿", "已提交", "已批准", "已拒绝"],
        default="DRAFT",
        description="选课状态",
        example="DRAFT",
    ),
]

importer = BaseImporter(
    fields=SELECTION_IMPORT_FIELDS,
    sheet_name="选课导入模板",
    id_field_key="student_no",
)


def build_template_xlsx() -> bytes:
    return importer.build_template_xlsx()


def build_template_csv() -> str:
    return importer.build_template_csv()


def parse_import_file(filename: str, content: bytes) -> Tuple[List[ImportRow], List[ImportErrorItem]]:
    return importer.parse_file(filename, content)


def import_selections_from_rows(db: Session, rows: List[ImportRow]) -> ImportResult:
    result = ImportResult()
    
    student_map = {s.student_no: s.id for s in db.query(Student).filter(Student.is_deleted == False).all()}
    subject_map = {s.name: s.id for s in db.query(AlevelSubject).all()}
    
    for row in rows:
        if row.action == "SKIP":
            result.skipped += 1
            continue
        
        d = row.data
        student_no = d.get("student_no")
        subject_name = d.get("subject_name")
        
        student_id = student_map.get(student_no)
        if not student_id:
            result.failed += 1
            result.errors.append(ImportErrorItem(
                row_number=row.row_number,
                identifier=student_no,
                message=f"学生不存在: {student_no}"
            ))
            continue
        
        subject_id = subject_map.get(subject_name)
        if not subject_id:
            result.failed += 1
            result.errors.append(ImportErrorItem(
                row_number=row.row_number,
                identifier=student_no,
                message=f"AL科目不存在: {subject_name}"
            ))
            continue
        
        try:
            # 检查该学生是否已有选课记录
            existing_list = crud.get_course_selections(db, student_id=student_id, limit=1)
            existing = existing_list[0] if existing_list else None
            
            selection_item = SelectionItem(
                alevel_subject_id=subject_id,
                priority=d.get("priority", 1)
            )
            
            if existing:
                # 追加到现有记录
                current_selections = existing.selections or []
                current_selections.append(selection_item.model_dump())
                crud.update_course_selection(db, existing.id, {
                    "selections": current_selections
                })
            else:
                # 创建新记录
                selection_data = CourseSelectionCreate(
                    student_id=student_id,
                    academic_year=d.get("academic_year", "2025-2026"),
                    semester=d.get("semester", "FALL"),
                    status=d.get("status", "DRAFT"),
                    selections=[selection_item],
                )
                crud.create_course_selection(db, selection_data)
            
            result.created += 1
        except Exception as e:
            result.failed += 1
            result.errors.append(ImportErrorItem(
                row_number=row.row_number,
                identifier=student_no,
                message=str(e)
            ))
    
    return result
