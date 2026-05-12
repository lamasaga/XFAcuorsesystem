"""
一次性脚本：修复已软删除但名称未重命名的班级记录

运行方式：
cd backend
python fix_deleted_classes.py
"""

import sys
sys.path.insert(0, '.')

from sqlalchemy import text
from app.core.database import engine

def fix_deleted_classes():
    with engine.connect() as conn:
        # 查找所有已软删除但名称不是 "_D" 开头的记录
        result = conn.execute(text(
            "SELECT id, name FROM classes WHERE is_deleted = true AND name NOT LIKE '_D%'"
        ))
        records = result.fetchall()
        
        if not records:
            print("No records to fix")
            return
        
        print(f"Found {len(records)} records to fix:")
        for record in records:
            old_name = record[1]
            new_name = f"_D{record[0]}"
            conn.execute(text(
                "UPDATE classes SET name = :new_name WHERE id = :id"
            ), {"new_name": new_name, "id": record[0]})
            print(f"  - ID {record[0]}: '{old_name}' -> '{new_name}'")
        
        conn.commit()
        print("\nFix completed!")

if __name__ == "__main__":
    fix_deleted_classes()
