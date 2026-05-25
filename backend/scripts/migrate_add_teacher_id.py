#!/usr/bin/env python3
"""
为 alevel_subjects 表添加 teacher_id 列
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text, inspect
from app.core.database import engine


def migrate():
    insp = inspect(engine)
    cols = [c['name'] for c in insp.get_columns('alevel_subjects')]

    if 'teacher_id' not in cols:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE alevel_subjects ADD COLUMN teacher_id INTEGER"))
            conn.commit()
        print("[OK] 已添加 teacher_id 列到 alevel_subjects 表")
    else:
        print("[OK] teacher_id 列已存在，跳过")


if __name__ == "__main__":
    migrate()
