#!/usr/bin/env python3
"""验证周五第8节班会固定时段（本地/服务器排课一轮）。"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from app.core.database import SessionLocal
from app.engine.core import ScheduleEngine
from app.engine.data.loader import load_schedule_data
from app.engine.fixed_slots import build_fixed_class_meeting_records
from app.modules.schedules.models import ScheduleItem
from app.modules.subjects.models import Subject


def verify_fixed_records_only(db) -> bool:
    data = load_schedule_data(db)
    fixed = build_fixed_class_meeting_records(data)
    if not fixed:
        print("[WARN] 未生成班会固定记录")
        return False
    locked = sum(1 for r in fixed if r.is_locked)
    print(f"[OK] 固定班会记录 {len(fixed)} 条，锁定 {locked} 条")
    return locked == len(fixed)


def verify_after_schedule(db, schedule_id: int) -> bool:
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
    print(f">>> 周五第8节: 共 {len(items)} 条, 锁定 {len(locked)} 条, 班会 {len(assembly)} 条")
    if conflicts:
        print(f"[FAIL] 周五第8节存在非班会课程 {len(conflicts)} 条")
        return False
    if assembly and len(locked) < len(assembly):
        print(f"[FAIL] 班会未全部锁定")
        return False
    print("[OK] 周五第8节班会固定时段验证通过")
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true", help="仅验证固定班会记录生成，不跑完整排课")
    parser.add_argument("--optimization", type=int, default=3)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.quick:
            ok = verify_fixed_records_only(db)
            sys.exit(0 if ok else 1)

        print(f">>> 开始排课验证 (optimization={args.optimization})...")
        engine = ScheduleEngine(db)
        result = engine.run(optimization=args.optimization, plan_count=1)
        schedule_id = result["schedule_id"]
        print(f">>> 方案 ID={schedule_id}, score={result.get('score')}")
        ok = verify_after_schedule(db, schedule_id)
        sys.exit(0 if ok else 1)
    except Exception as e:
        print(f"[FAIL] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
