"""
模拟退火优化算法

用于优化初始排课方案，通过邻域操作和概率接受机制寻找更优解。
"""

import math
import random
import copy
import time
from typing import List, Dict, Tuple, Optional, TYPE_CHECKING
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from ..state import ScheduleState
    from ..data.models import ScheduleData, ScheduleRecord
    from ..constraints import ConstraintChecker

from .evaluator import ScheduleEvaluator


@dataclass
class SAConfig:
    """模拟退火算法配置"""
    initial_temp: float = 1000.0      # 初始温度
    cooling_rate: float = 0.9995      # 降温速率
    min_temp: float = 0.01            # 最小温度
    max_iterations: int = 50000       # 最大迭代次数
    max_time_seconds: int = 300       # 最大运行时间（秒）
    reheat_threshold: int = 5000      # 无改进触发升温的迭代数
    reheat_factor: float = 1.5        # 升温倍数
    
    @classmethod
    def from_optimization_level(cls, level: int) -> 'SAConfig':
        """
        根据优化程度生成配置
        
        Args:
            level: 优化程度 (1-5)
        
        Returns:
            SAConfig: 对应的配置
        """
        # 基础配置
        base_iterations = 10000
        base_time = 60  # 秒
        
        return cls(
            initial_temp=1000.0,
            cooling_rate=0.9995 + (5 - level) * 0.00005,  # 级别越高，降温越慢
            min_temp=0.01,
            max_iterations=base_iterations * level,       # 1-5 -> 10k-50k
            max_time_seconds=base_time * level,           # 1-5 -> 60s-300s
            reheat_threshold=1000 * level,
            reheat_factor=1.5
        )


class SimulatedAnnealing:
    """
    模拟退火优化器
    
    通过以下邻域操作优化排课方案：
    1. swap: 交换两节课的时间
    2. move: 移动一节课到空闲时间
    3. chain_swap: 链式交换（A→B→C→A）
    """
    
    def __init__(
        self,
        state: 'ScheduleState',
        data: 'ScheduleData',
        constraint_checker: 'ConstraintChecker' = None,
        config: SAConfig = None
    ):
        self.state = state
        self.data = data
        self.constraint_checker = constraint_checker
        self.config = config or SAConfig()
        
        self.evaluator = ScheduleEvaluator(data, constraint_checker)
        
        # 统计信息
        self.stats = {
            'iterations': 0,
            'accepted': 0,
            'improved': 0,
            'swap_ops': 0,
            'move_ops': 0,
            'chain_ops': 0,
            'reheat_count': 0
        }
    
    def optimize(
        self,
        records: List['ScheduleRecord'],
        random_seed: int = None
    ) -> Tuple[List['ScheduleRecord'], float]:
        """
        优化排课方案
        
        Args:
            records: 初始排课记录
            random_seed: 随机种子（用于生成不同方案）
        
        Returns:
            Tuple[List[ScheduleRecord], float]: 优化后的记录和得分
        """
        if random_seed is not None:
            random.seed(random_seed)
        
        # 复制记录，避免修改原数据
        current_records = copy.deepcopy(records)
        current_score = self.evaluator.quick_evaluate(current_records)
        
        best_records = copy.deepcopy(current_records)
        best_score = current_score
        
        temperature = self.config.initial_temp
        no_improve_count = 0
        start_time = time.time()
        
        print(f"    模拟退火开始: 初始温度={temperature:.2f}, 初始得分={current_score:.2f}")
        
        for iteration in range(self.config.max_iterations):
            self.stats['iterations'] = iteration + 1
            
            # 检查时间限制
            elapsed = time.time() - start_time
            if elapsed > self.config.max_time_seconds:
                print(f"    达到时间限制 ({elapsed:.1f}s)，停止优化")
                break
            
            # 检查温度
            if temperature < self.config.min_temp:
                print(f"    温度过低 ({temperature:.6f})，停止优化")
                break
            
            # 生成邻域解
            neighbor_records, op_type = self._generate_neighbor(current_records)
            
            if neighbor_records is None:
                # 无法生成有效邻域解，跳过
                continue
            
            # 评估新解
            neighbor_score = self.evaluator.quick_evaluate(neighbor_records)
            
            # 计算接受概率
            delta = neighbor_score - current_score
            
            if delta > 0:
                # 新解更好，直接接受
                accept = True
                self.stats['improved'] += 1
            else:
                # 新解更差，按概率接受
                accept_prob = math.exp(delta / temperature)
                accept = random.random() < accept_prob
            
            if accept:
                current_records = neighbor_records
                current_score = neighbor_score
                self.stats['accepted'] += 1
                no_improve_count = 0
                
                # 更新最优解
                if current_score > best_score:
                    best_records = copy.deepcopy(current_records)
                    best_score = current_score
            else:
                no_improve_count += 1
            
            # 降温
            temperature *= self.config.cooling_rate
            
            # 检查是否需要升温（避免陷入局部最优）
            if no_improve_count >= self.config.reheat_threshold:
                temperature *= self.config.reheat_factor
                no_improve_count = 0
                self.stats['reheat_count'] += 1
                print(f"    升温: 新温度={temperature:.2f}, 当前得分={current_score:.2f}")
            
            # 定期输出进度
            if (iteration + 1) % 5000 == 0:
                print(f"    迭代 {iteration + 1}: 温度={temperature:.4f}, "
                      f"当前={current_score:.2f}, 最优={best_score:.2f}")
        
        print(f"    模拟退火结束: 迭代={self.stats['iterations']}, "
              f"最终得分={best_score:.2f}")
        print(f"    操作统计: swap={self.stats['swap_ops']}, "
              f"move={self.stats['move_ops']}, chain={self.stats['chain_ops']}")
        
        return best_records, best_score
    
    def _generate_neighbor(
        self,
        records: List['ScheduleRecord']
    ) -> Tuple[Optional[List['ScheduleRecord']], str]:
        """
        生成邻域解
        
        随机选择一种邻域操作：
        - swap (50%): 交换两节课的时间
        - move (40%): 移动一节课到空闲时间
        - chain_swap (10%): 链式交换
        """
        if not records:
            return None, ''
        
        op_choice = random.random()
        
        if op_choice < 0.5:
            return self._swap_operation(records)
        elif op_choice < 0.9:
            return self._move_operation(records)
        else:
            return self._chain_swap_operation(records)
    
    def _swap_operation(
        self,
        records: List['ScheduleRecord']
    ) -> Tuple[Optional[List['ScheduleRecord']], str]:
        """
        交换操作：交换同一班级两节不同课的时间
        """
        if len(records) < 2:
            return None, 'swap'
        
        # 按班级分组
        class_records: Dict[int, List[int]] = {}
        for i, r in enumerate(records):
            if r.class_id not in class_records:
                class_records[r.class_id] = []
            class_records[r.class_id].append(i)
        
        # 选择一个有多节课的班级
        valid_classes = [cid for cid, indices in class_records.items() if len(indices) >= 2]
        if not valid_classes:
            return None, 'swap'
        
        class_id = random.choice(valid_classes)
        indices = class_records[class_id]
        
        # 随机选择两节课
        idx1, idx2 = random.sample(indices, 2)
        
        # 复制并交换
        new_records = copy.deepcopy(records)
        r1, r2 = new_records[idx1], new_records[idx2]
        
        # 交换时间
        r1.day, r2.day = r2.day, r1.day
        r1.period, r2.period = r2.period, r1.period
        
        # 检查交换后是否有效（简单检查教师冲突）
        if self._has_teacher_conflict(new_records, idx1) or self._has_teacher_conflict(new_records, idx2):
            return None, 'swap'
        
        self.stats['swap_ops'] += 1
        return new_records, 'swap'
    
    def _move_operation(
        self,
        records: List['ScheduleRecord']
    ) -> Tuple[Optional[List['ScheduleRecord']], str]:
        """
        移动操作：将一节课移动到班级的空闲时间
        """
        if not records:
            return None, 'move'
        
        # 随机选择一条记录
        idx = random.randint(0, len(records) - 1)
        record = records[idx]
        
        # 获取该班级的已占用时间
        class_occupied = set()
        for r in records:
            if r.class_id == record.class_id:
                for p in r.periods:
                    class_occupied.add((r.day, p))
        
        # 获取该教师的已占用时间
        teacher_occupied = set()
        for r in records:
            if r.teacher_id == record.teacher_id:
                for p in r.periods:
                    teacher_occupied.add((r.day, p))
        
        # 查找可用的空闲时间
        available_slots = []
        
        # 获取班级年级
        cls = self.data.get_class(record.class_id)
        grade = cls.grade if cls else None
        
        for day in range(1, 6):
            # 根据年级确定最大节次
            if day == 5:
                max_period = 8
            elif day == 4 and grade in ['G8', 'G9']:
                max_period = 11
            else:
                max_period = 9
            
            for period in range(1, max_period + 1):
                # 检查是否为选修课时段
                if period >= 10 and not (day == 4 and grade in ['G8', 'G9']):
                    continue
                
                slot = (day, period)
                
                # 检查班级和教师都空闲
                if slot not in class_occupied and slot not in teacher_occupied:
                    available_slots.append(slot)
        
        if not available_slots:
            return None, 'move'
        
        # 随机选择一个空闲时间
        new_day, new_period = random.choice(available_slots)
        
        # 复制并修改
        new_records = copy.deepcopy(records)
        new_records[idx].day = new_day
        new_records[idx].period = new_period
        
        self.stats['move_ops'] += 1
        return new_records, 'move'
    
    def _chain_swap_operation(
        self,
        records: List['ScheduleRecord']
    ) -> Tuple[Optional[List['ScheduleRecord']], str]:
        """
        链式交换操作：A→B→C→A 形式的三节课时间轮换
        
        这种操作可以更大范围地调整课表结构
        """
        if len(records) < 3:
            return None, 'chain'
        
        # 按班级分组
        class_records: Dict[int, List[int]] = {}
        for i, r in enumerate(records):
            if r.class_id not in class_records:
                class_records[r.class_id] = []
            class_records[r.class_id].append(i)
        
        # 选择一个有至少3节课的班级
        valid_classes = [cid for cid, indices in class_records.items() if len(indices) >= 3]
        if not valid_classes:
            return None, 'chain'
        
        class_id = random.choice(valid_classes)
        indices = class_records[class_id]
        
        # 随机选择三节课
        idx1, idx2, idx3 = random.sample(indices, 3)
        
        # 复制并执行链式交换
        new_records = copy.deepcopy(records)
        r1, r2, r3 = new_records[idx1], new_records[idx2], new_records[idx3]
        
        # A→B→C→A: A的时间给C，B的时间给A，C的时间给B
        t1_day, t1_period = r1.day, r1.period
        t2_day, t2_period = r2.day, r2.period
        t3_day, t3_period = r3.day, r3.period
        
        r1.day, r1.period = t2_day, t2_period
        r2.day, r2.period = t3_day, t3_period
        r3.day, r3.period = t1_day, t1_period
        
        # 检查是否有教师冲突
        if (self._has_teacher_conflict(new_records, idx1) or
            self._has_teacher_conflict(new_records, idx2) or
            self._has_teacher_conflict(new_records, idx3)):
            return None, 'chain'
        
        self.stats['chain_ops'] += 1
        return new_records, 'chain'
    
    def _has_teacher_conflict(self, records: List['ScheduleRecord'], check_idx: int) -> bool:
        """检查指定记录是否与其他记录有教师冲突"""
        check_record = records[check_idx]
        check_periods = set(check_record.periods)
        
        for i, r in enumerate(records):
            if i == check_idx:
                continue
            
            if r.teacher_id != check_record.teacher_id:
                continue
            
            if r.day != check_record.day:
                continue
            
            # 检查时间是否重叠
            r_periods = set(r.periods)
            if check_periods & r_periods:
                return True
        
        return False
    
    def get_stats(self) -> Dict:
        """获取优化统计信息"""
        return self.stats.copy()
