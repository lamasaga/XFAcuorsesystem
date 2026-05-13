# OR-Tools CP-SAT 技术指南

> 最后更新: 2026-02-09  
> 本文档整理了本项目中使用 Google OR-Tools CP-SAT 求解器的技术细节、设计模式和实用技巧。  
> 适合需要理解、维护或扩展排课引擎的开发者阅读。

---

## 目录

1. [CP-SAT 基础概念](#一cp-sat-基础概念)
2. [本项目的建模思路](#二本项目的建模思路)
3. [变量创建与域过滤](#三变量创建与域过滤)
4. [硬约束编写模式](#四硬约束编写模式)
5. [软约束编写模式](#五软约束编写模式)
6. [Hard/Soft 统一调度模式](#六hardsoft-统一调度模式)
7. [连堂课建模](#七连堂课建模)
8. [教研组组会建模](#八教研组组会建模)
9. [诊断与无解分析](#九诊断与无解分析)
10. [多方案多样性](#十多方案多样性)
11. [求解器调优](#十一求解器调优)
12. [常用 API 速查](#十二常用-api-速查)
13. [常见陷阱与最佳实践](#十三常见陷阱与最佳实践)

---

## 一、CP-SAT 基础概念

### 1.1 什么是 CP-SAT

CP-SAT (Constraint Programming - SAT) 是 Google OR-Tools 中的约束满足求解器。它将问题建模为：

- **变量**: 需要求解的未知量（如"这节课排在哪个时间段"）
- **约束**: 变量必须满足的条件（如"同一教师不能同时上两节课"）
- **目标函数**: 可选的优化目标（如"主科尽量排在上午"）

### 1.2 核心对象

```python
from ortools.sat.python import cp_model

model = cp_model.CpModel()     # 创建模型
solver = cp_model.CpSolver()   # 创建求解器

# 创建变量
x = model.NewBoolVar('x')       # 布尔变量 (0 或 1)
y = model.NewIntVar(0, 10, 'y') # 整数变量 (0-10)

# 添加约束
model.Add(x + y <= 5)

# 添加目标（最大化/最小化）
model.Maximize(x + 2 * y)

# 求解
status = solver.Solve(model)
if status == cp_model.OPTIMAL:
    print(f"x = {solver.Value(x)}, y = {solver.Value(y)}")
```

### 1.3 求解状态

```python
cp_model.OPTIMAL      # 找到最优解
cp_model.FEASIBLE     # 找到可行解（但可能不是最优）
cp_model.INFEASIBLE   # 无解（约束矛盾）
cp_model.UNKNOWN      # 超时，未确定
cp_model.MODEL_INVALID  # 模型定义有误
```

---

## 二、本项目的建模思路

### 2.1 决策变量设计

排课问题的核心决策是：**每个排课会话 (Session) 分配到哪个时间槽 (day, period)**。

```
x[session_id][(day, period)] = BoolVar
```

对于 session `s`，`x[s.id][(d, p)] = 1` 表示将该 session 排在第 `d` 天第 `p` 节。

```python
# 实际代码 (cp_solver.py)
self.x: Dict[int, Dict[Tuple[int, int], cp_model.IntVar]] = {}

for s in self.sessions:
    valid_slots = self._get_valid_slots(s)  # 过滤不合法的时间槽
    slot_vars = {}
    for day, period in valid_slots:
        slot_vars[(day, period)] = self.model.NewBoolVar(
            f"x_s{s.id}_d{day}_p{period}"
        )
    self.x[s.id] = slot_vars
```

### 2.2 ScheduleSession 抽象

`ScheduleSession` 是排课的最小决策单元：

```python
@dataclass
class ScheduleSession:
    id: int
    task_ids: List[int]      # 关联的教学任务 ID
    teacher_ids: List[int]   # 涉及的教师
    class_ids: List[int]     # 涉及的班级
    subject_id: int          # 科目
    subject_name: str
    duration: int            # 1=单节, 2=连堂
    venue_type: Optional[str]
    layer_group_id: Optional[int]
    grades: List[str]
    is_main_subject: bool
    is_continuous_pair: bool  # 是否为连堂 session
```

**设计要点**：
- 一个分层组的多个 Task 共享一个 Session（同时上课）
- 连堂课拆分为 1 个 `duration=2` 的 Session + 多个 `duration=1` 的 Session

### 2.3 索引结构

为了高效添加约束，预先构建反向索引：

```python
self._teacher_sessions: Dict[int, List[int]]  # 教师 -> session IDs
self._class_sessions: Dict[int, List[int]]    # 班级 -> session IDs
self._venue_sessions: Dict[str, List[int]]    # 场地类型 -> session IDs
self._class_subject_sessions: Dict[Tuple[int, int], List[int]]  # (班级, 科目) -> session IDs
```

---

## 三、变量创建与域过滤

### 3.1 合法时间槽计算

创建变量时就过滤掉不可能的时间槽，减少搜索空间：

```python
def _get_valid_slots(self, session) -> List[Tuple[int, int]]:
    slots = []
    for day in range(1, 6):  # 周一到周五
        max_period = self._get_max_period(day, session.grades)
        for period in range(1, max_period + 1):
            end_period = period + session.duration - 1
            
            # 1. 不能超出当天最大节次
            if end_period > max_period:
                continue
            
            # 2. 10-11 节只允许 G8/G9 周四
            if period >= 10 or end_period >= 10:
                if day != 4 or not all(g in ('G8','G9') for g in session.grades):
                    continue
            
            # 3. 连堂不跨午休 (5-6 节边界)
            if session.duration > 1 and period <= 5 < end_period:
                continue
            
            # 4. 教师手动不可用时间
            if any_teacher_unavailable(session, day, period, end_period):
                continue
            
            slots.append((day, period))
    return slots
```

**技巧**: 物理上不可能的时间槽直接在变量域中排除，比添加约束更高效。

### 3.2 每天最大节次

```python
@staticmethod
def _get_max_period(day: int, grades: List[str]) -> int:
    if day == 5:              # 周五
        return 8
    if day == 4 and grades and all(g in ('G8', 'G9') for g in grades):
        return 11             # G8/G9 周四有 10-11 节
    return 9                  # 默认 9 节
```

---

## 四、硬约束编写模式

### 4.1 恰好选一 (ExactlyOne)

**H1: 每个 Session 恰好分配到一个时间槽**

```python
def _h1_exactly_one(self):
    for s in self.sessions:
        slot_vars = list(self.x[s.id].values())
        if not slot_vars:
            continue  # 无合法槽位，跳过
        self.model.AddExactlyOne(slot_vars)
```

`AddExactlyOne(vars)` 等价于 `sum(vars) == 1`，但效率更高（专用传播器）。

### 4.2 至多一个 (AtMostOne / sum ≤ 1)

**H2: 同一教师同一时刻最多上一节课**

```python
def _h2_teacher_no_conflict(self):
    for tid, sids in self._teacher_sessions.items():
        if len(sids) < 2:
            continue
        
        # 按 (day, period) 收集所有可能占据该时刻的变量
        slot_map: Dict[Tuple[int,int], List] = defaultdict(list)
        for sid in sids:
            s = self.sessions[sid]
            for (day, period), var in self.x[sid].items():
                # 连堂课占据 [period, period+duration-1]
                for p in range(period, period + s.duration):
                    slot_map[(day, p)].append(var)
        
        # 每个时刻最多一个变量为 1
        for _, vars_at_slot in slot_map.items():
            if len(vars_at_slot) > 1:
                self.model.Add(sum(vars_at_slot) <= 1)
```

**关键技巧**: 连堂课 (duration=2) 的起始变量 `x[s.id][(d, p)]` 会占据 `p` 和 `p+1` 两个时刻，所以需要在 `slot_map` 中展开。

### 4.3 容量上限约束

**H4: 场地容量限制**

```python
def _h4_venue_capacity(self):
    for vtype, sids in self._venue_sessions.items():
        cap = self._venue_capacities.get(vtype, 1)
        if len(sids) <= cap:
            continue  # 总数不超过容量，无需约束
        
        # 同上展开为 slot_map
        slot_map = defaultdict(list)
        for sid in sids:
            s = self.sessions[sid]
            for (day, period), var in self.x[sid].items():
                for p in range(period, period + s.duration):
                    slot_map[(day, p)].append(var)
        
        for _, vars_at_slot in slot_map.items():
            if len(vars_at_slot) > cap:
                self.model.Add(sum(vars_at_slot) <= cap)
```

---

## 五、软约束编写模式

### 5.1 核心思路：目标函数加权

软约束不是"必须满足"，而是"尽量满足"。实现方式是将期望行为转化为目标函数的奖惩项：

```python
objective_terms = []

# 奖励好的行为（正分）
terms.append(good_var * weight)

# 惩罚坏的行为（负分）
terms.append(-bad_var * weight)

# 最终最大化总和
model.Maximize(sum(objective_terms))
```

### 5.2 示例：主科优先上午 (S1)

```python
def _rule_main_morning(self, ctype, weight, terms):
    for s in self.sessions:
        if not s.is_main_subject:
            continue
        
        morning_vars = []
        for (day, period), var in self.x[s.id].items():
            if period <= 5:  # 上午
                morning_vars.append(var)
        
        if ctype == "hard":
            # 强制：不允许下午
            afternoon_vars = [v for (d,p),v in self.x[s.id].items() if p > 5]
            if afternoon_vars:
                self.model.Add(sum(afternoon_vars) == 0)
        else:
            # 软约束：排在上午加分
            if morning_vars:
                terms.append(sum(morning_vars) * weight)
```

### 5.3 示例：惩罚超限 (excess 变量模式)

当需要对"超过某个阈值"的情况进行惩罚时，引入辅助变量：

```python
def _rule_daily_subject_limit(self, ctype, weight, terms):
    for (cid, subj_id), sids in self._class_subject_sessions.items():
        for day in range(1, 6):
            day_vars = []
            for sid in sids:
                s = self.sessions[sid]
                for (d, p), var in self.x[sid].items():
                    if d == day:
                        day_vars.append((var, s.duration))
            
            if not day_vars:
                continue
            
            total_duration = sum(v * dur for v, dur in day_vars)
            
            if ctype == "hard":
                self.model.Add(total_duration <= 2)
            else:
                # 创建超限变量: excess >= total - 2, excess >= 0
                excess = self.model.NewIntVar(0, 10, f"exc_{cid}_{subj_id}_{day}")
                self.model.Add(excess >= total_duration - 2)
                terms.append(-excess * weight)  # 惩罚超限
```

**模式总结**: `excess = max(0, actual - limit)`，对 excess 施加惩罚。

### 5.4 示例：布尔分散奖励

```python
def _rule_balanced_distribution(self, ctype, weight, terms):
    """鼓励科目分散到不同天"""
    for (cid, subj_id), sids in self._class_subject_sessions.items():
        for day in range(1, 6):
            day_vars = [...]  # 这天的所有变量
            
            if len(day_vars) > 1:
                # 创建布尔变量: 这天是否有课
                has_any = self.model.NewBoolVar(f"bal_{cid}_{subj_id}_{day}")
                
                # has_any=1 => sum >= 1
                self.model.Add(sum(day_vars) >= 1).OnlyEnforceIf(has_any)
                # has_any=0 => sum == 0
                self.model.Add(sum(day_vars) == 0).OnlyEnforceIf(has_any.Not())
                
                # 奖励"有分布"，惩罚"扎堆"
                terms.append(has_any * weight)
                for v in day_vars:
                    terms.append(-v * weight)
```

---

## 六、Hard/Soft 统一调度模式

### 6.1 设计模式

本项目的一大特色是**所有业务约束都支持 Hard/Soft 模式切换**。统一的约束处理函数签名：

```python
def _rule_xxx(self, ctype: str, weight: int, terms: list):
    """
    Args:
        ctype: "hard" 或 "soft"
        weight: 权重（已乘以 10）
        terms: 目标函数项列表（仅 soft 模式使用）
    """
    if ctype == "hard":
        model.Add(...)           # 添加硬约束
    else:
        terms.append(... * weight)  # 添加目标项
```

### 6.2 统一调度器

```python
def _apply_configurable_constraints(self):
    objective_terms = []
    
    dispatch = {
        "daily_subject_limit": self._rule_daily_subject_limit,
        "main_morning": self._rule_main_morning,
        # ... 所有可配置约束
    }
    
    for cfg in self._constraints:
        cid = cfg.get("id")
        enabled = cfg.get("enabled", True)
        ctype = cfg.get("type", "soft")
        weight = cfg.get("weight", 5) * 10
        
        if not enabled:
            continue
        
        handler = dispatch.get(cid)
        if handler:
            handler(ctype, weight, objective_terms)
    
    if objective_terms:
        self.model.Maximize(sum(objective_terms))
```

**好处**：
- 用户可以在前端 UI 中将任何约束在 Hard/Soft 之间切换
- 无解时的诊断可以自动将 Hard 约束放松为 Soft 来定位冲突

---

## 七、连堂课建模

### 7.1 SessionBuilder 拆分逻辑

```python
if needs_continuous and weekly_hours >= 2:
    # 恰好 1 次连堂 (占 2 课时)
    sessions.append(ScheduleSession(
        id=sid, duration=2, is_continuous_pair=True, ...
    ))
    # 剩余为单节
    for _ in range(weekly_hours - 2):
        sessions.append(ScheduleSession(
            id=sid, duration=1, is_continuous_pair=False, ...
        ))
```

### 7.2 连堂在约束中的影响

`duration=2` 的 Session 在约束检查时需要考虑两个时刻：

```python
# 遍历变量时展开 duration
for (day, period), var in self.x[sid].items():
    for p in range(period, period + s.duration):  # duration=2 → p, p+1
        slot_map[(day, p)].append(var)
```

### 7.3 连堂不跨午休

在变量域过滤阶段就排除了跨午休的情况：

```python
# 午休在第 5-6 节之间
if session.duration > 1 and period <= 5 < end_period:
    continue  # 不允许连堂跨 5-6 节
```

---

## 八、教研组组会建模

### 8.1 问题描述

同一教研组的所有教师需要每周有 2 节连续的空闲时段用于组会。

### 8.2 建模方法

引入**组会选择变量** `meeting_vars[(day, period)]`：

```python
# 为每个教研组创建组会时段选择变量
for gid, tids in group_teachers.items():
    meeting_vars = {}
    valid_starts = [1, 2, 3, 4, 6, 7, 8]  # 不跨午休
    
    for day in range(1, 6):
        for p in valid_starts:
            var = model.NewBoolVar(f"meet_g{gid}_d{day}_p{p}")
            meeting_vars[(day, p)] = var
    
    # Hard: 恰好选 1 个时段
    model.AddExactlyOne(list(meeting_vars.values()))
    
    # 当组会时段被选中时，该组所有教师在那 2 节不能有课
    for (day, p_start), m_var in meeting_vars.items():
        for sid in group_sids:
            for target_p in [p_start, p_start + 1]:
                for (d, p), x_var in self.x[sid].items():
                    if d == day and p <= target_p < p + s.duration:
                        # 条件约束: m_var=1 => x_var=0
                        model.Add(x_var == 0).OnlyEnforceIf(m_var)
```

### 8.3 关键技巧：OnlyEnforceIf

`OnlyEnforceIf(literal)` 是 CP-SAT 的条件约束（也叫指示约束/Indicator Constraint）：

```python
# 只有当 condition 为 True 时，约束才生效
model.Add(x == 0).OnlyEnforceIf(condition)

# 等价于逻辑蕴含: condition → x == 0
# 如果 condition 为 False，约束被忽略
```

这在本项目中大量使用，特别是在组会约束中：只有当某个时段被选为组会时段时，才禁止排课。

---

## 九、诊断与无解分析

### 9.1 诊断思路

当求解结果为 `INFEASIBLE` 时，我们需要找出哪条约束导致了矛盾。方法是**逐层叠加约束**：

```
仅 H1 → 可行 ✓
H1 + H2 → 可行 ✓
H1 + H2 + H3 → 可行 ✓
H1 + H2 + H3 + H4 → 不可行 ✗ ← H4 是冲突源！
```

### 9.2 实现代码

```python
def _diagnose_infeasibility(self):
    layers = [
        ("H1: 课程必须排入", [self._h1_exactly_one]),
        ("H2: 教师无冲突", [self._h2_teacher_no_conflict]),
        ("H3: 班级无冲突", [self._h3_class_no_conflict]),
        ("H4: 场地容量", [self._h4_venue_capacity]),
        # + 所有配置为 Hard 的业务约束
    ]
    
    accumulated_fns = []
    for layer_name, fns in layers:
        accumulated_fns.extend(fns)
        
        # 重建干净的模型
        self.model = cp_model.CpModel()
        self.x = {}
        self._create_variables()
        
        # 应用已累积的约束
        for fn in accumulated_fns:
            fn()
        
        # 快速求解（只判断可行性，不优化）
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 30
        status = solver.Solve(self.model)
        
        if status == cp_model.INFEASIBLE:
            return {"failed": layer_name, "suggestion": "..."}
```

### 9.3 诊断注意事项

- 每次诊断都**重建模型**（`CpModel()`），确保干净无副作用
- 使用较短的时间限制（30秒），只需判断可行性
- 诊断结果包含建议信息，引导用户调整数据或切换约束模式

---

## 十、多方案多样性

### 10.1 问题

用户可能希望生成多个不同的排课方案来对比。CP-SAT 默认会返回相同（或相似）的解。

### 10.2 多样性约束

在第 2 个及后续方案中，添加"与前一个方案至少 N% 不同"的约束：

```python
def _rebuild_model_for_diversity(self, prev_solutions, idx, lenient=False):
    # 收集前一个方案中每个 session 的分配
    prev_assignments = {session_id: (day, period) for ...}
    
    # 重建模型（包含所有原始约束）
    self.model = cp_model.CpModel()
    self._create_variables()
    self._add_tier1_constraints()
    self._apply_configurable_constraints()
    
    # 多样性约束
    diff_ratio = 20 if lenient else 10  # 至少 5% 或 10% 不同
    
    for prev in prev_assignments:
        same_vars = []
        for sid, (day, period) in prev.items():
            if (day, period) in self.x.get(sid, {}):
                same_vars.append(self.x[sid][(day, period)])
        
        min_diff = max(1, len(same_vars) // diff_ratio)
        self.model.Add(sum(same_vars) <= len(same_vars) - min_diff)
```

### 10.3 随机种子

不同方案使用不同的随机种子，让搜索路径不同：

```python
seed_base = int(time.time()) % 100000
solver.parameters.random_seed = seed_base + idx * 37
```

---

## 十一、求解器调优

### 11.1 关键参数

```python
solver = cp_model.CpSolver()

# 时间限制（秒）
solver.parameters.max_time_in_seconds = 120

# 工作线程数（利用多核 CPU）
solver.parameters.num_workers = 4

# 随机种子（确保不同运行产生不同结果）
solver.parameters.random_seed = 42

# 开启求解日志（调试用）
solver.parameters.log_search_progress = True
```

### 11.2 优化等级映射

本项目根据用户选择的优化等级设定时间限制：

```python
time_limits = {
    1: 30,   # 快速 - 30秒
    2: 60,   # 标准 - 1分钟
    3: 120,  # 高质量 - 2分钟
    4: 300,  # 深度优化 - 5分钟
    5: 600,  # 极致优化 - 10分钟
}
```

### 11.3 性能优化建议

| 优化手段 | 说明 | 效果 |
|---------|------|------|
| 变量域过滤 | 创建变量时排除不合法的时间槽 | 减少 30-50% 变量 |
| 预计算索引 | 提前建好 teacher/class/venue → session 索引 | 约束添加加速 10x |
| 短路跳过 | `if len(sids) < 2: continue` | 避免无意义约束 |
| 容量预检 | `if len(sids) <= cap: continue` | 跳过不必要的场地约束 |
| 增量多方案 | 在已有约束上添加多样性约束而非重新求解 | 后续方案更快 |

---

## 十二、常用 API 速查

### 变量创建

```python
model.NewBoolVar('name')           # 布尔变量 {0, 1}
model.NewIntVar(lb, ub, 'name')    # 整数变量 [lb, ub]
model.NewConstant(value)            # 常量
```

### 常用约束

```python
model.Add(expr <= value)           # 线性不等式
model.Add(expr == value)           # 线性等式
model.AddExactlyOne(vars)         # 恰好一个为 True
model.AddAtMostOne(vars)          # 至多一个为 True
model.AddAtLeastOne(vars)         # 至少一个为 True
model.AddAllDifferent(vars)       # 所有变量取不同值

# 条件约束
model.Add(x == 0).OnlyEnforceIf(b)       # b=True 时 x=0
model.Add(x == 0).OnlyEnforceIf(b.Not()) # b=False 时 x=0

# 数组元素
model.AddElement(index, array, target)    # target = array[index]

# 表约束
model.AddAllowedAssignments([x, y], [(1,2), (3,4)])
model.AddForbiddenAssignments([x, y], [(1,1)])
```

### 目标函数

```python
model.Maximize(expression)
model.Minimize(expression)
```

### 求解与结果

```python
status = solver.Solve(model)
value = solver.Value(var)           # 获取变量值
obj = solver.ObjectiveValue()       # 获取目标值
wall_time = solver.WallTime()       # 求解耗时
```

---

## 十三、常见陷阱与最佳实践

### 13.1 陷阱：忘记处理连堂的 duration

```python
# ❌ 错误：只检查起始时刻
for (day, period), var in self.x[sid].items():
    slot_map[(day, period)].append(var)

# ✅ 正确：展开连堂占据的所有时刻
for (day, period), var in self.x[sid].items():
    for p in range(period, period + s.duration):
        slot_map[(day, p)].append(var)
```

### 13.2 陷阱：软约束权重比例不当

权重差异太小（如 5 vs 6），求解器可能忽略优先级差异。建议：

```python
# 内部将权重 × 10，拉开梯度
weight = cfg.get("weight", 5) * 10
```

### 13.3 陷阱：诊断时不重建模型

```python
# ❌ 错误：在原模型上添加约束（约束会累积）
self._h1_exactly_one()
solver.Solve(self.model)
self._h2_teacher_no_conflict()  # 约束在 H1 基础上叠加了！
solver.Solve(self.model)

# ✅ 正确：每次诊断都重建模型
self.model = cp_model.CpModel()
self.x = {}
self._create_variables()
```

### 13.4 最佳实践：索引命名规范

给变量起有意义的名字，方便调试：

```python
# ✅ 好的命名
model.NewBoolVar(f"x_s{session_id}_d{day}_p{period}")
model.NewBoolVar(f"meet_g{group_id}_d{day}_p{period}")
model.NewIntVar(0, 10, f"exc_h5_{class_id}_{subject_id}_{day}")
```

### 13.5 最佳实践：日志输出

在每个约束添加步骤输出统计信息：

```python
print(f"    H2: 教师无冲突 {count} 条")
print(f"    H4: 场地容量 {count} 条")
print(f"    规则 [主科上午]: {ctype.upper()}, 涉及 {count} 项")
```

### 13.6 最佳实践：提前检查无效数据

```python
# 跳过无合法槽位的 session
slot_vars = list(self.x[s.id].values())
if not slot_vars:
    skipped += 1
    continue

# 跳过不需要约束的情况
if len(sids) < 2:
    continue  # 只有一个 session，不会冲突
```

---

## 附录：本项目约束实现一览

| 约束 ID | 约束名称 | 实现函数 | 模式 |
|---------|---------|---------|------|
| H1 | 课程必须排入 | `_h1_exactly_one()` | 固定 Hard |
| H2 | 教师无冲突 | `_h2_teacher_no_conflict()` | 固定 Hard |
| H3 | 班级无冲突 | `_h3_class_no_conflict()` | 固定 Hard |
| H4 | 场地容量 | `_h4_venue_capacity()` | 固定 Hard |
| R1 | 每日同科目上限 | `_rule_daily_subject_limit()` | Hard/Soft |
| R2 | 主科上午 | `_rule_main_morning()` | Hard/Soft |
| R3 | 均匀分布 | `_rule_balanced_distribution()` | Hard/Soft |
| R4 | 艺体非首节 | `_rule_artpe_not_first()` | Hard/Soft |
| R5 | 场地分散 | `_rule_venue_dispersion()` | Hard/Soft |
| R6 | 早晚班 | `_rule_teacher_shift()` | Hard/Soft |
| R7 | 会议预留 | `_rule_meeting_reservation()` | Hard/Soft |
| R8 | 教研组组会 | `_rule_department_meeting()` | Hard/Soft |
| R9 | 管理干部会议 | `_rule_admin_afternoon()` | Hard/Soft |

---

*本文档基于 cp_solver.py 实际代码整理。如有更新，请同步修改本文档。*
