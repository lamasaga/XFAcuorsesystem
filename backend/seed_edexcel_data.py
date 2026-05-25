#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
爱德思 A-Level 测试数据导入脚本
================================
导入内容：
1. 爱德思 A-Level 科目（AS + A2）
2. 20 个 G10 学生
3. 10 个爱德思学科老师
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

from app.core.database import SessionLocal
from app.modules.subjects.models import Subject
from app.modules.alevel_subjects.models import AlevelSubject
from app.modules.students.models import Student
from app.modules.teachers.models import Teacher
from app.modules.classes.models import Class


def get_or_create_subject(session, code, name, category="文化课"):
    """获取或创建基础科目"""
    subject = session.query(Subject).filter(Subject.code == code).first()
    if subject:
        return subject.id
    subject = Subject(
        code=code,
        name=name,
        category=category,
        is_main=False,
        applicable_grades=["G10", "G11", "G12"],
        applicable_class_types=["INTERNATIONAL"]
    )
    session.add(subject)
    session.flush()
    print(f"  [创建科目] {code} - {name} (id={subject.id})")
    return subject.id


def seed_edexcel_subjects(session):
    """导入爱德思 A-Level 科目"""
    print("\n【1/3】导入爱德思 A-Level 科目")

    # 定义科目映射：code -> name
    subject_map = {
        "EDX_MATH": "Mathematics",
        "EDX_FMATH": "Further Mathematics",
        "EDX_PHYS": "Physics",
        "EDX_CHEM": "Chemistry",
        "EDX_BIO": "Biology",
        "EDX_ECON": "Economics",
        "EDX_BUS": "Business Studies",
        "EDX_ENGLIT": "English Literature",
        "EDX_PSY": "Psychology",
        "EDX_CS": "Computer Science",
        "EDX_HIST": "History",
        "EDX_GEO": "Geography",
    }

    # 创建基础科目并收集 ID
    subject_ids = {}
    for code, name in subject_map.items():
        subject_ids[code] = get_or_create_subject(session, code, name)

    # 爱德思 A-Level 科目定义 (AS + A2)
    edexcel_subjects = [
        # Mathematics
        {"subject_id": subject_ids["EDX_MATH"], "exam_board": "Edexcel", "level": "AS", "module_code": "C12", "name": "Mathematics AS (C12)", "weekly_hours": 5, "max_students": 20},
        {"subject_id": subject_ids["EDX_MATH"], "exam_board": "Edexcel", "level": "A2", "module_code": "C34", "name": "Mathematics A2 (C34)", "weekly_hours": 5, "max_students": 20},
        # Further Mathematics
        {"subject_id": subject_ids["EDX_FMATH"], "exam_board": "Edexcel", "level": "AS", "module_code": "F1", "name": "Further Mathematics AS (F1)", "weekly_hours": 5, "max_students": 15},
        {"subject_id": subject_ids["EDX_FMATH"], "exam_board": "Edexcel", "level": "A2", "module_code": "F2", "name": "Further Mathematics A2 (F2)", "weekly_hours": 5, "max_students": 15},
        # Physics
        {"subject_id": subject_ids["EDX_PHYS"], "exam_board": "Edexcel", "level": "AS", "module_code": "6PH01", "name": "Physics AS (Unit 1)", "weekly_hours": 5, "max_students": 18},
        {"subject_id": subject_ids["EDX_PHYS"], "exam_board": "Edexcel", "level": "A2", "module_code": "6PH04", "name": "Physics A2 (Unit 4)", "weekly_hours": 5, "max_students": 18},
        # Chemistry
        {"subject_id": subject_ids["EDX_CHEM"], "exam_board": "Edexcel", "level": "AS", "module_code": "6CH01", "name": "Chemistry AS (Unit 1)", "weekly_hours": 5, "max_students": 18},
        {"subject_id": subject_ids["EDX_CHEM"], "exam_board": "Edexcel", "level": "A2", "module_code": "6CH04", "name": "Chemistry A2 (Unit 4)", "weekly_hours": 5, "max_students": 18},
        # Biology
        {"subject_id": subject_ids["EDX_BIO"], "exam_board": "Edexcel", "level": "AS", "module_code": "6BIO01", "name": "Biology AS (Unit 1)", "weekly_hours": 5, "max_students": 18},
        {"subject_id": subject_ids["EDX_BIO"], "exam_board": "Edexcel", "level": "A2", "module_code": "6BIO04", "name": "Biology A2 (Unit 4)", "weekly_hours": 5, "max_students": 18},
        # Economics
        {"subject_id": subject_ids["EDX_ECON"], "exam_board": "Edexcel", "level": "AS", "module_code": "6EC01", "name": "Economics AS (Unit 1)", "weekly_hours": 4, "max_students": 20},
        {"subject_id": subject_ids["EDX_ECON"], "exam_board": "Edexcel", "level": "A2", "module_code": "6EC03", "name": "Economics A2 (Unit 3)", "weekly_hours": 4, "max_students": 20},
        # Business Studies
        {"subject_id": subject_ids["EDX_BUS"], "exam_board": "Edexcel", "level": "AS", "module_code": "6BS01", "name": "Business Studies AS (Unit 1)", "weekly_hours": 4, "max_students": 20},
        {"subject_id": subject_ids["EDX_BUS"], "exam_board": "Edexcel", "level": "A2", "module_code": "6BS03", "name": "Business Studies A2 (Unit 3)", "weekly_hours": 4, "max_students": 20},
        # English Literature
        {"subject_id": subject_ids["EDX_ENGLIT"], "exam_board": "Edexcel", "level": "AS", "module_code": "6ET01", "name": "English Literature AS (Unit 1)", "weekly_hours": 4, "max_students": 16},
        {"subject_id": subject_ids["EDX_ENGLIT"], "exam_board": "Edexcel", "level": "A2", "module_code": "6ET03", "name": "English Literature A2 (Unit 3)", "weekly_hours": 4, "max_students": 16},
        # Psychology
        {"subject_id": subject_ids["EDX_PSY"], "exam_board": "Edexcel", "level": "AS", "module_code": "6PS01", "name": "Psychology AS (Unit 1)", "weekly_hours": 4, "max_students": 20},
        {"subject_id": subject_ids["EDX_PSY"], "exam_board": "Edexcel", "level": "A2", "module_code": "6PS03", "name": "Psychology A2 (Unit 3)", "weekly_hours": 4, "max_students": 20},
        # Computer Science
        {"subject_id": subject_ids["EDX_CS"], "exam_board": "Edexcel", "level": "AS", "module_code": "6CS01", "name": "Computer Science AS (Unit 1)", "weekly_hours": 4, "max_students": 18},
        {"subject_id": subject_ids["EDX_CS"], "exam_board": "Edexcel", "level": "A2", "module_code": "6CS03", "name": "Computer Science A2 (Unit 3)", "weekly_hours": 4, "max_students": 18},
        # History
        {"subject_id": subject_ids["EDX_HIST"], "exam_board": "Edexcel", "level": "AS", "module_code": "6HI01", "name": "History AS (Unit 1)", "weekly_hours": 4, "max_students": 18},
        {"subject_id": subject_ids["EDX_HIST"], "exam_board": "Edexcel", "level": "A2", "module_code": "6HI03", "name": "History A2 (Unit 3)", "weekly_hours": 4, "max_students": 18},
        # Geography
        {"subject_id": subject_ids["EDX_GEO"], "exam_board": "Edexcel", "level": "AS", "module_code": "6GE01", "name": "Geography AS (Unit 1)", "weekly_hours": 4, "max_students": 18},
        {"subject_id": subject_ids["EDX_GEO"], "exam_board": "Edexcel", "level": "A2", "module_code": "6GE03", "name": "Geography A2 (Unit 3)", "weekly_hours": 4, "max_students": 18},
    ]

    count = 0
    for item in edexcel_subjects:
        exists = session.query(AlevelSubject).filter(
            AlevelSubject.exam_board == "Edexcel",
            AlevelSubject.module_code == item["module_code"]
        ).first()
        if not exists:
            als = AlevelSubject(**item)
            session.add(als)
            count += 1
            print(f"  [创建A-Level] {item['name']} ({item['level']})")
        else:
            print(f"  [跳过] {item['name']} 已存在")

    session.commit()
    print(f"  -> 新增 {count} 条爱德思 A-Level 科目")


def seed_g10_students(session):
    """导入 20 个 G10 学生"""
    print("\n【2/3】导入 G10 学生")

    students_data = [
        {"name": "张伟", "student_no": "EDX2025001"},
        {"name": "李娜", "student_no": "EDX2025002"},
        {"name": "王芳", "student_no": "EDX2025003"},
        {"name": "刘洋", "student_no": "EDX2025004"},
        {"name": "陈静", "student_no": "EDX2025005"},
        {"name": "杨帆", "student_no": "EDX2025006"},
        {"name": "赵敏", "student_no": "EDX2025007"},
        {"name": "黄磊", "student_no": "EDX2025008"},
        {"name": "周杰", "student_no": "EDX2025009"},
        {"name": "吴倩", "student_no": "EDX2025010"},
        {"name": "徐鹏", "student_no": "EDX2025011"},
        {"name": "孙丽", "student_no": "EDX2025012"},
        {"name": "马超", "student_no": "EDX2025013"},
        {"name": "朱婷", "student_no": "EDX2025014"},
        {"name": "胡军", "student_no": "EDX2025015"},
        {"name": "郭明", "student_no": "EDX2025016"},
        {"name": "林雪", "student_no": "EDX2025017"},
        {"name": "何伟", "student_no": "EDX2025018"},
        {"name": "高飞", "student_no": "EDX2025019"},
        {"name": "梁雨", "student_no": "EDX2025020"},
    ]

    # 获取 G10 班级 ID，优先 IG10-1
    from sqlalchemy import text
    class_row = session.execute(
        text("SELECT id FROM classes WHERE grade = 'G10' AND name = 'IG10-1'")
    ).fetchone()
    class_id = class_row[0] if class_row else None

    count = 0
    for item in students_data:
        exists = session.query(Student).filter(Student.student_no == item["student_no"]).first()
        if not exists:
            student = Student(
                name=item["name"],
                student_no=item["student_no"],
                grade="G10",
                class_id=class_id,
                status="ACTIVE"
            )
            session.add(student)
            count += 1
            print(f"  [创建学生] {item['name']} ({item['student_no']})")
        else:
            print(f"  [跳过] {item['name']} 已存在")

    session.commit()
    print(f"  -> 新增 {count} 个 G10 学生")


def seed_edexcel_teachers(session):
    """导入 10 个爱德思学科老师"""
    print("\n【3/3】导入爱德思学科老师")

    teachers_data = [
        {
            "name": "Dr. Smith",
            "type": "EN",
            "department": "SECONDARY",
            "subjects": ["Mathematics", "Further Mathematics"],
            "max_weekly_hours": 25,
        },
        {
            "name": "Dr. Johnson",
            "type": "EN",
            "department": "SECONDARY",
            "subjects": ["Physics"],
            "max_weekly_hours": 25,
        },
        {
            "name": "Ms. Williams",
            "type": "EN",
            "department": "SECONDARY",
            "subjects": ["Chemistry"],
            "max_weekly_hours": 25,
        },
        {
            "name": "Mr. Brown",
            "type": "EN",
            "department": "SECONDARY",
            "subjects": ["Biology"],
            "max_weekly_hours": 25,
        },
        {
            "name": "Ms. Davis",
            "type": "EN",
            "department": "SECONDARY",
            "subjects": ["Economics", "Business Studies"],
            "max_weekly_hours": 25,
        },
        {
            "name": "Mr. Wilson",
            "type": "EN",
            "department": "SECONDARY",
            "subjects": ["English Literature"],
            "max_weekly_hours": 20,
        },
        {
            "name": "Dr. Taylor",
            "type": "EN",
            "department": "SECONDARY",
            "subjects": ["Psychology"],
            "max_weekly_hours": 20,
        },
        {
            "name": "Mr. Anderson",
            "type": "EN",
            "department": "SECONDARY",
            "subjects": ["Computer Science"],
            "max_weekly_hours": 22,
        },
        {
            "name": "Dr. Thomas",
            "type": "EN",
            "department": "SECONDARY",
            "subjects": ["History", "Geography"],
            "max_weekly_hours": 25,
        },
        {
            "name": "王老师",
            "type": "CN",
            "department": "SECONDARY",
            "subjects": ["Mathematics", "Physics"],
            "max_weekly_hours": 25,
        },
    ]

    count = 0
    for item in teachers_data:
        # 用姓名作为唯一标识检查
        exists = session.query(Teacher).filter(Teacher.name == item["name"]).first()
        if not exists:
            teacher = Teacher(
                name=item["name"],
                type=item["type"],
                department=item["department"],
                subjects=item["subjects"],
                tags=[],
                max_weekly_hours=item["max_weekly_hours"],
                weekly_hours=0,
                unavailable_slots={},
                daily_shifts={"1": "morning", "2": "morning", "3": "morning", "4": "morning", "5": "morning"},
            )
            session.add(teacher)
            count += 1
            print(f"  [创建老师] {item['name']} ({item['type']}) - {', '.join(item['subjects'])}")
        else:
            print(f"  [跳过] {item['name']} 已存在")

    session.commit()
    print(f"  -> 新增 {count} 个爱德思老师")


def main():
    print("=" * 50)
    print("爱德思 A-Level 测试数据导入")
    print("=" * 50)

    session = SessionLocal()
    try:
        seed_edexcel_subjects(session)
        seed_g10_students(session)
        seed_edexcel_teachers(session)
        print("\n" + "=" * 50)
        print("导入完成！")
        print("=" * 50)
    except Exception as e:
        session.rollback()
        print(f"\n[错误] 导入失败: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
