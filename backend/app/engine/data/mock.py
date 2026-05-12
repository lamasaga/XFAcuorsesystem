"""
模拟数据生成器

用于测试排课算法，无需数据库即可运行。
生成符合学校实际结构的模拟数据。
"""

import random
from typing import List, Optional, Dict
from dataclasses import dataclass

from .models import (
    Teacher, Class, Subject, Task, LayerGroup, Venue, ScheduleData
)


@dataclass
class MockConfig:
    """
    模拟数据配置
    
    Attributes:
        grades: 要生成的年级列表
        classes_per_grade: 每个年级的班级数
        cn_teachers: 中教数量
        en_teachers: 外教数量
        include_layers: 是否包含分层课
        include_venues: 是否包含场地限制
        seed: 随机数种子（用于可重复的测试）
    """
    grades: List[str] = None
    classes_per_grade: int = 2
    cn_teachers: int = 20
    en_teachers: int = 10
    include_layers: bool = True
    include_venues: bool = True
    seed: Optional[int] = None
    
    def __post_init__(self):
        if self.grades is None:
            # 默认包含小学部和部分中学部
            self.grades = ['G1', 'G2', 'G3', 'G4', 'G5', 'G6']


class MockDataGenerator:
    """
    模拟数据生成器
    
    生成用于测试的模拟排课数据。
    
    Usage:
        generator = MockDataGenerator()
        data = generator.generate()
        
        # 或使用自定义配置
        config = MockConfig(grades=['G1', 'G2'], classes_per_grade=3)
        data = generator.generate(config)
    """
    
    # 科目定义
    SUBJECTS = [
        {"code": "CHINESE", "name": "语文", "category": "文化课", "is_main": True, "color": "#ef4444"},
        {"code": "MATH_CN", "name": "数学(中)", "category": "文化课", "is_main": True, "color": "#3b82f6"},
        {"code": "MATH_EN", "name": "数学(外)", "category": "文化课", "is_main": True, "color": "#2563eb"},
        {"code": "ENGLISH_CN", "name": "英语(中)", "category": "文化课", "is_main": True, "color": "#f59e0b"},
        {"code": "ENGLISH_EN", "name": "英语(外)", "category": "文化课", "is_main": True, "color": "#d97706"},
        {"code": "SCIENCE", "name": "科学", "category": "综合", "is_main": False, "color": "#10b981"},
        {"code": "PE", "name": "体育", "category": "体育", "is_main": False, "color": "#22c55e", "venue": "体育场"},
        {"code": "MUSIC", "name": "音乐", "category": "艺术", "is_main": False, "color": "#8b5cf6"},
        {"code": "ART", "name": "美术", "category": "艺术", "is_main": False, "color": "#ec4899", "venue": "美术教室"},
        {"code": "IPC", "name": "IPC", "category": "综合", "is_main": False, "color": "#06b6d4"},
        {"code": "LIBRARY", "name": "图书馆", "category": "综合", "is_main": False, "color": "#84cc16"},
        {"code": "MORAL", "name": "品德", "category": "综合", "is_main": False, "color": "#14b8a6"},
    ]
    
    # 中教姓名库
    CN_NAMES = [
        "张伟", "王芳", "李娜", "刘洋", "陈静", "杨磊", "赵敏", "黄丽",
        "周杰", "吴婷", "徐明", "孙艳", "马超", "朱红", "胡军", "郭芳",
        "林峰", "何欣", "高强", "罗敏", "郑伟", "梁静", "谢涛", "宋佳",
        "唐亮", "韩雪", "曹刚", "冯晶", "董艳", "程明"
    ]
    
    # 外教姓名库
    EN_NAMES = [
        "John", "Emma", "Michael", "Sarah", "David", "Jessica", "James", "Emily",
        "Robert", "Ashley", "William", "Amanda", "Richard", "Jennifer", "Thomas", "Nicole",
        "Andrew", "Rachel", "Daniel", "Stephanie"
    ]
    
    # 各年级课时配置
    GRADE_HOURS = {
        "PK": {"语文": 10, "数学(中)": 6, "英语(外)": 8, "体育": 4, "音乐": 2, "美术": 2},
        "KG": {"语文": 10, "数学(中)": 6, "英语(外)": 10, "体育": 4, "音乐": 2, "美术": 2},
        "G1": {"语文": 9, "数学(中)": 7, "数学(外)": 1, "英语(外)": 8, "科学": 2, "体育": 4, "音乐": 2, "美术": 2, "IPC": 2, "图书馆": 1, "品德": 2},
        "G2": {"语文": 9, "数学(中)": 7, "数学(外)": 1, "英语(外)": 8, "科学": 2, "体育": 4, "音乐": 2, "美术": 2, "IPC": 2, "图书馆": 1, "品德": 2},
        "G3": {"语文": 8, "数学(中)": 6, "数学(外)": 2, "英语(外)": 8, "科学": 3, "体育": 4, "音乐": 2, "美术": 2, "IPC": 2, "图书馆": 1, "品德": 2},
        "G4": {"语文": 8, "数学(中)": 6, "数学(外)": 2, "英语(外)": 8, "科学": 3, "体育": 4, "音乐": 2, "美术": 2, "IPC": 2, "图书馆": 1, "品德": 2},
        "G5": {"语文": 7, "数学(中)": 6, "数学(外)": 2, "英语(外)": 8, "科学": 4, "体育": 4, "音乐": 2, "美术": 2, "IPC": 2, "图书馆": 1, "品德": 2},
        "G6": {"语文": 6, "数学(中)": 5, "数学(外)": 2, "英语(外)": 7, "科学": 5, "体育": 3, "音乐": 2, "美术": 2, "IPC": 2, "图书馆": 1, "品德": 2},
        "G7": {"语文": 6, "数学(中)": 5, "数学(外)": 2, "英语(外)": 7, "科学": 5, "体育": 3, "音乐": 2, "美术": 2, "IPC": 2, "图书馆": 1},
        "G8": {"语文": 5, "数学(中)": 5, "数学(外)": 2, "英语(外)": 6, "科学": 6, "体育": 3, "音乐": 2, "美术": 2},
    }
    
    def __init__(self):
        self._next_id = {
            'teacher': 1,
            'class': 1,
            'subject': 1,
            'task': 1,
            'layer_group': 1,
            'venue': 1
        }
    
    def _get_next_id(self, entity_type: str) -> int:
        """获取下一个ID"""
        id_val = self._next_id[entity_type]
        self._next_id[entity_type] += 1
        return id_val
    
    def generate(self, config: MockConfig = None) -> ScheduleData:
        """
        生成模拟数据
        
        Args:
            config: 配置对象，为None时使用默认配置
            
        Returns:
            ScheduleData: 生成的数据集
        """
        if config is None:
            config = MockConfig()
        
        # 设置随机数种子
        if config.seed is not None:
            random.seed(config.seed)
        
        # 生成各类数据
        subjects = self._generate_subjects()
        venues = self._generate_venues(config) if config.include_venues else []
        teachers = self._generate_teachers(config, subjects)
        classes = self._generate_classes(config)
        layer_groups = self._generate_layer_groups(config, subjects) if config.include_layers else []
        tasks = self._generate_tasks(config, teachers, classes, subjects, layer_groups)
        
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
    
    def _generate_subjects(self) -> List[Subject]:
        """生成科目"""
        subjects = []
        for s in self.SUBJECTS:
            subject = Subject(
                id=self._get_next_id('subject'),
                code=s["code"],
                name=s["name"],
                category=s["category"],
                is_main=s["is_main"],
                required_room_type=s.get("venue"),
                color=s["color"]
            )
            subjects.append(subject)
        return subjects
    
    def _generate_venues(self, config: MockConfig) -> List[Venue]:
        """生成场地"""
        venues = [
            Venue(
                id=self._get_next_id('venue'),
                name="体育场",
                capacity=4,  # 同时可以上4个班的体育课
                subjects=["体育"]
            ),
            Venue(
                id=self._get_next_id('venue'),
                name="美术教室1",
                capacity=1,
                subjects=["美术"]
            ),
            Venue(
                id=self._get_next_id('venue'),
                name="美术教室2",
                capacity=1,
                subjects=["美术"]
            ),
            Venue(
                id=self._get_next_id('venue'),
                name="音乐教室",
                capacity=2,
                subjects=["音乐"]
            ),
            Venue(
                id=self._get_next_id('venue'),
                name="科学实验室",
                capacity=2,
                subjects=["科学"]
            ),
        ]
        return venues
    
    def _generate_teachers(
        self,
        config: MockConfig,
        subjects: List[Subject]
    ) -> List[Teacher]:
        """生成教师"""
        teachers = []
        subject_map = {s.name: s for s in subjects}
        
        # 生成中教
        cn_subjects = ["语文", "数学(中)", "英语(中)", "科学", "品德", "音乐", "美术", "体育"]
        cn_names = random.sample(self.CN_NAMES, min(config.cn_teachers, len(self.CN_NAMES)))
        
        for i, name in enumerate(cn_names):
            # 分配科目（每个老师1-2门）
            available_subjects = [s for s in cn_subjects if s in subject_map]
            teacher_subjects = random.sample(available_subjects, min(2, len(available_subjects)))
            
            teacher = Teacher(
                id=self._get_next_id('teacher'),
                name=name,
                type="CN",
                department="PRIMARY" if i < config.cn_teachers // 2 else "SECONDARY",
                subjects=teacher_subjects,
                max_weekly_hours=22,
                tags=["HOMEROOM_TEACHER"] if i < len(config.grades) * config.classes_per_grade else []
            )
            teachers.append(teacher)
        
        # 生成外教
        en_subjects = ["数学(外)", "英语(外)", "IPC", "图书馆", "科学"]
        en_names = random.sample(self.EN_NAMES, min(config.en_teachers, len(self.EN_NAMES)))
        
        for i, name in enumerate(en_names):
            available_subjects = [s for s in en_subjects if s in subject_map]
            teacher_subjects = random.sample(available_subjects, min(2, len(available_subjects)))
            
            teacher = Teacher(
                id=self._get_next_id('teacher'),
                name=name,
                type="EN",
                department="PRIMARY" if i < config.en_teachers // 2 else "SECONDARY",
                subjects=teacher_subjects,
                max_weekly_hours=18,
                tags=["HOMEROOM_TEACHER"] if i < len(config.grades) * config.classes_per_grade else []
            )
            teachers.append(teacher)
        
        return teachers
    
    def _generate_classes(self, config: MockConfig) -> List[Class]:
        """生成班级"""
        classes = []
        
        for grade in config.grades:
            department = "PRIMARY" if grade in ['PK', 'KG', 'G1', 'G2', 'G3', 'G4', 'G5'] else "SECONDARY"
            
            for class_no in range(1, config.classes_per_grade + 1):
                # 交替生成 I 类和 N 类班级
                class_type = "I" if class_no % 2 == 1 else "N"
                
                cls = Class(
                    id=self._get_next_id('class'),
                    name=f"{class_type}{grade}-{class_no}",
                    type=class_type,
                    grade=grade,
                    class_no=class_no,
                    department=department
                )
                classes.append(cls)
        
        return classes
    
    def _generate_layer_groups(
        self,
        config: MockConfig,
        subjects: List[Subject]
    ) -> List[LayerGroup]:
        """生成分层组"""
        groups = []
        subject_map = {s.name: s for s in subjects}
        
        # 数学分层：G3及以上，同年级分2层
        math_subject = subject_map.get("数学(中)")
        if math_subject:
            for grade in config.grades:
                if grade in ['G3', 'G4', 'G5', 'G6', 'G7', 'G8']:
                    group = LayerGroup(
                        id=self._get_next_id('layer_group'),
                        subject_id=math_subject.id,
                        subject_name=math_subject.name,
                        grades=[grade],
                        layer_count=2,  # 分2层
                        is_cross_grade=False,
                        weekly_hours=6,
                        needs_continuous=True
                    )
                    groups.append(group)
        
        # 英语分层：G6-G7 跨年级分3层
        english_subject = subject_map.get("英语(外)")
        if english_subject:
            g6_g7_grades = [g for g in config.grades if g in ['G6', 'G7']]
            if len(g6_g7_grades) >= 2:
                group = LayerGroup(
                    id=self._get_next_id('layer_group'),
                    subject_id=english_subject.id,
                    subject_name=english_subject.name,
                    grades=g6_g7_grades,
                    layer_count=3,  # 跨年级分3层
                    is_cross_grade=True,
                    weekly_hours=7,
                    needs_continuous=False
                )
                groups.append(group)
        
        return groups
    
    def _generate_tasks(
        self,
        config: MockConfig,
        teachers: List[Teacher],
        classes: List[Class],
        subjects: List[Subject],
        layer_groups: List[LayerGroup]
    ) -> List[Task]:
        """生成教学任务"""
        tasks = []
        subject_map = {s.name: s for s in subjects}
        
        # 按科目类型分组教师
        teachers_by_subject: Dict[str, List[Teacher]] = {}
        for teacher in teachers:
            for subj in teacher.subjects:
                if subj not in teachers_by_subject:
                    teachers_by_subject[subj] = []
                teachers_by_subject[subj].append(teacher)
        
        # 为每个班级生成教学任务
        for cls in classes:
            # 获取该年级的课时配置
            grade_hours = self.GRADE_HOURS.get(cls.grade, self.GRADE_HOURS.get('G1', {}))
            
            for subject_name, hours in grade_hours.items():
                subject = subject_map.get(subject_name)
                if not subject:
                    continue
                
                # 分配教师
                available_teachers = teachers_by_subject.get(subject_name, [])
                if not available_teachers:
                    continue
                
                teacher = random.choice(available_teachers)
                
                # 确定是否需要连堂
                is_continuous = subject.is_main and hours >= 4
                continuous_count = 2 if is_continuous else 1
                
                # 检查是否属于分层组
                layer_group_id = None
                for lg in layer_groups:
                    if lg.subject_id == subject.id and cls.grade in lg.grades:
                        layer_group_id = lg.id
                        break
                
                task = Task(
                    id=self._get_next_id('task'),
                    teacher_id=teacher.id,
                    teacher_name=teacher.name,
                    class_id=cls.id,
                    class_name=cls.name,
                    subject_id=subject.id,
                    subject_name=subject.name,
                    weekly_hours=hours,
                    is_continuous=is_continuous,
                    continuous_count=continuous_count,
                    layer_group_id=layer_group_id,
                    preferred_period="MORNING" if subject.is_main else "ANY",
                    required_venue_type=subject.required_room_type
                )
                tasks.append(task)
                
                # 将任务添加到分层组
                if layer_group_id:
                    for lg in layer_groups:
                        if lg.id == layer_group_id:
                            lg.task_ids.append(task.id)
                            break
        
        # 设置任务优先级
        self._set_task_priorities(tasks, layer_groups)
        
        return tasks
    
    def _set_task_priorities(self, tasks: List[Task], layer_groups: List[LayerGroup]):
        """设置任务优先级"""
        layer_complexity = {lg.id: lg.complexity for lg in layer_groups}
        
        for task in tasks:
            priority = 0
            
            if task.layer_group_id:
                priority = 1000 + layer_complexity.get(task.layer_group_id, 0)
            elif task.required_venue_type:
                priority = 500
            elif task.is_continuous:
                priority = 200
            
            task.priority = priority


def generate_mock_data(
    grades: List[str] = None,
    classes_per_grade: int = 2,
    seed: int = None
) -> ScheduleData:
    """
    便捷函数：生成模拟数据
    
    Args:
        grades: 年级列表，默认 G1-G6
        classes_per_grade: 每年级班级数
        seed: 随机数种子
    
    Returns:
        ScheduleData: 生成的数据集
    """
    config = MockConfig(
        grades=grades,
        classes_per_grade=classes_per_grade,
        seed=seed
    )
    generator = MockDataGenerator()
    return generator.generate(config)


def generate_simple_test_data() -> ScheduleData:
    """
    生成简单的测试数据（用于单元测试）
    
    只包含2个年级，每年级1个班，便于快速测试。
    """
    config = MockConfig(
        grades=['G1', 'G2'],
        classes_per_grade=1,
        cn_teachers=5,
        en_teachers=3,
        include_layers=False,
        include_venues=False,
        seed=42
    )
    generator = MockDataGenerator()
    return generator.generate(config)


def generate_full_test_data() -> ScheduleData:
    """
    生成完整的测试数据（接近真实规模）
    
    包含完整的年级结构、分层课和场地限制。
    """
    config = MockConfig(
        grades=['G1', 'G2', 'G3', 'G4', 'G5', 'G6', 'G7', 'G8'],
        classes_per_grade=2,
        cn_teachers=30,
        en_teachers=15,
        include_layers=True,
        include_venues=True,
        seed=42
    )
    generator = MockDataGenerator()
    return generator.generate(config)
