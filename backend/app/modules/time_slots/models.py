"""
========================================
时间槽配置数据库模型
========================================

存储各学部（小学部/中学部/高中部）在不同星期几的课程时间槽定义。

用途：
1. 为排课引擎提供精确的时间槽数据（替代硬编码）
2. 支持跨学部教师的时间约束正确映射
3. 为前端课表显示提供真实时间段标签

设计要点：
- 每个学部 × 每天类型（周一/周二~四/周五）× 每节课 = 一条记录
- department + day_type + period_num 联合唯一
- 使用 TIME 类型存储起止时间，便于排序和计算
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Time, UniqueConstraint
from sqlalchemy.sql import func
from app.core.database import Base


class TimeSlotConfig(Base):
    """
    时间槽配置模型

    对应数据库中的 time_slot_configs 表。

    示例数据：
        小学部(PRIMARY) 周一(MONDAY) 第1节(1) 08:40-09:20 正课(class)
        中学部(SECONDARY) 周二~四(TUE_THU) 第5节(5) 11:40-12:20 正课(class)
        高中部(SENIOR) 周一~四(MON_THU) 第10节(10) 16:40-17:20 选修(elective)
    """

    __tablename__ = "time_slot_configs"

    # 主键
    id = Column(
        Integer,
        primary_key=True,
        index=True,
        autoincrement=True,
        comment="配置ID，主键"
    )

    # 学部代码：PRIMARY / SECONDARY / SENIOR
    # PRIMARY = 小学部 (PK, KG, G1-G5)
    # SECONDARY = 中学部 (G6-G9)
    # SENIOR = 高中部 (G10-G12, A-Level)
    department = Column(
        String(20),
        nullable=False,
        comment="学部：PRIMARY=小学部，SECONDARY=中学部，SENIOR=高中部"
    )

    # 星期类型：区分不同星期的作息差异
    # MONDAY = 周一（小学/中学第一节推迟 20 分钟）
    # TUE_THU = 周二~周四（标准作息）
    # FRIDAY = 周五（提前放学，下午大课间缩短）
    # MON_THU = 周一~周四（高中部专用，含晚自习）
    day_type = Column(
        String(20),
        nullable=False,
        comment="星期类型：MONDAY=周一, TUE_THU=周二~四, FRIDAY=周五, MON_THU=周一~四"
    )

    # 节次编号：1, 2, 3, ...
    # 小学部最大 8，中学部最大 9（周五 8），高中部最大 13（周一~四）/ 8（周五）
    period_num = Column(
        Integer,
        nullable=False,
        comment="节次编号（1-based）"
    )

    # 节次名称：如"第1节课"、"第10节课(选修课)"、"第12节课(晚自习)"
    period_name = Column(
        String(50),
        nullable=False,
        comment="节次名称"
    )

    # 开始时间（如 08:40:00）
    start_time = Column(
        Time,
        nullable=False,
        comment="开始时间"
    )

    # 结束时间（如 09:20:00）
    end_time = Column(
        Time,
        nullable=False,
        comment="结束时间"
    )

    # 时段类型
    # class = 正课（常规课程）
    # elective = 选修课（高中部第10-11节）
    # self_study = 自习/晚自习（高中部第12-13节）
    # break = 大课间/午休（不可排课，仅作为时间标注）
    period_type = Column(
        String(20),
        nullable=False,
        default="class",
        comment="时段类型：class=正课, elective=选修, self_study=自习, break=休息"
    )

    # 是否启用：支持未来灵活调整（如临时调整作息）
    is_active = Column(
        Boolean,
        default=True,
        comment="是否启用"
    )

    # 系统字段
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="创建时间"
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="更新时间"
    )

    # 联合唯一约束：同一学部同一天同一节次只能有一条记录
    __table_args__ = (
        UniqueConstraint(
            'department', 'day_type', 'period_num',
            name='uq_time_slot_dept_day_period'
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<TimeSlotConfig("
            f"dept={self.department}, "
            f"day={self.day_type}, "
            f"period={self.period_num}, "
            f"time={self.start_time.strftime('%H:%M')}-{self.end_time.strftime('%H:%M')}"
            f")>"
        )
