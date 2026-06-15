#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.core.database import SessionLocal
from app.engine.data.loader import load_schedule_data
from app.engine.fixed_slots import build_fixed_class_meeting_records, is_class_meeting_task

db = SessionLocal()
data = load_schedule_data(db)
fixed = build_fixed_class_meeting_records(data)
banhui_tasks = sum(1 for t in data.tasks if is_class_meeting_task(data, t))
print(f"fixed_records={len(fixed)} banhui_tasks={banhui_tasks} classes={len(data.classes)}")
db.close()
