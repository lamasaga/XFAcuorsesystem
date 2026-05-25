#!/usr/bin/env python3
"""
========================================
G10 学生 A-Level 排课诊断脚本
========================================

诊断 10 年级学生没有进入 A-Level 排课的原因。

用法：
    cd backend
    python scripts/diagnose_g10_scheduling.py

检查项：
1. G10/G11/G12 学生总数
2. 各年级选课记录状态分布
3. 自动分班结果（课程班及成员）
4. 课程班教师分配情况
5. 排课引擎实际加载的 A-Level 课程班
"""

import sys
import os

# 将 backend 加入路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import func
from app.core.database import SessionLocal, engine
from app.modules.students.models import Student
from app.modules.course_selections.models import CourseSelection
from app.modules.course_classes.models import CourseClass, CourseClassMember
from app.modules.alevel_subjects.models import AlevelSubject


def diagnose():
    db = SessionLocal()
    try:
        print("=" * 60)
        print("G10 学生 A-Level 排课诊断报告")
        print("=" * 60)

        # 1. 各年级学生总数
        print("\n【1】各年级学生总数")
        grade_counts = (
            db.query(Student.grade, func.count(Student.id))
            .filter(Student.is_deleted == False, Student.status == "ACTIVE")
            .group_by(Student.grade)
            .all()
        )
        for grade, count in sorted(grade_counts):
            print(f"    {grade}: {count} 人")

        # 2. 各年级选课记录状态分布
        print("\n【2】各年级选课记录状态分布（关联 students 表）")
        selections = (
            db.query(CourseSelection, Student.grade)
            .join(Student, CourseSelection.student_id == Student.id)
            .filter(CourseSelection.is_deleted == False)
            .all()
        )
        from collections import defaultdict
        status_by_grade = defaultdict(lambda: defaultdict(int))
        for sel, grade in selections:
            status_by_grade[grade][sel.status] += 1

        for grade in sorted(status_by_grade.keys()):
            print(f"    {grade}:")
            for status, count in sorted(status_by_grade[grade].items()):
                marker = " <-- 自动分班需要 APPROVED" if status != "APPROVED" else ""
                print(f"      {status}: {count}{marker}")

        # 3. 各年级 APPROVED 选课中，各科目选课人数
        print("\n【3】APPROVED 选课的各科目人数（按年级）")
        approved_selections = (
            db.query(CourseSelection, Student.grade, Student.name)
            .join(Student, CourseSelection.student_id == Student.id)
            .filter(
                CourseSelection.is_deleted == False,
                CourseSelection.status == "APPROVED",
            )
            .all()
        )

        subject_students_by_grade = defaultdict(lambda: defaultdict(list))
        for sel, grade, name in approved_selections:
            for item in (sel.selections or []):
                subject_id = item.get("alevel_subject_id")
                if subject_id:
                    subject_students_by_grade[grade][subject_id].append(name)

        subjects = db.query(AlevelSubject).filter(AlevelSubject.is_deleted == False).all()
        subject_map = {s.id: s.name for s in subjects}

        for grade in sorted(subject_students_by_grade.keys()):
            print(f"    {grade}:")
            for subject_id, names in sorted(subject_students_by_grade[grade].items(), key=lambda x: len(x[1]), reverse=True):
                subject_name = subject_map.get(subject_id, f"Subject({subject_id})")
                marker = " <-- 不足5人不会开班" if len(names) < 5 else ""
                print(f"      {subject_name}: {len(names)} 人{marker}")

        # 4. 课程班状态及教师分配
        print("\n【4】课程班状态及教师分配")
        classes = db.query(CourseClass).filter(CourseClass.is_deleted == False).all()
        for cc in classes:
            teacher_status = "[OK] 已分配" if cc.teacher_id else "[X] 未分配教师"
            status_marker = "[OK]" if cc.status == "ACTIVE" else f"[WARN] {cc.status}"
            subject_name = subject_map.get(cc.alevel_subject_id, f"Subject({cc.alevel_subject_id})")
            print(f"    {cc.name} ({subject_name}) | {status_marker} | {teacher_status}")

        # 5. 各课程班成员年级分布
        print("\n【5】各课程班成员年级分布")
        for cc in classes:
            if cc.status != "ACTIVE" or cc.is_deleted:
                continue
            members = (
                db.query(Student.grade, func.count(Student.id))
                .join(CourseClassMember, Student.id == CourseClassMember.student_id)
                .filter(
                    CourseClassMember.course_class_id == cc.id,
                    CourseClassMember.status == "ENROLLED",
                    Student.is_deleted == False,
                )
                .group_by(Student.grade)
                .all()
            )
            if members:
                member_str = ", ".join([f"{grade}: {count}" for grade, count in sorted(members)])
                teacher_marker = "[OK]" if cc.teacher_id else "[X] 无教师（排课会被跳过）"
                print(f"    {cc.name} | {member_str} | {teacher_marker}")

        # 6. 模拟排课引擎加载逻辑
        print("\n【6】模拟排课引擎 A-Level 加载结果")
        valid_classes = (
            db.query(CourseClass)
            .filter(
                CourseClass.is_deleted == False,
                CourseClass.status == "ACTIVE",
                CourseClass.teacher_id.isnot(None),
            )
            .all()
        )

        skipped_no_teacher = (
            db.query(CourseClass)
            .filter(
                CourseClass.is_deleted == False,
                CourseClass.status == "ACTIVE",
                CourseClass.teacher_id.is_(None),
            )
            .all()
        )

        print(f"    [OK] 有效课程班（有教师）: {len(valid_classes)} 个")
        print(f"    [X] 被跳过课程班（无教师）: {len(skipped_no_teacher)} 个")

        for cc in skipped_no_teacher:
            members = (
                db.query(Student.grade, func.count(Student.id))
                .join(CourseClassMember, Student.id == CourseClassMember.student_id)
                .filter(
                    CourseClassMember.course_class_id == cc.id,
                    CourseClassMember.status == "ENROLLED",
                    Student.is_deleted == False,
                )
                .group_by(Student.grade)
                .all()
            )
            member_str = ", ".join([f"{grade}: {count}" for grade, count in sorted(members)]) if members else "无成员"
            print(f"      - {cc.name} | {member_str}")

        # 7. 没有加入任何课程班的 G10 学生
        print("\n【7】没有加入任何 ACTIVE 课程班的 G10 学生")
        g10_students = (
            db.query(Student)
            .filter(Student.is_deleted == False, Student.grade == "G10", Student.status == "ACTIVE")
            .all()
        )
        g10_member_ids = (
            db.query(CourseClassMember.student_id)
            .join(CourseClass, CourseClassMember.course_class_id == CourseClass.id)
            .filter(
                CourseClassMember.status == "ENROLLED",
                CourseClass.is_deleted == False,
                CourseClass.status == "ACTIVE",
            )
            .distinct()
            .all()
        )
        g10_member_ids = {r[0] for r in g10_member_ids}

        g10_without_class = [s for s in g10_students if s.id not in g10_member_ids]
        if g10_without_class:
            print(f"    [WARN] 共 {len(g10_without_class)} 人：")
            for s in g10_without_class[:10]:
                print(f"      - {s.name} (ID: {s.id})")
            if len(g10_without_class) > 10:
                print(f"      ... 等共 {len(g10_without_class)} 人")
        else:
            print("    [OK] 所有 G10 学生都已加入课程班")

        print("\n" + "=" * 60)
        print("诊断完成")
        print("=" * 60)

    finally:
        db.close()


if __name__ == "__main__":
    diagnose()
