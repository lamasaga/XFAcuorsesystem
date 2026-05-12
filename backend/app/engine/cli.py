#!/usr/bin/env python
"""
排课算法引擎命令行测试工具

用于测试和调试排课算法，无需启动完整的后端服务。

Usage:
    # 使用模拟数据测试
    python -m app.engine.cli --mock
    
    # 使用简单测试数据
    python -m app.engine.cli --mock --simple
    
    # 指定输出格式
    python -m app.engine.cli --mock --format markdown
    
    # 保存报告到文件
    python -m app.engine.cli --mock --output report.txt
    
    # 使用数据库数据
    python -m app.engine.cli --db
"""

import argparse
import sys
import time
from typing import Optional

# 确保可以正确导入模块
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def run_with_mock_data(
    simple: bool = False,
    seed: int = None,
    verbose: bool = False
) -> tuple:
    """
    使用模拟数据运行排课
    
    Args:
        simple: 使用简单测试数据
        seed: 随机数种子
        verbose: 详细输出
    
    Returns:
        tuple: (state, data, score_report)
    """
    from app.engine.data.mock import (
        generate_simple_test_data, 
        generate_full_test_data,
        generate_mock_data
    )
    from app.engine.state import ScheduleState
    from app.engine.utils.slot_finder import SlotFinder
    from app.engine.schedulers import LayerScheduler, VenueScheduler, NormalScheduler
    from app.engine.evaluation import ScheduleScorer
    
    # 生成数据
    print("=" * 60)
    print("排课算法引擎测试")
    print("=" * 60)
    print()
    
    print("[1/5] 生成测试数据...")
    if simple:
        data = generate_simple_test_data()
        print("  使用简单测试数据")
    else:
        data = generate_full_test_data() if seed is None else generate_mock_data(seed=seed)
        print("  使用完整测试数据")
    
    print(f"  - 教师: {len(data.teachers)} 人")
    print(f"  - 班级: {len(data.classes)} 个")
    print(f"  - 科目: {len(data.subjects)} 门")
    print(f"  - 教学任务: {len(data.tasks)} 个")
    print(f"  - 分层组: {len(data.layer_groups)} 个")
    print(f"  - 场地: {len(data.venues)} 个")
    print(f"  - 总周课时: {data.stats['total_weekly_hours']}")
    print()
    
    # 初始化状态
    print("[2/5] 初始化排课状态...")
    state = ScheduleState()
    state.stats["total_tasks"] = len(data.tasks)
    
    # 设置场地容量
    for venue in data.venues:
        for subject in venue.subjects:
            current = state.venue_capacities.get(subject, 0)
            state.set_venue_capacity(subject, current + venue.capacity)
    
    # 创建时间槽查找器
    slot_finder = SlotFinder(state, data)
    print("  完成")
    print()
    
    # 运行排课
    start_time = time.time()
    
    # 分层课
    print("[3/5] 运行分层课调度器...")
    layer_scheduler = LayerScheduler(state, slot_finder, data)
    layer_ids = layer_scheduler.schedule()
    print()
    
    # 场地课
    print("[4/5] 运行场地课调度器...")
    venue_scheduler = VenueScheduler(state, slot_finder, data)
    venue_ids = venue_scheduler.schedule()
    print()
    
    # 普通课
    print("[5/5] 运行普通课调度器...")
    normal_scheduler = NormalScheduler(state, slot_finder, data)
    normal_ids = normal_scheduler.schedule()
    print()
    
    elapsed_time = time.time() - start_time
    
    # 评分
    print("计算评分...")
    scorer = ScheduleScorer(state, data)
    score_report = scorer.score()
    print()
    
    # 输出摘要
    print("=" * 60)
    print("排课结果摘要")
    print("=" * 60)
    print(f"  运行时间: {elapsed_time:.2f} 秒")
    print(f"  分层课任务: {len(layer_ids)} 个")
    print(f"  场地课任务: {len(venue_ids)} 个")
    print(f"  普通课任务: {len(normal_ids)} 个")
    print(f"  总排课节数: {len(state.schedule_records)}")
    print()
    print(f"  评分: {score_report.total_score:.1f} ({score_report.level.value})")
    print()
    
    if verbose:
        print("详细评分:")
        for metric in score_report.metrics:
            print(f"  - {metric.name}: {metric.score:.1f} (权重 {metric.weight:.0%})")
        print()
    
    return state, data, score_report


def run_with_database():
    """使用数据库数据运行排课"""
    try:
        from app.core.database import SessionLocal
        from app.engine.data.loader import load_schedule_data
        from app.engine.state import ScheduleState
        from app.engine.utils.slot_finder import SlotFinder
        from app.engine.schedulers import LayerScheduler, VenueScheduler, NormalScheduler
        from app.engine.evaluation import ScheduleScorer
    except ImportError as e:
        print(f"错误: 无法导入数据库模块 - {e}")
        print("请确保数据库配置正确")
        return None, None, None
    
    print("=" * 60)
    print("排课算法引擎测试 (数据库模式)")
    print("=" * 60)
    print()
    
    print("连接数据库...")
    db = SessionLocal()
    
    try:
        print("加载数据...")
        data = load_schedule_data(db)
        
        print(f"  - 教师: {len(data.teachers)} 人")
        print(f"  - 班级: {len(data.classes)} 个")
        print(f"  - 任务: {len(data.tasks)} 个")
        print()
        
        # 初始化状态
        state = ScheduleState()
        state.stats["total_tasks"] = len(data.tasks)
        
        # 设置场地容量
        for venue in data.venues:
            for subject in venue.subjects:
                current = state.venue_capacities.get(subject, 0)
                state.set_venue_capacity(subject, current + venue.capacity)
        
        slot_finder = SlotFinder(state, data)
        
        # 运行排课
        start_time = time.time()
        
        layer_scheduler = LayerScheduler(state, slot_finder, data)
        layer_ids = layer_scheduler.schedule()
        
        venue_scheduler = VenueScheduler(state, slot_finder, data)
        venue_ids = venue_scheduler.schedule()
        
        normal_scheduler = NormalScheduler(state, slot_finder, data)
        normal_ids = normal_scheduler.schedule()
        
        elapsed_time = time.time() - start_time
        
        # 评分
        scorer = ScheduleScorer(state, data)
        score_report = scorer.score()
        
        print("=" * 60)
        print("排课结果摘要")
        print("=" * 60)
        print(f"  运行时间: {elapsed_time:.2f} 秒")
        print(f"  总排课节数: {len(state.schedule_records)}")
        print(f"  评分: {score_report.total_score:.1f}")
        
        return state, data, score_report
        
    finally:
        db.close()


def generate_report(
    state,
    data,
    score_report,
    format: str = "text",
    output: str = None
):
    """生成并输出报告"""
    from app.engine.evaluation import ScheduleReporter, ReportFormat
    
    format_map = {
        "text": ReportFormat.TEXT,
        "json": ReportFormat.JSON,
        "markdown": ReportFormat.MARKDOWN,
        "html": ReportFormat.HTML,
    }
    
    report_format = format_map.get(format.lower(), ReportFormat.TEXT)
    reporter = ScheduleReporter(state, data, score_report)
    report = reporter.generate_report(report_format)
    
    if output:
        with open(output, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"报告已保存到: {output}")
    else:
        print()
        print(report)


def main():
    parser = argparse.ArgumentParser(
        description="排课算法引擎命令行测试工具"
    )
    
    # 数据源
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        "--mock",
        action="store_true",
        help="使用模拟数据"
    )
    source_group.add_argument(
        "--db",
        action="store_true",
        help="使用数据库数据"
    )
    
    # 模拟数据选项
    parser.add_argument(
        "--simple",
        action="store_true",
        help="使用简单测试数据（仅用于 --mock）"
    )
    parser.add_argument(
        "--seed",
        type=int,
        help="随机数种子（仅用于 --mock）"
    )
    
    # 输出选项
    parser.add_argument(
        "--format",
        choices=["text", "json", "markdown", "html"],
        default="text",
        help="报告格式 (默认: text)"
    )
    parser.add_argument(
        "--output", "-o",
        help="输出文件路径"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="详细输出"
    )
    
    args = parser.parse_args()
    
    # 运行
    if args.mock:
        state, data, score_report = run_with_mock_data(
            simple=args.simple,
            seed=args.seed,
            verbose=args.verbose
        )
    else:
        state, data, score_report = run_with_database()
    
    if state is None:
        sys.exit(1)
    
    # 生成报告
    generate_report(
        state,
        data,
        score_report,
        format=args.format,
        output=args.output
    )


if __name__ == "__main__":
    main()
