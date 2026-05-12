from app.core.database import engine, Base
from app.modules.tasks.models import TeachingTask
from app.modules.schedules.models import Schedule, ScheduleItem
from app.modules.teachers.models import Teacher
from app.modules.classes.models import Class
from app.modules.subjects.models import Subject
from app.modules.layers.models import LayerGroup
from app.modules.venues.models import Venue

def reset_tables():
    print("正在重置数据库表结构...")
    
    # 1. 先删除依赖别人的表 (子表)
    print("  - 删除 ScheduleItem...")
    ScheduleItem.__table__.drop(engine, checkfirst=True)
    
    print("  - 删除 TeachingTask...")
    TeachingTask.__table__.drop(engine, checkfirst=True)
    
    print("  - 删除 Schedule...")
    Schedule.__table__.drop(engine, checkfirst=True)
    
    # 2. 重新创建所有表
    print("正在重新创建所有表...")
    Base.metadata.create_all(bind=engine)
    print("✅ 数据库表重置完成！")

if __name__ == "__main__":
    reset_tables()
