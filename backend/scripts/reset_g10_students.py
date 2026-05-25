#!/usr/bin/env python3
"""
========================================
G10 学生数据重置脚本
========================================

删除现有所有 G10 学生及其关联数据，重新生成 20 名标准学生。

用法：
    cd backend
    python scripts/reset_g10_students.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.core.database import engine


def reset_g10_students():
    print("=" * 50)
    print("G10 学生数据重置")
    print("=" * 50)

    with engine.connect() as conn:
        # 1. 查询现有 G10 学生数量
        result = conn.execute(text("SELECT COUNT(*) FROM students WHERE grade = 'G10'"))
        existing_count = result.scalar()
        print(f"\n现有 G10 学生: {existing_count} 人")

        if existing_count and existing_count > 0:
            # 2. 获取 G10 学生 ID 列表（用于删除关联数据）
            result = conn.execute(text("SELECT id FROM students WHERE grade = 'G10'"))
            g10_ids = [row[0] for row in result.fetchall()]
            id_list = ",".join(str(i) for i in g10_ids)

            # 3. 删除关联的选课记录
            if g10_ids:
                r = conn.execute(text(f"DELETE FROM course_selections WHERE student_id IN ({id_list})"))
                print(f"  删除选课记录: {r.rowcount} 条")

                r = conn.execute(text(f"DELETE FROM course_class_members WHERE student_id IN ({id_list})"))
                print(f"  删除课程班成员: {r.rowcount} 条")

            # 4. 删除 G10 学生
            r = conn.execute(text("DELETE FROM students WHERE grade = 'G10'"))
            print(f"  删除学生: {r.rowcount} 人")

            conn.commit()

        # 5. 生成 20 名标准 G10 学生
        names = [
            "陈浩然", "林思远", "王雨桐", "张梓轩", "李沐晴",
            "周子涵", "吴嘉怡", "郑宇航", "黄诗涵", "刘子墨",
            "赵睿哲", "孙艺萌", "杨启航", "朱晓萱", "胡家豪",
            "郭欣怡", "何宇辰", "高子晴", "马俊熙", "罗雨萱",
        ]

        class_id = 21  # IG10-1
        created_count = 0

        for i, name in enumerate(names, start=1):
            student_no = f"G10-{i:03d}"
            conn.execute(text(
                "INSERT INTO students (name, student_no, grade, class_id, status) "
                "VALUES (:name, :student_no, :grade, :class_id, :status)"
            ), {
                "name": name,
                "student_no": student_no,
                "grade": "G10",
                "class_id": class_id,
                "status": "ACTIVE",
            })
            created_count += 1

        conn.commit()
        print(f"\n生成标准 G10 学生: {created_count} 人")
        print(f"  行政班: IG10-1 (class_id={class_id})")
        print(f"  学号范围: G10-001 ~ G10-{created_count:03d}")

        # 6. 验证
        result = conn.execute(text("SELECT COUNT(*) FROM students WHERE grade = 'G10'"))
        verify_count = result.scalar()
        print(f"\n验证: 当前 G10 学生共 {verify_count} 人")

    print("\n" + "=" * 50)
    print("重置完成")
    print("=" * 50)


if __name__ == "__main__":
    reset_g10_students()
