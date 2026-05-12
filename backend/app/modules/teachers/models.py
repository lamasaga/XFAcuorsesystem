"""
========================================
教师数据库模型
========================================

这个文件定义了教师表（teachers）在数据库中的结构。

SQLAlchemy 模型的概念：
- 一个 Python 类对应数据库中的一张表
- 类的属性对应表的列
- 类的实例对应表中的一行数据

例如：
    Teacher 类 → teachers 表
    Teacher.name 属性 → teachers 表的 name 列
    Teacher(name="张三") → teachers 表中的一条记录

常用的列类型：
- Integer: 整数
- String(n): 最大长度为 n 的字符串
- Boolean: 布尔值
- DateTime: 日期时间
- Text: 长文本
- JSON: JSON 数据

常用的列参数：
- primary_key=True: 主键
- nullable=False: 不允许为空
- unique=True: 值必须唯一
- default=值: 默认值
- index=True: 创建索引，加快查询速度
"""

# -----------------------------------------
# 导入必要的模块
# -----------------------------------------
# Column: 定义表的列
# Integer, String 等: 列的数据类型
from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, ForeignKey

# func: SQL 函数，如 func.now() 获取当前时间
from sqlalchemy.sql import func

# 跨数据库兼容的数组类型
from app.core.compat import PortableArray

# 导入模型基类
from app.core.database import Base


# -----------------------------------------
# 教研组模型定义
# -----------------------------------------
class ResearchGroup(Base):
    """教研组数据模型"""
    __tablename__ = "research_groups"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(50), nullable=False, unique=True, comment="教研组名称")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_deleted = Column(Boolean, default=False)

    def __repr__(self) -> str:
        return f"<ResearchGroup(id={self.id}, name='{self.name}')>"


# -----------------------------------------
# 教师模型定义
# -----------------------------------------
class Teacher(Base):
    """
    教师数据模型
    
    对应数据库中的 teachers 表，存储所有教师的信息。
    
    表结构说明：
    - id: 主键，自增
    - name: 教师姓名
    - type: 教师类型（CN=中教，EN=外教）
    - department: 所属学部（PRIMARY=小学部，SECONDARY=中学部）
    - subjects: 任教科目列表
    - tags: 标签列表（如 HOMEROOM_TEACHER=班主任）
    - max_weekly_hours: 每周最大课时数
    - created_at: 创建时间
    - updated_at: 更新时间
    - is_deleted: 是否已删除（软删除标记）
    
    Attributes:
        __tablename__ (str): 数据库表名
    """
    
    # 数据库表名
    # 注意：表名通常使用复数形式（teachers 而不是 teacher）
    __tablename__ = "teachers"
    
    # -----------------------------------------
    # 主键
    # -----------------------------------------
    # id: 教师的唯一标识符
    # primary_key=True: 设为主键
    # index=True: 创建索引，加快按 id 查询的速度
    # autoincrement=True: 自动递增
    id = Column(
        Integer,
        primary_key=True,
        index=True,
        autoincrement=True,
        comment="教师ID，主键"
    )
    
    # -----------------------------------------
    # 基本信息
    # -----------------------------------------
    # name: 教师姓名
    # String(50): 最大 50 个字符
    # nullable=False: 不允许为空
    name = Column(
        String(50),
        nullable=False,
        comment="教师姓名"
    )
    
    # type: 教师类型
    # CN = 中教（Chinese Teacher）
    # EN = 外教（English/Foreign Teacher）
    type = Column(
        String(2),
        nullable=False,
        default="CN",
        comment="教师类型：CN=中教，EN=外教"
    )
    
    # department: 所属学部
    # PRIMARY = 小学部
    # SECONDARY = 中学部
    # BOTH = 小中贯通（可在小学部和中学部同时任教）
    department = Column(
        String(20),
        nullable=False,
        default="PRIMARY",
        comment="所属学部：PRIMARY=小学部，SECONDARY=中学部，BOTH=小中贯通"
    )
    
    # -----------------------------------------
    # 教学相关
    # -----------------------------------------
    # subjects: 任教科目列表
    # 使用 PostgreSQL 的数组类型存储多个科目
    # 例如：["语文", "数学"]
    subjects = Column(
        PortableArray(item_type="string"),
        default=[],
        comment="任教科目列表"
    )
    
    # tags: 教师标签
    # 用于标记特殊角色，如班主任、管理干部等
    # 可能的值：
    # - HOMEROOM_TEACHER: 班主任
    # - ASSISTANT_HOMEROOM: 副班主任
    # - PRIMARY_ADMIN: 小学管理干部
    # - SECONDARY_ADMIN: 中学管理干部
    tags = Column(
        PortableArray(item_type="string"),
        default=[],
        comment="教师标签：HOMEROOM_TEACHER=班主任等"
    )
    
    # max_weekly_hours: 每周最大课时数
    # 用于排课时限制教师的总课时
    max_weekly_hours = Column(
        Integer,
        default=25,
        comment="每周最大课时数"
    )
    
    # weekly_hours: 当前已安排的周课时数
    weekly_hours = Column(
        Integer,
        default=0,
        comment="当前已安排的周课时数"
    )
    
    # -----------------------------------------
    # 时间限制
    # -----------------------------------------
    # unavailable_slots: 不可用时间槽
    # JSON 格式，存储教师不能上课的时间
    # 格式：{"1": [1, 2], "3": [5, 6]}
    # 表示：周一第1、2节不可用，周三第5、6节不可用
    unavailable_slots = Column(
        JSON,
        default={},
        comment="不可用时间槽，JSON格式"
    )
    
    # daily_shifts: 每日班次状态
    # JSON 格式，存储每天是早班还是晚班
    # 格式：{"1": "morning", "2": "morning", "3": "evening", "4": "evening", "5": "morning"}
    # morning = 早班（全天可用）
    # evening = 晚班（上午不可用，小学部第1-5节不可用，中学部第1-4节不可用）
    daily_shifts = Column(
        JSON,
        default={"1": "morning", "2": "morning", "3": "morning", "4": "morning", "5": "morning"},
        comment="每日班次状态：morning=早班, evening=晚班"
    )
    
    # -----------------------------------------
    # 教研组
    # -----------------------------------------
    research_group_id = Column(
        Integer,
        ForeignKey("research_groups.id"),
        nullable=True,
        comment="所属教研组ID"
    )

    # -----------------------------------------
    # 系统字段
    # -----------------------------------------
    # created_at: 记录创建时间
    # server_default=func.now(): 由数据库自动填充当前时间
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="创建时间"
    )
    
    # updated_at: 记录更新时间
    # onupdate=func.now(): 每次更新记录时自动更新为当前时间
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="更新时间"
    )
    
    # is_deleted: 软删除标记
    # True: 已删除（不会真正从数据库中删除）
    # False: 正常状态
    is_deleted = Column(
        Boolean,
        default=False,
        comment="是否已删除（软删除）"
    )
    
    # -----------------------------------------
    # 对象表示方法
    # -----------------------------------------
    def __repr__(self) -> str:
        """
        返回对象的字符串表示
        
        当打印 Teacher 对象时，显示有意义的信息。
        
        Returns:
            str: 对象的字符串表示
        
        Example:
            >>> teacher = Teacher(id=1, name="张三")
            >>> print(teacher)
            <Teacher(id=1, name='张三', type='CN')>
        """
        return f"<Teacher(id={self.id}, name='{self.name}', type='{self.type}')>"
