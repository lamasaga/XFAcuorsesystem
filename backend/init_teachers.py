"""
初始化教师数据脚本

运行方式：
cd backend
python init_teachers.py
"""

import sys
sys.path.insert(0, '.')

from sqlalchemy import text
from app.core.database import engine

# 教师列表（名字, 类型）
# CN = 中教, EN = 外教
TEACHERS = [
    ("张鑫", "CN"),
    ("李琳婷", "CN"),
    ("曾纪焕", "CN"),
    ("王梦晴", "CN"),
    ("金翠", "CN"),
    ("王蕴", "CN"),
    ("邱野", "CN"),
    ("杨薇薇", "CN"),
    ("马昕光", "CN"),
    ("张红娟", "CN"),
    ("刘泽宇", "CN"),
    ("赵苗", "CN"),
    ("彭涛", "CN"),
    ("赵传胜", "CN"),
    ("李伯元", "CN"),
    ("吴梦", "CN"),
    ("陶晓永", "CN"),
    ("宋程程", "CN"),
    ("Harley", "EN"),
    ("Eric", "EN"),
    ("Greg", "EN"),
    ("Shane", "EN"),
    ("张敏", "CN"),
    ("Rob", "EN"),
    ("Kyle", "EN"),
    ("Charles", "EN"),
    ("Ariel", "CN"),
    ("吕聪", "CN"),
    ("Sherry", "EN"),
    ("Cass", "EN"),
    ("李钦", "CN"),
    ("孙国忠", "CN"),
    ("Sean", "EN"),
    ("张万达", "CN"),
    ("Peter", "EN"),
    ("秦旭华", "CN"),
    ("崔朝晖", "CN"),
    ("李雪", "CN"),
    ("Charlie", "EN"),
    ("李立", "CN"),
    ("李军革", "CN"),
    ("贾宏鹏", "CN"),
    ("Belle", "EN"),
    ("马步青", "CN"),
    ("韩雪", "CN"),
    ("孙侨悉", "CN"),
    ("外聘", "CN"),
    ("Rebecca", "EN"),
    ("刘京京", "CN"),
    ("高艾婕", "CN"),
    ("Stan", "EN"),
    ("Aleks", "EN"),
    ("董丽娜", "CN"),
    ("赵轩", "CN"),
]

def init_teachers():
    with engine.connect() as conn:
        # 按依赖顺序删除数据（从叶子到根）
        
        # 1. 删除课表项目（引用了教学任务）
        result = conn.execute(text("DELETE FROM schedule_items"))
        print(f"Deleted {result.rowcount} schedule items")
        
        # 2. 删除课表（引用了班级等）
        result = conn.execute(text("DELETE FROM schedules"))
        print(f"Deleted {result.rowcount} schedules")
        
        # 3. 删除教学任务（引用了教师、班级、科目）
        result = conn.execute(text("DELETE FROM teaching_tasks"))
        print(f"Deleted {result.rowcount} teaching tasks")
        
        # 4. 清除班级的班主任关联（解除外键约束）
        conn.execute(text("UPDATE classes SET homeroom_cn_id = NULL, homeroom_en_id = NULL"))
        print("Cleared homeroom teacher references in classes")
        
        # 5. 删除所有现有教师（硬删除）
        result = conn.execute(text("DELETE FROM teachers"))
        print(f"Deleted {result.rowcount} existing teachers")
        
        # 重置序列（自增ID从1开始）
        conn.execute(text("ALTER SEQUENCE teachers_id_seq RESTART WITH 1"))
        print("Reset ID sequence")
        
        # 2. 添加新教师
        print(f"\nAdding {len(TEACHERS)} teachers:")
        for name, teacher_type in TEACHERS:
            conn.execute(text(
                """INSERT INTO teachers (name, type, department, subjects, tags, max_weekly_hours, weekly_hours, is_deleted)
                   VALUES (:name, :type, 'PRIMARY', '{}', '{}', 25, 0, false)"""
            ), {"name": name, "type": teacher_type})
            print(f"  + {name} ({teacher_type})")
        
        conn.commit()
        print(f"\nDone! Added {len(TEACHERS)} teachers.")

if __name__ == "__main__":
    init_teachers()
