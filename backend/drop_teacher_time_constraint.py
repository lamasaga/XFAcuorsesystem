"""
数据库迁移：删除 schedule_items 表的教师时间唯一约束

原因：分层/合班课程中，一个老师可以在同一时间教多个不同班级，
这是合理的业务场景，不应该被唯一约束阻止。

运行方式：
cd backend
python drop_teacher_time_constraint.py
"""
from sqlalchemy import text
from app.core.database import engine

def drop_constraint():
    with engine.connect() as conn:
        # 删除教师时间唯一约束
        conn.execute(text("ALTER TABLE schedule_items DROP CONSTRAINT IF EXISTS uq_schedule_teacher_time;"))
        conn.commit()
        print("成功删除约束 uq_schedule_teacher_time")

if __name__ == "__main__":
    drop_constraint()
