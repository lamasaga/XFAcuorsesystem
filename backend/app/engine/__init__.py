"""
排课算法引擎

提供完整的排课功能，包括：
- 数据模型：与ORM解耦的内部数据结构
- 调度器：分层课、场地课、普通课三级调度
- 约束系统：硬约束检查和软约束评分
- 评估系统：排课质量评分和报告生成

Usage:
    # 使用模拟数据测试
    from app.engine.data.mock import generate_full_test_data
    from app.engine.state import ScheduleState
    from app.engine.utils.slot_finder import SlotFinder
    from app.engine.schedulers import LayerScheduler, VenueScheduler, NormalScheduler
    from app.engine.evaluation import ScheduleScorer
    
    # 生成数据
    data = generate_full_test_data()
    
    # 初始化状态
    state = ScheduleState()
    slot_finder = SlotFinder(state, data)
    
    # 运行排课
    layer_scheduler = LayerScheduler(state, slot_finder, data)
    layer_scheduler.schedule()
    
    venue_scheduler = VenueScheduler(state, slot_finder, data)
    venue_scheduler.schedule()
    
    normal_scheduler = NormalScheduler(state, slot_finder, data)
    normal_scheduler.schedule()
    
    # 评分
    scorer = ScheduleScorer(state, data)
    report = scorer.score()
    print(f"总分: {report.total_score}")

CLI:
    # 使用命令行工具测试
    python -m app.engine.cli --mock
    python -m app.engine.cli --mock --simple
    python -m app.engine.cli --db
"""

from .state import ScheduleState, ScheduleRecord

__all__ = [
    'ScheduleState',
    'ScheduleRecord',
]
