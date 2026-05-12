"""
========================================
数据库初始化脚本
========================================

这个脚本用于：
1. 创建数据库表（如果不存在）
2. 插入示例数据

运行方法：
  cd backend
  python init_data.py

⚠️ 注意：
  - 运行前请确保 PostgreSQL 已启动
  - 运行前请确保 .env 配置正确
  - 多次运行不会重复插入数据（会检查是否已存在）
"""

import sys
from pathlib import Path

# 将项目根目录添加到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy.orm import Session
from app.core.database import engine, Base, SessionLocal
from app.core.config import settings

# 导入所有模型（这样 Base.metadata 才能知道所有表）
from app.modules.teachers.models import Teacher
from app.modules.classes.models import Class
from app.modules.subjects.models import Subject
from app.modules.tasks.models import TeachingTask


def create_tables():
    """创建所有数据库表"""
    print("正在创建数据库表...")
    Base.metadata.create_all(bind=engine)
    print("✅ 数据库表创建完成")


def init_subjects(db: Session):
    """初始化科目数据"""
    print("正在初始化科目数据...")
    
    subjects = [
        # 主科
        {"code": "CHINESE", "name": "语文", "category": "文化课", "is_main": True, "color": "#ef4444"},
        {"code": "MATH", "name": "数学", "category": "文化课", "is_main": True, "color": "#3b82f6"},
        {"code": "ENGLISH", "name": "英语", "category": "文化课", "is_main": True, "color": "#f59e0b"},
        
        # 文化课
        {"code": "PHYSICS", "name": "物理", "category": "文化课", "is_main": False, "color": "#10b981"},
        {"code": "CHEMISTRY", "name": "化学", "category": "文化课", "is_main": False, "color": "#8b5cf6"},
        {"code": "BIOLOGY", "name": "生物", "category": "文化课", "is_main": False, "color": "#06b6d4"},
        {"code": "HISTORY", "name": "历史", "category": "文化课", "is_main": False, "color": "#64748b"},
        {"code": "GEOGRAPHY", "name": "地理", "category": "文化课", "is_main": False, "color": "#84cc16"},
        {"code": "POLITICS", "name": "政治", "category": "文化课", "is_main": False, "color": "#ec4899"},
        
        # 艺术
        {"code": "ART", "name": "美术", "category": "艺术", "is_main": False, "required_room_type": "美术教室", "color": "#f97316"},
        {"code": "MUSIC", "name": "音乐", "category": "艺术", "is_main": False, "color": "#a855f7"},
        {"code": "VOCAL", "name": "声乐", "category": "艺术", "is_main": False, "required_room_type": "声乐教室", "color": "#ec4899"},
        {"code": "PIANO", "name": "钢琴", "category": "艺术", "is_main": False, "required_room_type": "钢琴教室", "color": "#6366f1"},
        {"code": "DANCE", "name": "舞蹈", "category": "艺术", "is_main": False, "color": "#f472b6"},
        
        # 体育
        {"code": "PE", "name": "体育", "category": "体育", "is_main": False, "required_room_type": "体育场地", "color": "#22c55e"},
        {"code": "SKATING", "name": "轮滑", "category": "体育", "is_main": False, "required_room_type": "体育场地", "color": "#14b8a6"},
        
        # 综合
        {"code": "SCIENCE", "name": "科学", "category": "综合", "is_main": False, "color": "#0ea5e9"},
        {"code": "IEYC", "name": "IEYC", "category": "综合", "is_main": False, "color": "#7c3aed"},
        {"code": "IPC", "name": "IPC", "category": "综合", "is_main": False, "color": "#6366f1"},
        {"code": "LIBRARY", "name": "图书馆", "category": "综合", "is_main": False, "color": "#78716c"},
    ]
    
    count = 0
    for subject_data in subjects:
        # 检查是否已存在
        existing = db.query(Subject).filter(Subject.code == subject_data["code"]).first()
        if not existing:
            db.add(Subject(**subject_data))
            count += 1
    
    db.commit()
    print(f"✅ 插入了 {count} 个科目")


def init_teachers(db: Session):
    """初始化教师数据"""
    print("正在初始化教师数据...")
    
    teachers = [
        # 小学部中教
        {"name": "郭金莉", "type": "CN", "department": "PRIMARY", "subjects": ["语文", "IEYC"], "tags": ["HOMEROOM_TEACHER"], "max_weekly_hours": 25},
        {"name": "黄丽娜", "type": "CN", "department": "PRIMARY", "subjects": ["语文", "数学"], "tags": ["HOMEROOM_TEACHER"], "max_weekly_hours": 25},
        {"name": "温惠", "type": "CN", "department": "PRIMARY", "subjects": ["数学"], "tags": [], "max_weekly_hours": 25},
        {"name": "赵立娜", "type": "CN", "department": "PRIMARY", "subjects": ["语文"], "tags": ["HOMEROOM_TEACHER"], "max_weekly_hours": 25},
        {"name": "李春香", "type": "CN", "department": "PRIMARY", "subjects": ["语文"], "tags": ["HOMEROOM_TEACHER"], "max_weekly_hours": 25},
        {"name": "王芳", "type": "CN", "department": "PRIMARY", "subjects": ["数学"], "tags": ["PRIMARY_ADMIN"], "max_weekly_hours": 20},
        {"name": "刘敏", "type": "CN", "department": "PRIMARY", "subjects": ["美术"], "tags": [], "max_weekly_hours": 25},
        {"name": "陈静", "type": "CN", "department": "PRIMARY", "subjects": ["音乐", "声乐"], "tags": [], "max_weekly_hours": 25},
        
        # 小学部外教
        {"name": "Bing", "type": "EN", "department": "PRIMARY", "subjects": ["英语"], "tags": ["HOMEROOM_TEACHER"], "max_weekly_hours": 25},
        {"name": "Josh B", "type": "EN", "department": "PRIMARY", "subjects": ["英语", "IEYC"], "tags": ["HOMEROOM_TEACHER"], "max_weekly_hours": 25},
        {"name": "Andrew", "type": "EN", "department": "PRIMARY", "subjects": ["科学", "图书馆", "英语", "IPC"], "tags": ["HOMEROOM_TEACHER"], "max_weekly_hours": 25},
        {"name": "Emily", "type": "EN", "department": "PRIMARY", "subjects": ["英语"], "tags": ["HOMEROOM_TEACHER"], "max_weekly_hours": 25},
        
        # 中学部中教
        {"name": "马昕光", "type": "CN", "department": "SECONDARY", "subjects": ["数学"], "tags": ["HOMEROOM_TEACHER", "SECONDARY_ADMIN"], "max_weekly_hours": 20},
        {"name": "张红娟", "type": "CN", "department": "SECONDARY", "subjects": ["数学"], "tags": ["HOMEROOM_TEACHER"], "max_weekly_hours": 25},
        {"name": "李明", "type": "CN", "department": "SECONDARY", "subjects": ["语文"], "tags": ["HOMEROOM_TEACHER"], "max_weekly_hours": 25},
        {"name": "王强", "type": "CN", "department": "SECONDARY", "subjects": ["物理"], "tags": [], "max_weekly_hours": 25},
        {"name": "赵勇", "type": "CN", "department": "SECONDARY", "subjects": ["化学"], "tags": ["HOMEROOM_TEACHER"], "max_weekly_hours": 25},
        
        # 中学部外教
        {"name": "Stan", "type": "EN", "department": "SECONDARY", "subjects": ["体育"], "tags": ["HOMEROOM_TEACHER"], "max_weekly_hours": 25},
        {"name": "Cass", "type": "EN", "department": "SECONDARY", "subjects": ["生物"], "tags": ["HOMEROOM_TEACHER"], "max_weekly_hours": 25},
        {"name": "Kevin", "type": "EN", "department": "SECONDARY", "subjects": ["英语"], "tags": ["HOMEROOM_TEACHER"], "max_weekly_hours": 25},
    ]
    
    count = 0
    for teacher_data in teachers:
        existing = db.query(Teacher).filter(Teacher.name == teacher_data["name"]).first()
        if not existing:
            db.add(Teacher(**teacher_data))
            count += 1
    
    db.commit()
    print(f"✅ 插入了 {count} 个教师")


def init_classes(db: Session):
    """初始化班级数据"""
    print("正在初始化班级数据...")
    
    classes = [
        # 小学部 I 类
        {"name": "IPK-1", "type": "I", "grade": "PK", "class_no": 1, "department": "PRIMARY"},
        {"name": "IKG-1", "type": "I", "grade": "KG", "class_no": 1, "department": "PRIMARY"},
        {"name": "IG1-1", "type": "I", "grade": "G1", "class_no": 1, "department": "PRIMARY"},
        {"name": "IG1-2", "type": "I", "grade": "G1", "class_no": 2, "department": "PRIMARY"},
        {"name": "IG2-1", "type": "I", "grade": "G2", "class_no": 1, "department": "PRIMARY"},
        {"name": "IG2-2", "type": "I", "grade": "G2", "class_no": 2, "department": "PRIMARY"},
        {"name": "IG3-1", "type": "I", "grade": "G3", "class_no": 1, "department": "PRIMARY"},
        {"name": "IG3-2", "type": "I", "grade": "G3", "class_no": 2, "department": "PRIMARY"},
        {"name": "IG4-1", "type": "I", "grade": "G4", "class_no": 1, "department": "PRIMARY"},
        {"name": "IG4-2", "type": "I", "grade": "G4", "class_no": 2, "department": "PRIMARY"},
        {"name": "IG5-1", "type": "I", "grade": "G5", "class_no": 1, "department": "PRIMARY"},
        {"name": "IG5-2", "type": "I", "grade": "G5", "class_no": 2, "department": "PRIMARY"},
        
        # 中学部 I 类
        {"name": "IG6-1", "type": "I", "grade": "G6", "class_no": 1, "department": "SECONDARY"},
        {"name": "IG6-2", "type": "I", "grade": "G6", "class_no": 2, "department": "SECONDARY"},
        {"name": "IG7-1", "type": "I", "grade": "G7", "class_no": 1, "department": "SECONDARY"},
        {"name": "IG7-2", "type": "I", "grade": "G7", "class_no": 2, "department": "SECONDARY"},
        {"name": "IG8-1", "type": "I", "grade": "G8", "class_no": 1, "department": "SECONDARY"},
        {"name": "IG8-2", "type": "I", "grade": "G8", "class_no": 2, "department": "SECONDARY"},
        {"name": "IG9-1", "type": "I", "grade": "G9", "class_no": 1, "department": "SECONDARY"},
        {"name": "IG9-2", "type": "I", "grade": "G9", "class_no": 2, "department": "SECONDARY"},
        {"name": "IG10-1", "type": "I", "grade": "G10", "class_no": 1, "department": "SECONDARY"},
        {"name": "IG11-1", "type": "I", "grade": "G11", "class_no": 1, "department": "SECONDARY"},
        
        # N 类
        {"name": "NG1-1", "type": "N", "grade": "G1", "class_no": 1, "department": "PRIMARY"},
        {"name": "NG2-1", "type": "N", "grade": "G2", "class_no": 1, "department": "PRIMARY"},
        {"name": "NG3-1", "type": "N", "grade": "G3", "class_no": 1, "department": "PRIMARY"},
        {"name": "NG4-1", "type": "N", "grade": "G4", "class_no": 1, "department": "PRIMARY"},
        {"name": "NG5-1", "type": "N", "grade": "G5", "class_no": 1, "department": "PRIMARY"},
        {"name": "NG6-1", "type": "N", "grade": "G6", "class_no": 1, "department": "SECONDARY"},
        {"name": "NG7-1", "type": "N", "grade": "G7", "class_no": 1, "department": "SECONDARY"},
        {"name": "NG8-1", "type": "N", "grade": "G8", "class_no": 1, "department": "SECONDARY"},
        {"name": "NG9-1", "type": "N", "grade": "G9", "class_no": 1, "department": "SECONDARY"},
    ]
    
    count = 0
    for class_data in classes:
        existing = db.query(Class).filter(Class.name == class_data["name"]).first()
        if not existing:
            db.add(Class(**class_data))
            count += 1
    
    db.commit()
    print(f"✅ 插入了 {count} 个班级")


def main():
    """主函数"""
    print("=" * 50)
    print("排课系统 - 数据库初始化")
    print("=" * 50)
    print(f"数据库: {settings.DATABASE_URL}")
    print()
    
    try:
        # 创建表
        create_tables()
        
        # 创建会话
        db = SessionLocal()
        
        try:
            # 初始化数据
            init_subjects(db)
            init_teachers(db)
            init_classes(db)
            
            print()
            print("=" * 50)
            print("✅ 数据库初始化完成！")
            print("=" * 50)
            print()
            print("现在可以：")
            print("1. 运行后端: uvicorn app.main:app --reload")
            print("2. 访问 API 文档: http://localhost:8000/docs")
            print("3. 运行前端: cd ../frontend && npm run dev")
        finally:
            db.close()
            
    except Exception as e:
        print()
        print("❌ 初始化失败！")
        print(f"错误信息: {e}")
        print()
        print("请检查：")
        print("1. PostgreSQL 服务是否启动")
        print("2. .env 文件中的数据库配置是否正确")
        print("3. 数据库 'schedule_db' 是否已创建")


if __name__ == "__main__":
    main()
