from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.compat import PortableArray


class LayerGroup(Base):
    """
    分层/合班课程模型 (The 'Big Rock')
    
    支持两种模式：
    1. LAYER (分层)：多个老师同时教不同层；范围由 layer_scope 决定
       - GRADE：同年级内多班参与
       - CROSS_GRADE：跨年级混排
       - SINGLE_CLASS：单一班级内分层
    2. COMBINE (合班)：年级内指定班级合并上课，同一个老师教
    
    分层示例：G6 数学分层，3层3个老师，G6所有班级学生参与
    合班示例：G6-1 和 G6-2 合班上体育，1个老师教两个班
    """
    __tablename__ = "layer_groups"

    id = Column(Integer, primary_key=True, index=True)
    
    # 课程类型：LAYER=分层, COMBINE=合班
    group_type = Column(String(20), default="LAYER", nullable=False,
                       comment="类型：LAYER=分层课程, COMBINE=合班上课")
    
    # 关联科目 (如: 英语)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    
    # 适用年级 (如: ["G6", "G7"])，分层模式必填
    grades = Column(PortableArray(item_type="string"), nullable=False)
    
    # 合班时指定的班级ID列表，合班模式必填
    class_ids = Column(PortableArray(item_type="integer"), nullable=True, default=[],
                      comment="合班时指定的班级ID列表")
    
    # 分层数量 (需要几位老师同时上课)，分层模式使用
    layer_count = Column(Integer, nullable=False)
    
    # 每层对应的教师ID列表
    # 分层模式：数组长度与 layer_count 相同，每层一个老师
    # 合班模式：数组长度为1，只有一个老师
    teacher_ids = Column(PortableArray(item_type="integer"), nullable=True, default=[])
    
    # 分层范围（仅 LAYER 模式）：GRADE / CROSS_GRADE / SINGLE_CLASS
    layer_scope = Column(String(20), default="GRADE", nullable=False,
                        comment="分层范围：GRADE=同年级, CROSS_GRADE=跨年级, SINGLE_CLASS=单班")

    # 是否跨年级（兼容旧接口；与 layer_scope=CROSS_GRADE 等价）
    is_cross_grade = Column(Boolean, default=False)
    
    # 每周课时数
    weekly_hours = Column(Integer, nullable=False)
    
    # 是否需要连堂 (如: 2节连上)
    needs_continuous = Column(Boolean, default=False)
    
    # 备注
    description = Column(Text, nullable=True)

    # 关系
    subject = relationship("Subject")
