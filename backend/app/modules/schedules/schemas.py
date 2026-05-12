"""
排课请求和响应的数据模式定义
"""
from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class ScheduleRequest(BaseModel):
    """排课请求参数"""
    # 排课范围
    scope: Literal["all", "grade", "class"] = Field(
        default="all",
        description="排课范围: all=全校, grade=指定年级, class=指定班级"
    )
    grades: List[str] = Field(
        default=[],
        description="指定年级列表（scope=grade时使用）"
    )
    classes: List[int] = Field(
        default=[],
        description="指定班级ID列表（scope=class时使用）"
    )
    
    # 算法参数
    optimization: int = Field(
        default=3,
        ge=1,
        le=5,
        description="优化程度: 1=快速(约1分钟), 5=精细(约10分钟)"
    )
    plan_count: int = Field(
        default=1,
        ge=1,
        le=5,
        description="生成方案数量: 1/3/5"
    )
    
    # 其他选项
    keep_manual: bool = Field(
        default=False,
        description="是否保留已手动调整的课程位置"
    )
    debug: bool = Field(
        default=True,
        description="是否开启详细日志"
    )
    debug: bool = Field(
        default=True,
        description="是否开启详细日志"
    )


class SchedulePlanResult(BaseModel):
    """单个排课方案的结果"""
    schedule_id: int = Field(..., description="课表ID")
    score: int = Field(..., description="方案总分(0-100)")
    
    # 基本统计
    total_tasks: int = Field(..., description="总任务数")
    scheduled_tasks: int = Field(..., description="已排课任务数")
    failed_tasks: int = Field(..., description="未排课任务数")
    total_periods: int = Field(..., description="总排课节数")
    
    # 质量指标
    teacher_gaps: int = Field(default=0, description="教师空窗期数")
    main_morning_rate: float = Field(default=0, description="主科上午率(%)")
    continuous_rate: float = Field(default=0, description="连堂完整率(%)")
    distribution_score: float = Field(default=0, description="分布均衡度")
    
    # 执行信息
    duration_seconds: float = Field(default=0, description="排课耗时(秒)")
    recommended: bool = Field(default=False, description="是否为推荐方案")


class ScheduleResponse(BaseModel):
    """排课响应"""
    code: int = 200
    message: str = "排课成功"
    data: dict = Field(default_factory=dict)


class ScheduleConfigUpdate(BaseModel):
    """约束配置更新请求"""
    name: Optional[str] = Field(default="自定义配置", max_length=50, description="配置名称")
    config: dict = Field(default_factory=dict, description="约束配置JSON对象")
