"""
数据库数据加载器

从 SQLAlchemy ORM 加载数据并转换为引擎内部模型。
"""

from typing import Optional
from sqlalchemy.orm import Session

from .models import (
    Teacher, Class, Subject, Task, LayerGroup, Venue, ScheduleData,
    TimeSlot, DepartmentTimeSlots, AlevelScheduleSession
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
        from app.modules.time_slots.models import TimeSlotConfig as TimeSlotORM
        from app.modules.course_classes.models import CourseClass as CourseClassORM
        from app.modules.course_classes.models import CourseClassMember as MemberORM
        from app.modules.alevel_subjects.models import AlevelSubject as AlevelSubjectORM
        
        self.TeacherORM = TeacherORM
        self.ClassORM = ClassORM
        self.SubjectORM = SubjectORM
        self.TaskORM = TaskORM
        self.LayerGroupORM = LayerGroupORM
        self.VenueORM = VenueORM
        self.TimeSlotORM = TimeSlotORM
        self.CourseClassORM = CourseClassORM
        self.MemberORM = MemberORM
        self.AlevelSubjectORM = AlevelSubjectORM
        
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
        time_slots = self._load_time_slots()
        alevel_sessions = self._load_alevel_sessions()
        
        # 构建数据集
        data = ScheduleData(
            teachers=teachers,
            classes=classes,
            subjects=subjects,
            tasks=tasks,
            layer_groups=layer_groups,
            venues=venues,
            time_slots=time_slots,
            alevel_sessions=alevel_sessions
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
    
    def _load_time_slots(self) -> dict[str, DepartmentTimeSlots]:
        """
        加载时间槽配置数据
        
        从 time_slot_configs 表加载各学部的时间槽定义，
        按学部组织为 DepartmentTimeSlots 对象。
        
        Returns:
            Dict[str, DepartmentTimeSlots]: {department: DepartmentTimeSlots}
        """
        orm_slots = self.db.query(self.TimeSlotORM).filter(
            self.TimeSlotORM.is_active == True
        ).all()
        
        # 按学部和 day_type 分组
        grouped: dict[str, dict[str, list[TimeSlot]]] = {}
        for s in orm_slots:
            dept = s.department
            day_type = s.day_type
            if dept not in grouped:
                grouped[dept] = {}
            if day_type not in grouped[dept]:
                grouped[dept][day_type] = []
            
            # 将 time 对象格式化为 HH:MM 字符串
            start_str = s.start_time.strftime("%H:%M") if s.start_time else ""
            end_str = s.end_time.strftime("%H:%M") if s.end_time else ""
            
            grouped[dept][day_type].append(TimeSlot(
                period=s.period_num,
                start_time=start_str,
                end_time=end_str,
                period_type=s.period_type,
                period_name=s.period_name or ""
            ))
        
        # 组装为 DepartmentTimeSlots
        result = {}
        for dept, day_slots in grouped.items():
            dts = DepartmentTimeSlots(department=dept)
            for day_type, slots in day_slots.items():
                # 按 period_num 排序
                slots.sort(key=lambda s: s.period)
                if day_type == "MONDAY":
                    dts.monday = slots
                elif day_type == "TUE_THU":
                    dts.tue_thu = slots
                elif day_type == "FRIDAY":
                    dts.friday = slots
            result[dept] = dts
        
        return result
    
    def _load_alevel_sessions(self) -> list[AlevelScheduleSession]:
        """
        加载 A-Level 课程班数据
        
        查询所有活跃的课程班及其学生成员，构建 AlevelScheduleSession 列表。
        
        Returns:
            List[AlevelScheduleSession]: A-Level 排课会话列表
        """
        # 查询活跃的课程班
        course_classes = self.db.query(self.CourseClassORM).filter(
            self.CourseClassORM.is_deleted == False,
            self.CourseClassORM.status == "ACTIVE",
            self.CourseClassORM.teacher_id.isnot(None)  # 必须有教师
        ).all()
        
        if not course_classes:
            return []
        
        # 查询所有成员（按课程班分组）
        class_ids = [cc.id for cc in course_classes]
        members = self.db.query(self.MemberORM).filter(
            self.MemberORM.course_class_id.in_(class_ids),
            self.MemberORM.status == "ENROLLED"
        ).all()
        
        # 按课程班ID分组学生
        class_students: dict[int, list[int]] = {}
        for m in members:
            class_students.setdefault(m.course_class_id, []).append(m.student_id)
        
        # 查询科目信息（获取 weekly_hours）
        subject_ids = list({cc.alevel_subject_id for cc in course_classes})
        subjects = self.db.query(self.AlevelSubjectORM).filter(
            self.AlevelSubjectORM.id.in_(subject_ids),
            self.AlevelSubjectORM.is_deleted == False
        ).all()
        subject_hours = {s.id: s.weekly_hours for s in subjects}
        
        # 查询学生年级，用于判断 G10 课程是否限制选修课时段
        from app.modules.students.models import Student as StudentORM
        all_student_ids = list(set(
            sid for ids in class_students.values() for sid in ids
        ))
        student_grades = {}
        if all_student_ids:
            for s in self.db.query(StudentORM).filter(StudentORM.id.in_(all_student_ids)).all():
                student_grades[s.id] = s.grade
        
        sessions = []
        for cc in course_classes:
            student_ids = class_students.get(cc.id, [])
            if not student_ids:
                continue  # 没有学生的课程班不排课
            
            weekly_hours = subject_hours.get(cc.alevel_subject_id, 2)
            
            # 若课程班包含 G10 学生，不强制优先选修课时段
            has_g10 = any(student_grades.get(sid) == "G10" for sid in student_ids)
            
            sessions.append(AlevelScheduleSession(
                course_class_id=cc.id,
                teacher_id=cc.teacher_id,
                student_ids=student_ids,
                aleve_subject_id=cc.alevel_subject_id,
                weekly_hours=weekly_hours,
                duration=1,  # 默认单节，可后续扩展为连堂
                required_venue_type=None,  # A-Level 课程暂不考虑场地限制
                department="SENIOR",
                priority=100,  # A-Level 课程优先级较高
                prefer_elective_slots=not has_g10,
            ))
        
        print(f"    A-Level 课程班: {len(sessions)} 个")
        return sessions


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
