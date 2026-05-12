"""
排课引擎数据层

提供与数据库解耦的数据模型和数据加载器。
"""

from .models import (
    Teacher,
    Class,
    Subject,
    Task,
    LayerGroup,
    Venue,
    ScheduleRecord,
    ScheduleData
)

from .loader import DatabaseLoader, load_schedule_data
from .mock import (
    MockConfig,
    MockDataGenerator,
    generate_mock_data,
    generate_simple_test_data,
    generate_full_test_data
)

from .test_school_config import generate_real_school_data

__all__ = [
    # 数据模型
    'Teacher',
    'Class', 
    'Subject',
    'Task',
    'LayerGroup',
    'Venue',
    'ScheduleRecord',
    'ScheduleData',
    # 数据加载
    'DatabaseLoader',
    'load_schedule_data',
    # 模拟数据
    'MockConfig',
    'MockDataGenerator',
    'generate_mock_data',
    'generate_simple_test_data',
    'generate_full_test_data',
    # 真实学校配置
    'generate_real_school_data',
]
