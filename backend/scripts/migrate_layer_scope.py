#!/usr/bin/env python3
"""
为 layer_groups 表添加 layer_scope 列，并根据 is_cross_grade 回填历史数据。
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text, inspect
from app.core.database import engine


def migrate():
    insp = inspect(engine)
    if "layer_groups" not in insp.get_table_names():
        print("[SKIP] layer_groups 表不存在")
        return

    cols = [c["name"] for c in insp.get_columns("layer_groups")]

    with engine.connect() as conn:
        if "layer_scope" not in cols:
            if engine.dialect.name == "sqlite":
                conn.execute(text(
                    "ALTER TABLE layer_groups ADD COLUMN layer_scope VARCHAR(20) "
                    "DEFAULT 'GRADE' NOT NULL"
                ))
            else:
                conn.execute(text(
                    "ALTER TABLE layer_groups ADD COLUMN layer_scope VARCHAR(20) "
                    "NOT NULL DEFAULT 'GRADE'"
                ))
            conn.commit()
            print("[OK] 已添加 layer_scope 列")
        else:
            print("[OK] layer_scope 列已存在")

        if engine.dialect.name == "sqlite":
            cross_sql = (
                "UPDATE layer_groups SET layer_scope = 'CROSS_GRADE' "
                "WHERE is_cross_grade = 1 AND (layer_scope IS NULL OR layer_scope = 'GRADE')"
            )
        else:
            cross_sql = (
                "UPDATE layer_groups SET layer_scope = 'CROSS_GRADE' "
                "WHERE is_cross_grade IS TRUE AND layer_scope = 'GRADE'"
            )
        conn.execute(text(cross_sql))
        conn.commit()
        print("[OK] 已根据 is_cross_grade 回填 CROSS_GRADE")


if __name__ == "__main__":
    migrate()
