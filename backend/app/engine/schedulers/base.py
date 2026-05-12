"""
调度器基类

所有具体的调度器（分层、场地、普通）都继承此类。
"""

from abc import ABC, abstractmethod
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from ..state import ScheduleState


class BaseScheduler(ABC):
    """
    调度器基类
    
    定义调度器的基本接口和通用功能。
    所有具体的调度器都应继承此类并实现 schedule 方法。
    
    Attributes:
        state: 课表状态管理器
        db: 数据库会话（可选）
    """
    
    def __init__(self, state: 'ScheduleState', db: 'Session' = None):
        """
        初始化调度器
        
        Args:
            state: 课表状态管理器
            db: 数据库会话（可选，用于直接查询数据库）
        """
        self.state = state
        self.db = db
    
    @abstractmethod
    def schedule(self) -> List[int]:
        """
        执行排课逻辑
        
        子类必须实现此方法。
        
        Returns:
            List[int]: 成功安排的 Task ID 列表
        """
        pass
    
    def get_stats(self) -> dict:
        """
        获取调度器统计信息
        
        Returns:
            dict: 统计信息
        """
        return self.state.get_schedule_summary()
