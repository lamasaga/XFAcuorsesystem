"""
排课方案评估器

用于评估排课方案的质量，为模拟退火算法提供评分。
"""

from typing import Dict, List, TYPE_CHECKING
from dataclasses import dataclass
from collections import defaultdict

if TYPE_CHECKING:
    from ..state import ScheduleState
    from ..data.models import ScheduleData, ScheduleRecord
    from ..constraints import ConstraintChecker


@dataclass
class EvaluationResult:
    """评估结果"""
    total_score: float = 0.0
    
    # 各项指标得分（0-100）
    completion_rate: float = 0.0      # 排课完成率
    main_morning_rate: float = 0.0    # 主科上午率
    distribution_score: float = 0.0    # 分布均衡度
    teacher_concentration: float = 0.0 # 教师课程集中度
    continuous_integrity: float = 0.0  # 连堂完整率
    
    # 惩罚项
    teacher_gap_penalty: float = 0.0   # 教师空窗期惩罚
    hard_violation_count: int = 0      # 硬约束违反数
    soft_violation_score: float = 0.0  # 软约束违反得分
    
    def to_dict(self) -> Dict:
        return {
            'total_score': self.total_score,
            'completion_rate': self.completion_rate,
            'main_morning_rate': self.main_morning_rate,
            'distribution_score': self.distribution_score,
            'teacher_concentration': self.teacher_concentration,
            'continuous_integrity': self.continuous_integrity,
            'teacher_gap_penalty': self.teacher_gap_penalty,
            'hard_violation_count': self.hard_violation_count,
            'soft_violation_score': self.soft_violation_score
        }


class ScheduleEvaluator:
    """
    排课方案评估器
    
    评估维度和权重：
    - 排课完成率 (40%): 所有任务是否都被安排
    - 主科上午率 (15%): 主科是否优先安排在上午
    - 分布均衡度 (15%): 科目在一周内分布是否均匀
    - 教师集中度 (10%): 教师课程是否集中（减少空窗期）
    - 连堂完整率 (10%): 连堂课是否完整安排
    - 软约束得分 (10%): 来自约束检查器的软约束评分
    """
    
    # 评估权重
    WEIGHTS = {
        'completion': 40,
        'main_morning': 15,
        'distribution': 15,
        'teacher_concentration': 10,
        'continuous': 10,
        'soft_constraints': 10
    }
    
    # 主科列表
    MAIN_SUBJECTS = ['语文', '数学', '英语', 'Chinese', 'Math', 'English']
    
    def __init__(
        self,
        data: 'ScheduleData',
        constraint_checker: 'ConstraintChecker' = None
    ):
        self.data = data
        self.constraint_checker = constraint_checker
    
    def evaluate(
        self,
        records: List['ScheduleRecord'],
        total_tasks: int = None
    ) -> EvaluationResult:
        """
        评估排课方案
        
        Args:
            records: 排课记录列表
            total_tasks: 总任务数（用于计算完成率）
        
        Returns:
            EvaluationResult: 评估结果
        """
        result = EvaluationResult()
        
        if not records:
            return result
        
        if total_tasks is None:
            total_tasks = len(self.data.tasks)
        
        # 1. 计算排课完成率
        result.completion_rate = self._calc_completion_rate(records, total_tasks)
        
        # 2. 计算主科上午率
        result.main_morning_rate = self._calc_main_morning_rate(records)
        
        # 3. 计算分布均衡度
        result.distribution_score = self._calc_distribution_score(records)
        
        # 4. 计算教师课程集中度
        result.teacher_concentration = self._calc_teacher_concentration(records)
        
        # 5. 计算连堂完整率
        result.continuous_integrity = self._calc_continuous_integrity(records)
        
        # 6. 计算教师空窗期惩罚
        result.teacher_gap_penalty = self._calc_teacher_gap_penalty(records)
        
        # 7. 检查硬约束违反
        if self.constraint_checker:
            result.hard_violation_count = self._count_hard_violations(records)
            result.soft_violation_score = self._calc_soft_constraint_score(records)
        
        # 计算总分
        result.total_score = self._calc_total_score(result)
        
        return result
    
    def _calc_completion_rate(self, records: List['ScheduleRecord'], total_tasks: int) -> float:
        """计算排课完成率"""
        if total_tasks == 0:
            return 100.0
        
        # 统计已排课的任务数
        scheduled_task_ids = set(r.task_id for r in records)
        scheduled_count = len(scheduled_task_ids)
        
        return (scheduled_count / total_tasks) * 100
    
    def _calc_main_morning_rate(self, records: List['ScheduleRecord']) -> float:
        """计算主科上午率"""
        main_subject_total = 0
        main_subject_morning = 0
        
        for record in records:
            subject = self.data.get_subject(record.subject_id)
            if not subject:
                continue
            
            # 检查是否为主科
            is_main = subject.name in self.MAIN_SUBJECTS or subject.category == '主科'
            if is_main:
                main_subject_total += 1
                # 上午节次：1-5
                if record.period <= 5:
                    main_subject_morning += 1
        
        if main_subject_total == 0:
            return 100.0
        
        return (main_subject_morning / main_subject_total) * 100
    
    def _calc_distribution_score(self, records: List['ScheduleRecord']) -> float:
        """
        计算科目分布均衡度
        
        理想情况：每个班每个科目的课程均匀分布在一周内
        """
        # 按班级-科目分组统计每天的课时
        class_subject_day: Dict[tuple, Dict[int, int]] = defaultdict(lambda: defaultdict(int))
        
        for record in records:
            key = (record.class_id, record.subject_id)
            class_subject_day[key][record.day] += 1
        
        if not class_subject_day:
            return 100.0
        
        # 计算每个班级-科目的分布方差
        variance_sum = 0
        count = 0
        
        for key, day_counts in class_subject_day.items():
            if len(day_counts) <= 1:
                continue
            
            counts = list(day_counts.values())
            avg = sum(counts) / len(counts)
            variance = sum((c - avg) ** 2 for c in counts) / len(counts)
            variance_sum += variance
            count += 1
        
        if count == 0:
            return 100.0
        
        # 方差越小越好，转换为0-100分
        avg_variance = variance_sum / count
        # 方差为0得100分，方差为2得60分，方差大于4得0分
        score = max(0, 100 - avg_variance * 25)
        
        return score
    
    def _calc_teacher_concentration(self, records: List['ScheduleRecord']) -> float:
        """
        计算教师课程集中度
        
        理想情况：教师一天的课程尽量连续，减少空窗期
        """
        # 按教师-天分组
        teacher_day_periods: Dict[tuple, List[int]] = defaultdict(list)
        
        for record in records:
            key = (record.teacher_id, record.day)
            teacher_day_periods[key].extend(record.periods)
        
        if not teacher_day_periods:
            return 100.0
        
        # 计算每个教师每天的课程集中度
        concentration_scores = []
        
        for (teacher_id, day), periods in teacher_day_periods.items():
            if len(periods) <= 1:
                concentration_scores.append(100)
                continue
            
            periods = sorted(periods)
            span = periods[-1] - periods[0] + 1
            actual = len(periods)
            
            # 集中度 = 实际课时 / 跨度
            concentration = (actual / span) * 100
            concentration_scores.append(concentration)
        
        return sum(concentration_scores) / len(concentration_scores)
    
    def _calc_continuous_integrity(self, records: List['ScheduleRecord']) -> float:
        """
        计算连堂完整率
        
        检查需要连堂的任务是否都安排为连堂
        """
        # 统计需要连堂的任务
        continuous_tasks = [t for t in self.data.tasks if t.is_continuous and t.continuous_count > 1]
        
        if not continuous_tasks:
            return 100.0
        
        # 检查每个连堂任务的完成情况
        task_records: Dict[int, List['ScheduleRecord']] = defaultdict(list)
        for record in records:
            task_records[record.task_id].append(record)
        
        complete_count = 0
        for task in continuous_tasks:
            task_recs = task_records.get(task.id, [])
            
            # 检查是否有连续的记录
            for rec in task_recs:
                if rec.duration >= task.continuous_count:
                    complete_count += 1
                    break
        
        return (complete_count / len(continuous_tasks)) * 100
    
    def _calc_teacher_gap_penalty(self, records: List['ScheduleRecord']) -> float:
        """
        计算教师空窗期惩罚
        
        空窗期：教师一天中两节课之间的空闲时间
        """
        # 按教师-天分组
        teacher_day_periods: Dict[tuple, List[int]] = defaultdict(list)
        
        for record in records:
            key = (record.teacher_id, record.day)
            teacher_day_periods[key].extend(record.periods)
        
        total_gaps = 0
        
        for periods in teacher_day_periods.values():
            if len(periods) <= 1:
                continue
            
            periods = sorted(periods)
            
            # 计算空窗期（不包括午休）
            for i in range(len(periods) - 1):
                gap = periods[i + 1] - periods[i] - 1
                
                # 午休时间（第5-6节之间）不算空窗
                if periods[i] == 5 and periods[i + 1] == 6:
                    continue
                
                if gap > 0:
                    total_gaps += gap
        
        # 每个空窗期扣2分，最多扣20分
        penalty = min(total_gaps * 2, 20)
        
        return penalty
    
    def _count_hard_violations(self, records: List['ScheduleRecord']) -> int:
        """统计硬约束违反数"""
        if not self.constraint_checker:
            return 0
        
        violations = 0
        for i, record in enumerate(records):
            existing = records[:i]  # 检查时只考虑之前的记录
            result = self.constraint_checker.check_hard(record, existing, self.data)
            if not result.passed:
                violations += len(result.violations)
        
        return violations
    
    def _calc_soft_constraint_score(self, records: List['ScheduleRecord']) -> float:
        """计算软约束得分"""
        if not self.constraint_checker:
            return 100.0
        
        total_score = 0
        for i, record in enumerate(records):
            existing = records[:i]
            result = self.constraint_checker.check_soft(record, existing, self.data)
            total_score += result.score
        
        # 转换为0-100分（假设每条记录满分100）
        if len(records) == 0:
            return 100.0
        
        return min(100, (total_score / len(records)))
    
    def _calc_total_score(self, result: EvaluationResult) -> float:
        """计算总分"""
        # 如果有硬约束违反，直接返回0分
        if result.hard_violation_count > 0:
            return 0.0
        
        score = 0.0
        
        # 加权计算
        score += result.completion_rate * (self.WEIGHTS['completion'] / 100)
        score += result.main_morning_rate * (self.WEIGHTS['main_morning'] / 100)
        score += result.distribution_score * (self.WEIGHTS['distribution'] / 100)
        score += result.teacher_concentration * (self.WEIGHTS['teacher_concentration'] / 100)
        score += result.continuous_integrity * (self.WEIGHTS['continuous'] / 100)
        
        # 软约束得分
        soft_score = 100 - result.soft_violation_score  # 转换为正向得分
        score += max(0, soft_score) * (self.WEIGHTS['soft_constraints'] / 100)
        
        # 扣除空窗期惩罚
        score -= result.teacher_gap_penalty
        
        return max(0, min(100, score))
    
    def quick_evaluate(self, records: List['ScheduleRecord']) -> float:
        """
        快速评估（仅计算关键指标）
        
        用于模拟退火的快速评分，减少计算开销
        """
        if not records:
            return 0.0
        
        # 只计算最关键的几个指标
        completion = len(set(r.task_id for r in records)) / max(len(self.data.tasks), 1) * 100
        
        # 快速计算主科上午率
        main_morning = 0
        main_total = 0
        for record in records:
            subject = self.data.get_subject(record.subject_id)
            if subject and (subject.name in self.MAIN_SUBJECTS or subject.category == '主科'):
                main_total += 1
                if record.period <= 5:
                    main_morning += 1
        
        main_rate = (main_morning / main_total * 100) if main_total > 0 else 100
        
        # 简化的分数计算
        score = completion * 0.5 + main_rate * 0.3 + 20  # 基础分20分
        
        return min(100, max(0, score))
