"""
排课引擎内部数据模型

与 SQLAlchemy ORM 解耦的纯 Python 数据类，用于算法内部处理。
这些模型专注于排课算法所需的属性，不依赖数据库。

设计原则：
1. 使用 dataclass 简化数据类定义
2. 所有字段都有明确的类型注解
3. 提供便捷的工厂方法从 ORM 对象转换
4. 支持 JSON 序列化用于测试和调试
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Set, Any
from enum import Enum


class TeacherType(Enum):
    """教师类型"""
    CN = "CN"  # 中教
    EN = "EN"  # 外教


class Department(Enum):
    """学部"""
    PRIMARY = "PRIMARY"      # 小学部
    SECONDARY = "SECONDARY"  # 中学部
    BOTH = "BOTH"            # 小中贯通（可同时在小学部和中学部任教）


class ClassType(Enum):
    """班级类型"""
    I = "I"  # 国际班
    N = "N"  # 综素班


class Period(Enum):
    """时段偏好"""
    MORNING = "MORNING"      # 上午
    AFTERNOON = "AFTERNOON"  # 下午
    ANY = "ANY"              # 任意


@dataclass
class Teacher:
    """
    教师数据模型
    
    Attributes:
        id: 教师ID
        name: 姓名
        type: 教师类型 (CN/EN)
        department: 所属学部
        subjects: 任教科目名称列表
        max_weekly_hours: 每周最大课时数
        unavailable_slots: 不可用时间槽 {day: [period1, period2, ...]}
        tags: 标签列表（如 HOMEROOM_TEACHER）
        daily_shifts: 每日班次状态 {"1": "morning", "2": "evening", ...}
    """
    id: int
    name: str
    type: str = "CN"
    department: str = "PRIMARY"
    subjects: List[str] = field(default_factory=list)
    max_weekly_hours: int = 25
    unavailable_slots: Dict[int, List[int]] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    daily_shifts: Dict[str, str] = field(default_factory=lambda: {
        "1": "morning", "2": "morning", "3": "morning", "4": "morning", "5": "morning"
    })
    research_group_id: Optional[int] = None
    
    @property
    def is_homeroom(self) -> bool:
        """是否是班主任"""
        return "HOMEROOM_TEACHER" in self.tags
    
    def _get_shift_unavailable(self, day: int) -> List[int]:
        """
        根据班次获取不可用时间段
        
        晚班规则：
        - 小学部晚班：上午（第1-5节）不可用
        - 中学部晚班：第1-4节不可用，可排第5节
        """
        shift = self.daily_shifts.get(str(day), "morning")
        if shift == "evening":
            if self.department == "PRIMARY":
                return [1, 2, 3, 4, 5]  # 小学部晚班：上午全部不可用
            else:
                return [1, 2, 3, 4]     # 中学部晚班：可排第5节
        return []
    
    def is_available(self, day: int, period: int) -> bool:
        """
        检查教师在指定时间是否可用
        
        同时检查手动设置的不可用时间和班次导致的不可用时间
        """
        # 先检查手动设置的不可用时间
        manual_unavailable = self.unavailable_slots.get(day, [])
        if period in manual_unavailable:
            return False
        # 再检查班次导致的不可用时间
        shift_unavailable = self._get_shift_unavailable(day)
        if period in shift_unavailable:
            return False
        return True
    
    @classmethod
    def from_orm(cls, obj) -> 'Teacher':
        """从 ORM 对象创建"""
        # JSON key 始终是字符串，但求解器使用整数 day 做 key
        raw_slots = obj.unavailable_slots or {}
        int_slots = {int(k): v for k, v in raw_slots.items()}
        return cls(
            id=obj.id,
            name=obj.name,
            type=obj.type,
            department=obj.department,
            subjects=obj.subjects or [],
            max_weekly_hours=obj.max_weekly_hours,
            unavailable_slots=int_slots,
            tags=obj.tags or [],
            daily_shifts=obj.daily_shifts or {
                "1": "morning", "2": "morning", "3": "morning", "4": "morning", "5": "morning"
            },
            research_group_id=getattr(obj, 'research_group_id', None),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


@dataclass
class Class:
    """
    班级数据模型
    
    Attributes:
        id: 班级ID
        name: 班级名称（如 IG3-1）
        type: 班级类型 (I/N)
        grade: 年级（PK/KG/G1-G12）
        class_no: 班级序号
        department: 学部
        homeroom_cn_id: 中教班主任ID
        homeroom_en_id: 外教班主任ID
    """
    id: int
    name: str
    type: str = "I"
    grade: str = "G1"
    class_no: int = 1
    department: str = "PRIMARY"
    homeroom_cn_id: Optional[int] = None
    homeroom_en_id: Optional[int] = None
    
    @property
    def grade_number(self) -> int:
        """获取年级数字（用于排序和比较）"""
        grade_order = {
            'PK': 0, 'KG': 1,
            'G1': 2, 'G2': 3, 'G3': 4, 'G4': 5, 'G5': 6,
            'G6': 7, 'G7': 8, 'G8': 9, 'G9': 10, 'G10': 11, 'G11': 12, 'G12': 13
        }
        return grade_order.get(self.grade, 0)
    
    @classmethod
    def from_orm(cls, obj) -> 'Class':
        """从 ORM 对象创建"""
        return cls(
            id=obj.id,
            name=obj.name,
            type=obj.type,
            grade=obj.grade,
            class_no=obj.class_no,
            department=obj.department,
            homeroom_cn_id=obj.homeroom_cn_id,
            homeroom_en_id=obj.homeroom_en_id
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


@dataclass
class Subject:
    """
    科目数据模型
    
    Attributes:
        id: 科目ID
        code: 科目代码
        name: 科目名称
        category: 分类（文化课/艺术/体育/综合）
        is_main: 是否主科
        required_room_type: 所需教室类型
        color: 显示颜色
    """
    id: int
    code: str
    name: str
    category: str = "文化课"
    is_main: bool = False
    required_room_type: Optional[str] = None
    color: str = "#3b82f6"
    
    @classmethod
    def from_orm(cls, obj) -> 'Subject':
        """从 ORM 对象创建"""
        return cls(
            id=obj.id,
            code=obj.code,
            name=obj.name,
            category=obj.category,
            is_main=obj.is_main,
            required_room_type=obj.required_room_type,
            color=obj.color
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


@dataclass
class Task:
    """
    教学任务数据模型（排课的基本单元）
    
    一个 Task 代表"某位教师给某个班级上某门课"的安排。
    排课算法的核心工作就是为每个 Task 分配时间槽。
    
    Attributes:
        id: 任务ID
        teacher_id: 教师ID
        teacher_name: 教师姓名（冗余，便于显示）
        class_id: 班级ID
        class_name: 班级名称（冗余，便于显示）
        subject_id: 科目ID
        subject_name: 科目名称（冗余，便于显示）
        weekly_hours: 每周课时数
        is_continuous: 是否需要连堂
        continuous_count: 连堂节数（默认2节）
        layer_group_id: 分层组ID（如果是分层课）
        preferred_period: 优先时段
        required_venue_type: 所需场地类型
        priority: 优先级（用于排序）
    """
    id: int
    teacher_id: int
    teacher_name: str
    class_id: int
    class_name: str
    subject_id: int
    subject_name: str
    weekly_hours: int
    is_continuous: bool = False
    continuous_count: int = 2
    layer_group_id: Optional[int] = None
    preferred_period: str = "ANY"
    required_venue_type: Optional[str] = None
    priority: int = 0  # 数字越大优先级越高
    
    @property
    def is_layer_task(self) -> bool:
        """是否是分层课任务"""
        return self.layer_group_id is not None
    
    @property
    def is_venue_limited(self) -> bool:
        """是否受场地限制"""
        return self.required_venue_type is not None
    
    @property
    def sessions_count(self) -> int:
        """
        计算需要排几次课
        
        例如：周6课时，连堂2节 -> 需要排3次（每次2节）
        例如：周5课时，不连堂 -> 需要排5次（每次1节）
        """
        if self.is_continuous and self.continuous_count > 1:
            # 连堂课：每次排 continuous_count 节
            return self.weekly_hours // self.continuous_count
        return self.weekly_hours
    
    @property
    def session_duration(self) -> int:
        """每次课的时长（节数）"""
        if self.is_continuous and self.continuous_count > 1:
            return self.continuous_count
        return 1
    
    @classmethod
    def from_orm(cls, obj, teacher_name: str = "", class_name: str = "", 
                 subject_name: str = "", venue_type: str = None) -> 'Task':
        """从 ORM 对象创建"""
        return cls(
            id=obj.id,
            teacher_id=obj.teacher_id,
            teacher_name=teacher_name,
            class_id=obj.class_id,
            class_name=class_name,
            subject_id=obj.subject_id,
            subject_name=subject_name,
            weekly_hours=obj.weekly_hours,
            is_continuous=obj.is_continuous,
            continuous_count=obj.continuous_count or 2,
            layer_group_id=obj.layer_group_id,
            preferred_period=obj.preferred_period or "ANY",
            required_venue_type=venue_type
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


@dataclass
class LayerGroup:
    """
    分层/合班课程数据模型
    
    支持两种模式：
    - LAYER（分层）：年级内所有班级参与，学生按能力分层，多个老师同时教不同层
    - COMBINE（合班）：年级内指定班级合并上课，同一个老师教
    
    分层示例：G6 数学分层，3层3个老师，G6所有班级学生参与
    合班示例：G6-1 和 G6-2 合班上体育，1个老师教两个班
    
    Attributes:
        id: 分层组ID
        group_type: 类型 LAYER=分层, COMBINE=合班
        subject_id: 关联科目ID
        subject_name: 科目名称
        grades: 适用年级列表（分层模式使用）
        class_ids: 指定班级ID列表（合班模式使用）
        layer_count: 分层数量（需要几位老师同时上）
        teacher_ids: 每层对应的教师ID列表
        is_cross_grade: 是否跨年级
        weekly_hours: 每周课时数
        needs_continuous: 是否需要连堂
        task_ids: 关联的任务ID列表（由系统自动创建）
    """
    id: int
    subject_id: int
    subject_name: str
    grades: List[str]
    layer_count: int
    group_type: str = "LAYER"  # LAYER 或 COMBINE
    class_ids: List[int] = field(default_factory=list)  # 合班时指定的班级
    teacher_ids: List[int] = field(default_factory=list)
    is_cross_grade: bool = False
    weekly_hours: int = 4
    needs_continuous: bool = False
    task_ids: List[int] = field(default_factory=list)
    
    @property
    def is_combine(self) -> bool:
        """是否是合班类型"""
        return self.group_type == "COMBINE"
    
    @property
    def complexity(self) -> int:
        """
        计算分层组的复杂度（用于排序）
        
        复杂度越高越难排，应该优先处理。
        """
        score = 0
        # 跨年级更复杂
        if self.is_cross_grade:
            score += 100
        # 分层数量越多越复杂
        score += self.layer_count * 20
        # 涉及年级越多越复杂
        score += len(self.grades) * 10
        # 合班涉及的班级数量
        score += len(self.class_ids) * 15
        return score
    
    @classmethod
    def from_orm(cls, obj, subject_name: str = "", task_ids: List[int] = None) -> 'LayerGroup':
        """从 ORM 对象创建"""
        return cls(
            id=obj.id,
            group_type=obj.group_type or "LAYER",
            subject_id=obj.subject_id,
            subject_name=subject_name,
            grades=obj.grades or [],
            class_ids=obj.class_ids or [],
            layer_count=obj.layer_count,
            teacher_ids=obj.teacher_ids or [],
            is_cross_grade=obj.is_cross_grade,
            weekly_hours=obj.weekly_hours,
            needs_continuous=obj.needs_continuous,
            task_ids=task_ids or []
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


@dataclass
class Venue:
    """
    场地数据模型
    
    Attributes:
        id: 场地ID
        name: 场地名称
        capacity: 容量（同时能容纳几个班）
        subjects: 关联科目列表
        applicable_grades: 适用年级列表（空表示全部适用）
    """
    id: int
    name: str
    capacity: int = 1
    subjects: List[str] = field(default_factory=list)
    applicable_grades: List[str] = field(default_factory=list)
    
    @classmethod
    def from_orm(cls, obj) -> 'Venue':
        """从 ORM 对象创建"""
        return cls(
            id=obj.id,
            name=obj.name,
            capacity=obj.capacity,
            subjects=obj.subjects or [],
            applicable_grades=obj.applicable_grades or []
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


@dataclass
class ScheduleRecord:
    """
    排课记录（算法输出的基本单元）
    
    记录一次成功的课程安排。
    
    Attributes:
        task_id: 任务ID
        teacher_id: 教师ID
        class_id: 班级ID
        subject_id: 科目ID
        day: 星期几（1-5）
        period: 第几节（1-9）
        duration: 持续节数（连堂课 > 1）
        layer_group_id: 分层组ID（如果是分层课）
    """
    task_id: int
    teacher_id: int
    class_id: int
    subject_id: int
    day: int
    period: int
    duration: int = 1
    layer_group_id: Optional[int] = None
    
    @property
    def time_slot(self) -> str:
        """返回时间槽描述"""
        days = ['', '周一', '周二', '周三', '周四', '周五']
        return f"{days[self.day]}第{self.period}节"
    
    @property
    def periods(self) -> List[int]:
        """返回占用的所有节次"""
        return list(range(self.period, self.period + self.duration))
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


@dataclass
class ScheduleData:
    """
    完整的排课数据集
    
    包含排课所需的所有输入数据，用于算法处理。
    """
    teachers: List[Teacher] = field(default_factory=list)
    classes: List[Class] = field(default_factory=list)
    subjects: List[Subject] = field(default_factory=list)
    tasks: List[Task] = field(default_factory=list)
    layer_groups: List[LayerGroup] = field(default_factory=list)
    venues: List[Venue] = field(default_factory=list)
    
    # 索引字典（便于快速查找）
    _teacher_map: Dict[int, Teacher] = field(default_factory=dict, repr=False)
    _class_map: Dict[int, Class] = field(default_factory=dict, repr=False)
    _subject_map: Dict[int, Subject] = field(default_factory=dict, repr=False)
    _task_map: Dict[int, Task] = field(default_factory=dict, repr=False)
    
    def __post_init__(self):
        """初始化后构建索引"""
        self.build_indexes()
    
    def build_indexes(self):
        """构建查找索引"""
        self._teacher_map = {t.id: t for t in self.teachers}
        self._class_map = {c.id: c for c in self.classes}
        self._subject_map = {s.id: s for s in self.subjects}
        self._task_map = {t.id: t for t in self.tasks}
    
    def get_teacher(self, teacher_id: int) -> Optional[Teacher]:
        """根据ID获取教师"""
        return self._teacher_map.get(teacher_id)
    
    def get_class(self, class_id: int) -> Optional[Class]:
        """根据ID获取班级"""
        return self._class_map.get(class_id)
    
    def get_subject(self, subject_id: int) -> Optional[Subject]:
        """根据ID获取科目"""
        return self._subject_map.get(subject_id)
    
    def get_task(self, task_id: int) -> Optional[Task]:
        """根据ID获取任务"""
        return self._task_map.get(task_id)
    
    def get_layer_tasks(self, layer_group_id: int) -> List[Task]:
        """获取分层组的所有任务"""
        return [t for t in self.tasks if t.layer_group_id == layer_group_id]
    
    def get_venue_limited_tasks(self) -> List[Task]:
        """获取所有受场地限制的任务"""
        return [t for t in self.tasks if t.is_venue_limited]
    
    def get_normal_tasks(self) -> List[Task]:
        """获取所有普通任务（非分层、非场地限制）"""
        return [t for t in self.tasks 
                if not t.is_layer_task and not t.is_venue_limited]
    
    def get_tasks_by_teacher(self, teacher_id: int) -> List[Task]:
        """获取某教师的所有任务"""
        return [t for t in self.tasks if t.teacher_id == teacher_id]
    
    def get_tasks_by_class(self, class_id: int) -> List[Task]:
        """获取某班级的所有任务"""
        return [t for t in self.tasks if t.class_id == class_id]
    
    def get_venue_capacity(self, venue_type: str) -> int:
        """获取某类型场地的总容量"""
        total = 0
        for venue in self.venues:
            if venue_type in venue.subjects:
                total += venue.capacity
        return total if total > 0 else 1  # 默认容量1
    
    @property
    def stats(self) -> Dict[str, int]:
        """获取数据统计"""
        return {
            "teachers": len(self.teachers),
            "classes": len(self.classes),
            "subjects": len(self.subjects),
            "tasks": len(self.tasks),
            "layer_groups": len(self.layer_groups),
            "venues": len(self.venues),
            "total_weekly_hours": sum(t.weekly_hours for t in self.tasks)
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于JSON序列化）"""
        return {
            "teachers": [t.to_dict() for t in self.teachers],
            "classes": [c.to_dict() for c in self.classes],
            "subjects": [s.to_dict() for s in self.subjects],
            "tasks": [t.to_dict() for t in self.tasks],
            "layer_groups": [lg.to_dict() for lg in self.layer_groups],
            "venues": [v.to_dict() for v in self.venues],
            "stats": self.stats
        }
