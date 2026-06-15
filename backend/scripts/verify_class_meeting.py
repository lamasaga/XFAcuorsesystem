#!/usr/bin/env python3
"""验证周五第8节班会固定时段（本地排课一轮）。"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from app.core.database import SessionLocal
from app.engine.core import ScheduleEngine
from app.modules.schedules.models import ScheduleItem
from app.modules.subjects.models import Subject


def main():
    db = SessionLocal()
    try:
        print(">>> 开始排课验证 (optimization=1, 约30s)...")
        engine = ScheduleEngine(db)
        result = engine.run(optimization=1, plan_count=1)
        schedule_id = result["schedule_id"]
        print(f">>> 方案 ID={schedule_id}, score={result.get('score')}, "
              f"scheduled={result.get('scheduled_tasks')}/{result.get('total_tasks')}")

        assembly_ids = {
            s.id for s in db.query(Subject).filter(Subject.name.in_(["班会", "班会课"])).all()
        }
        items = (
            db.query(ScheduleItem)
            .filter(
                ScheduleItem.schedule_id == schedule_id,
                ScheduleItem.day == 5,
                ScheduleItem.period == 8,
            )
            .all()
        )
        locked = [i for i in items if i.is_locked]
        assembly = [i for i in items if i.subject_id in assembly_ids]
        conflicts = [
            i for i in items
            if i.subject_id not in assembly_ids and i.item_type != "alevel"
        ]

        print(f">>> 周五第8节课表项: 共 {len(items)} 条, 锁定 {len(locked)} 条, 班会 {len(assembly)} 条")
        if conflicts:
            print(f"[FAIL] 周五第8节存在非班会课程 {len(conflicts)} 条")
            for c in conflicts[:5]:
                print(f"       class_id={c.class_id} subject_id={c.subject_id} locked={c.is_locked}")
            sys.exit(1)
        if len(assembly) == 0:
            print("[WARN] 未生成班会记录（请检查科目库是否有「班会」及班级班主任）")
            sys.exit(0)
        if len(locked) < len(assembly):
            print(f"[FAIL] 班会未全部锁定: locked={len(locked)} assembly={len(assembly)}")
            sys.exit(1)

        print("[OK] 周五第8节班会固定时段验证通过")
    except Exception as e:
        print(f"[FAIL] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
