"""
排课评分系统

评估排课结果的质量，提供量化的评分指标。
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from collections import defaultdict
from enum import Enum

if TYPE_CHECKING:
    from ..state import ScheduleState, ScheduleRecord
    from ..data.models import ScheduleData


class ScoreLevel(Enum):
    """评分等级"""
    EXCELLENT = "excellent"  # 优秀 (90+)
    GOOD = "good"            # 良好 (80-89)
    FAIR = "fair"            # 一般 (70-79)
    POOR = "poor"            # 较差 (60-69)
    FAILED = "failed"        # 不合格 (<60)


@dataclass
class ScoreMetric:
    """
    评分指标
    
    Attributes:
        name: 指标名称
        score: 得分 (0-100)
        weight: 权重 (0-1)
        description: 描述
        details: 详细信息
    """
    name: str
    score: float
    weight: float
    description: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def weighted_score(self) -> float:
        """加权得分"""
        return self.score * self.weight
    
    @property
    def level(self) -> ScoreLevel:
        """评分等级"""
        if self.score >= 90:
            return ScoreLevel.EXCELLENT
        elif self.score >= 80:
            return ScoreLevel.GOOD
        elif self.score >= 70:
            return ScoreLevel.FAIR
        elif self.score >= 60:
            return ScoreLevel.POOR
        else:
            return ScoreLevel.FAILED


@dataclass
class ScoreReport:
    """
    评分报告
    
    Attributes:
        total_score: 总分 (0-100)
        metrics: 各项指标
        level: 整体评级
        issues: 发现的问题列表
        suggestions: 改进建议
    """
    total_score: float
    metrics: List[ScoreMetric]
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    
    @property
    def level(self) -> ScoreLevel:
        """整体评级"""
        if self.total_score >= 90:
            return ScoreLevel.EXCELLENT
        elif self.total_score >= 80:
            return ScoreLevel.GOOD
        elif self.total_score >= 70:
            return ScoreLevel.FAIR
        elif self.total_score >= 60:
            return ScoreLevel.POOR
        else:
            return ScoreLevel.FAILED
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "total_score": round(self.total_score, 2),
            "level": self.level.value,
            "metrics": [
                {
                    "name": m.name,
                    "score": round(m.score, 2),
                    "weight": m.weight,
                    "weighted_score": round(m.weighted_score, 2),
                    "level": m.level.value,
                    "description": m.description,
                    "details": m.details
                }
                for m in self.metrics
            ],
            "issues": self.issues,
            "suggestions": self.suggestions
        }


class ScheduleScorer:
    """
    排课评分器
    
    评估排课结果的质量，计算各项指标分数。
    
    评分维度：
    1. 任务完成率 (25%)
    2. 主科上午率 (20%)
    3. 课时分布均衡度 (15%)
    4. 教师课程集中度 (15%)
    5. 连堂完整率 (15%)
    6. 无冲突率 (10%)
    
    Usage:
        scorer = ScheduleScorer(state, data)
        report = scorer.score()
        print(f"总分: {report.total_score}")
    """
    
    # 指标权重配置
    WEIGHTS = {
        "completion_rate": 0.25,
        "main_subject_morning": 0.20,
        "distribution_balance": 0.15,
        "teacher_concentration": 0.15,
        "continuous_integrity": 0.15,
        "conflict_free": 0.10,
    }
    
    def __init__(self, state: 'ScheduleState', data: 'ScheduleData'):
        """
        初始化评分器
        
        Args:
            state: 课表状态
            data: 排课数据
        """
        self.state = state
        self.data = data
    
    def score(self) -> ScoreReport:
        """
        计算排课评分
        
        Returns:
            ScoreReport: 评分报告
        """
        metrics = []
        issues = []
        suggestions = []
        
        # 1. 任务完成率
        completion_metric = self._score_completion_rate()
        metrics.append(completion_metric)
        if completion_metric.score < 95:
            issues.append(f"任务完成率偏低: {completion_metric.score:.1f}%")
            suggestions.append("检查是否有资源冲突或约束过于严格")
        
        # 2. 主科上午率
        morning_metric = self._score_main_subject_morning()
        metrics.append(morning_metric)
        if morning_metric.score < 70:
            issues.append(f"主科上午安排率不足: {morning_metric.score:.1f}%")
            suggestions.append("调整排课顺序，优先为主科安排上午时段")
        
        # 3. 课时分布均衡度
        balance_metric = self._score_distribution_balance()
        metrics.append(balance_metric)
        if balance_metric.score < 70:
            issues.append("班级每日课时分布不均衡")
            suggestions.append("尝试分散课程，避免某天课时过多")
        
        # 4. 教师课程集中度
        concentration_metric = self._score_teacher_concentration()
        metrics.append(concentration_metric)
        if concentration_metric.score < 70:
            issues.append("教师课程安排较分散，空档较多")
            suggestions.append("优化教师课程安排，减少空档时间")
        
        # 5. 连堂完整率
        continuous_metric = self._score_continuous_integrity()
        metrics.append(continuous_metric)
        if continuous_metric.score < 90:
            issues.append("部分需要连堂的课程未能连堂")
            suggestions.append("检查连堂课约束，预留足够的连续时段")
        
        # 6. 无冲突率
        conflict_metric = self._score_conflict_free()
        metrics.append(conflict_metric)
        if conflict_metric.score < 100:
            issues.append(f"存在 {100 - conflict_metric.score:.0f} 处冲突")
            suggestions.append("检查并修复时间冲突")
        
        # 计算总分
        total_score = sum(m.weighted_score for m in metrics)
        
        return ScoreReport(
            total_score=total_score,
            metrics=metrics,
            issues=issues,
            suggestions=suggestions
        )
    
    def _score_completion_rate(self) -> ScoreMetric:
        """评分：任务完成率"""
        total_hours = sum(t.weekly_hours for t in self.data.tasks)
        scheduled_hours = len(self.state.schedule_records)
        
        rate = (scheduled_hours / total_hours * 100) if total_hours > 0 else 0
        
        return ScoreMetric(
            name="任务完成率",
            score=min(100, rate),
            weight=self.WEIGHTS["completion_rate"],
            description=f"已排 {scheduled_hours} 课时，共需 {total_hours} 课时",
            details={
                "total_hours": total_hours,
                "scheduled_hours": scheduled_hours,
                "rate": rate
            }
        )
    
    def _score_main_subject_morning(self) -> ScoreMetric:
        """评分：主科上午率"""
        main_subject_ids = {s.id for s in self.data.subjects if s.is_main}
        
        morning_periods = {1, 2, 3, 4}
        main_total = 0
        main_morning = 0
        
        for record in self.state.schedule_records:
            if record.subject_id in main_subject_ids:
                main_total += 1
                if record.period in morning_periods:
                    main_morning += 1
        
        rate = (main_morning / main_total * 100) if main_total > 0 else 100
        
        return ScoreMetric(
            name="主科上午率",
            score=rate,
            weight=self.WEIGHTS["main_subject_morning"],
            description=f"主科 {main_morning}/{main_total} 节安排在上午",
            details={
                "main_total": main_total,
                "main_morning": main_morning,
                "rate": rate
            }
        )
    
    def _score_distribution_balance(self) -> ScoreMetric:
        """评分：课时分布均衡度"""
        # 统计每个班级每天的课时
        class_daily_hours = defaultdict(lambda: defaultdict(int))
        
        for record in self.state.schedule_records:
            class_daily_hours[record.class_id][record.day] += 1
        
        # 计算标准差
        std_devs = []
        for class_id, daily_hours in class_daily_hours.items():
            hours = list(daily_hours.values())
            if len(hours) >= 2:
                mean = sum(hours) / len(hours)
                variance = sum((h - mean) ** 2 for h in hours) / len(hours)
                std_dev = variance ** 0.5
                std_devs.append(std_dev)
        
        avg_std_dev = sum(std_devs) / len(std_devs) if std_devs else 0
        
        # 标准差转换为分数（标准差越小分数越高）
        if avg_std_dev <= 0.5:
            score = 100
        elif avg_std_dev <= 1.0:
            score = 90
        elif avg_std_dev <= 1.5:
            score = 80
        elif avg_std_dev <= 2.0:
            score = 70
        elif avg_std_dev <= 2.5:
            score = 60
        else:
            score = max(0, 50 - (avg_std_dev - 2.5) * 10)
        
        return ScoreMetric(
            name="课时分布均衡",
            score=score,
            weight=self.WEIGHTS["distribution_balance"],
            description=f"平均标准差: {avg_std_dev:.2f}",
            details={
                "avg_std_dev": avg_std_dev,
                "classes_analyzed": len(class_daily_hours)
            }
        )
    
    def _score_teacher_concentration(self) -> ScoreMetric:
        """评分：教师课程集中度"""
        # 统计每个教师每天的空档数
        teacher_daily_gaps = defaultdict(lambda: defaultdict(int))
        teacher_daily_periods = defaultdict(lambda: defaultdict(list))
        
        for record in self.state.schedule_records:
            teacher_daily_periods[record.teacher_id][record.day].append(record.period)
        
        total_gaps = 0
        total_teachers = 0
        
        for teacher_id, daily_periods in teacher_daily_periods.items():
            for day, periods in daily_periods.items():
                if len(periods) >= 2:
                    sorted_periods = sorted(periods)
                    for i in range(len(sorted_periods) - 1):
                        gap = sorted_periods[i + 1] - sorted_periods[i] - 1
                        # 午休不算空档
                        if not (sorted_periods[i] <= 4 and sorted_periods[i + 1] >= 5):
                            total_gaps += gap
            total_teachers += 1
        
        avg_gaps = total_gaps / total_teachers if total_teachers > 0 else 0
        
        # 空档转换为分数
        if avg_gaps <= 0.5:
            score = 100
        elif avg_gaps <= 1.0:
            score = 90
        elif avg_gaps <= 2.0:
            score = 80
        elif avg_gaps <= 3.0:
            score = 70
        else:
            score = max(0, 60 - (avg_gaps - 3) * 10)
        
        return ScoreMetric(
            name="教师课程集中",
            score=score,
            weight=self.WEIGHTS["teacher_concentration"],
            description=f"平均每教师空档: {avg_gaps:.2f}",
            details={
                "total_gaps": total_gaps,
                "teachers_analyzed": total_teachers,
                "avg_gaps": avg_gaps
            }
        )
    
    def _score_continuous_integrity(self) -> ScoreMetric:
        """评分：连堂完整率"""
        # 找出需要连堂的任务
        continuous_tasks = [t for t in self.data.tasks if t.is_continuous]
        
        if not continuous_tasks:
            return ScoreMetric(
                name="连堂完整率",
                score=100,
                weight=self.WEIGHTS["continuous_integrity"],
                description="无需要连堂的课程"
            )
        
        # 检查每个连堂任务是否实际连堂
        task_records = defaultdict(list)
        for record in self.state.schedule_records:
            task_records[record.task_id].append(record)
        
        complete_count = 0
        total_count = len(continuous_tasks)
        
        for task in continuous_tasks:
            records = task_records.get(task.id, [])
            if not records:
                continue
            
            # 按天分组
            by_day = defaultdict(list)
            for r in records:
                by_day[r.day].append(r.period)
            
            # 检查是否有连续的节次
            has_continuous = False
            for day, periods in by_day.items():
                sorted_periods = sorted(periods)
                consecutive_count = 1
                for i in range(len(sorted_periods) - 1):
                    if sorted_periods[i + 1] - sorted_periods[i] == 1:
                        consecutive_count += 1
                        if consecutive_count >= task.continuous_count:
                            has_continuous = True
                            break
                    else:
                        consecutive_count = 1
                if has_continuous:
                    break
            
            if has_continuous:
                complete_count += 1
        
        rate = (complete_count / total_count * 100) if total_count > 0 else 100
        
        return ScoreMetric(
            name="连堂完整率",
            score=rate,
            weight=self.WEIGHTS["continuous_integrity"],
            description=f"{complete_count}/{total_count} 个连堂任务完整",
            details={
                "continuous_tasks": total_count,
                "complete_count": complete_count,
                "rate": rate
            }
        )
    
    def _score_conflict_free(self) -> ScoreMetric:
        """评分：无冲突率"""
        # 检查教师冲突
        teacher_slots = defaultdict(set)
        teacher_conflicts = 0
        
        for record in self.state.schedule_records:
            slot = (record.day, record.period)
            if slot in teacher_slots[record.teacher_id]:
                teacher_conflicts += 1
            teacher_slots[record.teacher_id].add(slot)
        
        # 检查班级冲突
        class_slots = defaultdict(set)
        class_conflicts = 0
        
        for record in self.state.schedule_records:
            slot = (record.day, record.period)
            if slot in class_slots[record.class_id]:
                class_conflicts += 1
            class_slots[record.class_id].add(slot)
        
        total_conflicts = teacher_conflicts + class_conflicts
        total_records = len(self.state.schedule_records)
        
        conflict_rate = (total_conflicts / total_records * 100) if total_records > 0 else 0
        score = max(0, 100 - conflict_rate * 10)
        
        return ScoreMetric(
            name="无冲突率",
            score=score,
            weight=self.WEIGHTS["conflict_free"],
            description=f"发现 {total_conflicts} 处冲突",
            details={
                "teacher_conflicts": teacher_conflicts,
                "class_conflicts": class_conflicts,
                "total_conflicts": total_conflicts
            }
        )
