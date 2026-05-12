"""
数据库迁移脚本：创建教研组表 + 教师表增加 research_group_id 列
"""
from app.core.database import engine
from sqlalchemy import text, inspect


def migrate():
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    with engine.connect() as conn:
        # 1. 创建教研组表（如果不存在）
        if "research_groups" not in existing_tables:
            conn.execute(text("""
                CREATE TABLE research_groups (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(50) NOT NULL UNIQUE,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    is_deleted BOOLEAN DEFAULT FALSE
                )
            """))
            print("已创建 research_groups 表")
        else:
            print("research_groups 表已存在，跳过")

        # 2. 教师表增加 research_group_id 列（如果不存在）
        teacher_cols = [c["name"] for c in inspector.get_columns("teachers")]
        if "research_group_id" not in teacher_cols:
            conn.execute(text("""
                ALTER TABLE teachers
                ADD COLUMN research_group_id INTEGER
                    REFERENCES research_groups(id)
            """))
            print("已为 teachers 表添加 research_group_id 列")
        else:
            print("teachers.research_group_id 列已存在，跳过")

        conn.commit()

    # 3. 插入默认教研组
    from app.core.database import SessionLocal
    from app.modules.teachers.models import ResearchGroup

    db = SessionLocal()
    defaults = [
        "语文教研组", "数学教研组", "英语教研组", "理科教研组",
        "文科教研组", "艺体教研组", "小学教研组", "中学教研组",
    ]
    added = 0
    for name in defaults:
        exists = db.query(ResearchGroup).filter(
            ResearchGroup.name == name
        ).first()
        if not exists:
            db.add(ResearchGroup(name=name))
            added += 1
    db.commit()
    db.close()
    if added:
        print(f"已插入 {added} 个默认教研组")
    else:
        print("默认教研组已存在，跳过")

    print("迁移完成!")


if __name__ == "__main__":
    migrate()
