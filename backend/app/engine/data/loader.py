"""
数据库数据加载器

从 SQLAlchemy ORM 加载数据并转换为引擎内部模型。
"""

from typing import Optional
from sqlalchemy.orm import Session

from .models import (
    Teacher, Class, Subject, Task, LayerGroup, Venue, ScheduleData
)


class DatabaseLoader:
    """
    数据库数据加载器
    
    从数据库加载排课所需的所有数据，并转换为引擎内部模型。
    
    Usage:
        from app.core.database import SessionLocal
        
        db = SessionLocal()
        loader = DatabaseLoader(db)
        data = loader.load()
    """
    
    def __init__(self, db: Session):
        """
        初始化加载器
        
        Args:
            db: SQLAlchemy 数据库会话
        """
        self.db = db
        
        # 延迟导入 ORM 模型，避免循环依赖
        self._orm_models_loaded = False
    
    def _load_orm_models(self):
        """延迟加载 ORM 模型"""
        if self._orm_models_loaded:
            return
        
        from app.modules.teachers.models import Teacher as TeacherORM
        from app.modules.classes.models import Class as ClassORM
        from app.modules.subjects.models import Subject as SubjectORM
        from app.modules.tasks.models import TeachingTask as TaskORM
        from app.modules.layers.models import LayerGroup as LayerGroupORM
        from app.modules.venues.models import Venue as VenueORM
        
        self.TeacherORM = TeacherORM
        self.ClassORM = ClassORM
        self.SubjectORM = SubjectORM
        self.TaskORM = TaskORM
        self.LayerGroupORM = LayerGroupORM
        self.VenueORM = VenueORM
        
        self._orm_models_loaded = True
    
    def load(self) -> ScheduleData:
        """
        加载完整的排课数据
        
        Returns:
            ScheduleData: 包含所有数据的数据集
        """
        self._load_orm_models()
        
        # 加载各类数据
        teachers = self._load_teachers()
        classes = self._load_classes()
        subjects = self._load_subjects()
        venues = self._load_venues()
        layer_groups = self._load_layer_groups(subjects)
        tasks = self._load_tasks(teachers, classes, subjects, layer_groups)
        
        # 构建数据集
        data = ScheduleData(
            teachers=teachers,
            classes=classes,
            subjects=subjects,
            tasks=tasks,
            layer_groups=layer_groups,
            venues=venues
        )
        
        return data
    
    def _load_teachers(self) -> list[Teacher]:
        """加载教师数据"""
        orm_teachers = self.db.query(self.TeacherORM).filter(
            self.TeacherORM.is_deleted == False
        ).all()
        
        return [Teacher.from_orm(t) for t in orm_teachers]
    
    def _load_classes(self) -> list[Class]:
        """加载班级数据"""
        orm_classes = self.db.query(self.ClassORM).filter(
            self.ClassORM.is_deleted == False
        ).all()
        
        return [Class.from_orm(c) for c in orm_classes]
    
    def _load_subjects(self) -> list[Subject]:
        """加载科目数据"""
        orm_subjects = self.db.query(self.SubjectORM).filter(
            self.SubjectORM.is_deleted == False
        ).all()
        
        return [Subject.from_orm(s) for s in orm_subjects]
    
    def _load_venues(self) -> list[Venue]:
        """加载场地数据"""
        orm_venues = self.db.query(self.VenueORM).all()
        
        return [Venue.from_orm(v) for v in orm_venues]
    
    def _load_layer_groups(self, subjects: list[Subject]) -> list[LayerGroup]:
        """加载分层组数据"""
        # 构建科目ID到名称的映射
        subject_names = {s.id: s.name for s in subjects}
        
        orm_groups = self.db.query(self.LayerGroupORM).all()
        
        groups = []
        for g in orm_groups:
            subject_name = subject_names.get(g.subject_id, "未知科目")
            groups.append(LayerGroup.from_orm(g, subject_name=subject_name))
        
        return groups
    
    def _load_tasks(
        self,
        teachers: list[Teacher],
        classes: list[Class],
        subjects: list[Subject],
        layer_groups: list[LayerGroup]
    ) -> list[Task]:
        """加载教学任务数据"""
        # 构建查找映射
        teacher_names = {t.id: t.name for t in teachers}
        class_names = {c.id: c.name for c in classes}
        subject_map = {s.id: s for s in subjects}
        
        orm_tasks = self.db.query(self.TaskORM).filter(
            self.TaskORM.is_deleted == False
        ).all()
        
        tasks = []
        for t in orm_tasks:
            subject = subject_map.get(t.subject_id)
            venue_type = subject.required_room_type if subject else None
            
            task = Task.from_orm(
                t,
                teacher_name=teacher_names.get(t.teacher_id, "未知教师"),
                class_name=class_names.get(t.class_id, "未知班级"),
                subject_name=subject.name if subject else "未知科目",
                venue_type=venue_type
            )
            tasks.append(task)
            
            # 将任务ID添加到对应的分层组
            if t.layer_group_id:
                for lg in layer_groups:
                    if lg.id == t.layer_group_id:
                        lg.task_ids.append(t.id)
                        break
        
        # 设置任务优先级
        self._set_task_priorities(tasks, layer_groups)
        
        return tasks
    
    def _set_task_priorities(
        self,
        tasks: list[Task],
        layer_groups: list[LayerGroup]
    ):
        """
        设置任务优先级
        
        优先级规则：
        1. 分层课（复杂度越高优先级越高）
        2. 场地受限课
        3. 主科连堂课
        4. 普通课
        """
        # 分层组复杂度映射
        layer_complexity = {lg.id: lg.complexity for lg in layer_groups}
        
        for task in tasks:
            priority = 0
            
            # 分层课
            if task.layer_group_id:
                priority = 1000 + layer_complexity.get(task.layer_group_id, 0)
            # 场地受限课
            elif task.required_venue_type:
                priority = 500
            # 连堂课
            elif task.is_continuous:
                priority = 200
            
            task.priority = priority


def load_schedule_data(db: Session) -> ScheduleData:
    """
    便捷函数：从数据库加载排课数据
    
    Args:
        db: 数据库会话
    
    Returns:
        ScheduleData: 完整的排课数据集
    """
    loader = DatabaseLoader(db)
    return loader.load()
