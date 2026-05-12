from sqlalchemy import Column, Integer, String, Boolean, Text
from app.core.database import Base
from app.core.compat import PortableArray

class Venue(Base):
    """
    场地资源模型 (The 'Pebbles')
    
    代表受限的教学场地，如体育场、美术教室、钢琴房等。
    限制了同一时间段内可以进行的课程数量。
    """
    __tablename__ = "venues"

    id = Column(Integer, primary_key=True, index=True)
    
    # 场地名称 (如: 体育场, 钢琴教室)
    name = Column(String, nullable=False)
    
    # 容量 (同时能容纳多少个班级)
    capacity = Column(Integer, default=1)
    
    # 关联科目 (如: ["体育", "轮滑"])
    subjects = Column(PortableArray(item_type="string"), nullable=False)
    
    # 适用年级 (如: ["KG", "G1", "G2"], 空表示全适用)
    applicable_grades = Column(PortableArray(item_type="string"), nullable=True)
    
    # 备注
    description = Column(Text, nullable=True)
