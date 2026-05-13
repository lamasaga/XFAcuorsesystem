# A-Level 排课系统现状与待办事项

> 文档生成时间：2026-05-13
> 最后更新：2026-05-13（连堂课约束 + G12 支持）

---

## 一、系统架构概览

### 1.1 排课流程（顺序排课模式）

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  行政班排课      │ --> │  A-Level 排课     │ --> │   结果保存       │
│  CP-SAT 求解器   │     │  AlevelSchedule  │     │  ScheduleItem   │
│  (PK-G9 为主)   │     │   Solver         │     │  (homeroom +    │
│                 │     │  (G10-G12 选修)  │     │   alevel)       │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

### 1.2 时间槽配置

| 学部 | 年级范围 | Mon-Thu 节次 | 周五节次 | 特殊时段 |
|------|---------|-------------|---------|---------|
| PRIMARY | PK-G5 | 1-8 | 1-8 | 无 |
| SECONDARY | G6-G9 | 1-9 (周四G8/G9可到11) | 1-8 | 周四10-11为选修课 |
| SENIOR | G10-G12 (A-Level) | 1-13 (含选修+晚自习) | 1-8 | 10-11选修课, 12-13晚自习 |

---

## 二、本次修改内容（2026-05-13）

### 2.1 G12 年级支持

**问题**：前端 `ClassManagement.vue` 的 `secondaryGrades` 数组缺少 G12，导致 G12 班级无法在前端显示。

**修改文件**：`frontend/src/views/data/ClassManagement.vue`

**修改内容**：
- `secondaryGrades` 新增 `{ key: 'G12', name: 'G12 (十二年级/毕业)' }`
- 班级表单中学部年级选项从 `g in 6` 改为 `g in 7`（覆盖 G6-G12）
- 升班提示从 "PK ~ G10" 修正为 "PK ~ G11"

**后端状态**：✅ 已支持（`GRADE_ORDER` 含 G12，升班逻辑已处理 G12→毕业）

### 2.2 A-Level 连堂课约束（独立设计）

**问题**：A-Level 课程有很多连堂课（double period），但之前所有 session 的 `duration=1`（单节），且没有连堂课边界约束。如果复用行政班的 `ContinuousBreakConstraint` 等硬约束，会由于年级范围不同（PK-G9 vs G10-G12）导致问题。

**解决方案**：在 `AlevelScheduleSolver` 中独立设计连堂课约束，与行政班硬约束完全解耦。

**修改文件**：`backend/app/engine/alevel_solver.py`

**新增约束**（在 `_build_available_slots` 中物理过滤）：

| 约束ID | 说明 | 规则 |
|--------|------|------|
| AL-C1 | 不跨午休 | 连堂课不能跨越第5节和第6节之间 |
| AL-C2 | 不跨正课/选修课边界 | 连堂课不能跨越第9节和第10节之间 |
| AL-C3 | 不跨选修课/晚自习边界 | 连堂课不能跨越第11节和第12节之间 |
| AL-C4 | 周五不连堂 | 周五只有8节课，时间不充裕，不安排连堂课 |
| AL-C5 | 最大连堂节数 | A-Level 连堂最多2节（不支持3节连堂） |

**冲突约束增强**（在 `_add_constraints` 中）：
- 教师冲突：现在正确考虑 `duration`，连堂课占用的 `[period, period+duration-1]` 所有时段都会检查
- 学生冲突：同样正确考虑 `duration` 覆盖

**验证结果**：
- 单节课程：可在全部 60 个时段安排（Mon-Thu 13节×4天 + Fri 8节）
- 连堂课程（duration=2）：Mon-Thu 有 36 个合法起始时段，周五无
- 三连堂（duration=3）：全部被过滤，无合法时段
- 冲突检测：同一学生/教师在同一时段的连堂课会被正确检测为不可解（INFEASIBLE）

---

## 三、A-Level 排课约束完整清单

### 3.1 硬约束

| 约束 | 来源 | 说明 |
|------|------|------|
| C1 每个session恰好一个槽位 | `alevel_solver.py` | 基本分配约束 |
| C2 教师不冲突 | `alevel_solver.py` | 同一教师同一时刻只能上一门课（duration感知） |
| C3 学生不冲突 | `alevel_solver.py` | 同一学生同一时刻只能上一门课（duration感知） |
| AL-C1 不跨午休 | `alevel_solver.py` | 连堂课不跨5-6节 |
| AL-C2 不跨正课/选修边界 | `alevel_solver.py` | 连堂课不跨9-10节 |
| AL-C3 不跨选修/晚自习边界 | `alevel_solver.py` | 连堂课不跨11-12节 |
| AL-C4 周五不连堂 | `alevel_solver.py` | 周五不安排连堂课 |
| AL-C5 最大连堂2节 | `alevel_solver.py` | 不支持3节及以上连堂 |
| 行政班占用 | `core.py` → `teacher_occupied` | A-Level 排课时避开行政班已占时段 |

### 3.2 软约束（目标函数）

| 优先级 | 时段 | 分数 | 说明 |
|--------|------|------|------|
| P1 | 第 10-11 节 | +100 | 选修课时间，首选 |
| P2 | 第 8-9 节 | +50 | 次选 |
| P3 | 第 6-7 节 | +20 | 再次选 |
| P4 | 第 1-5 节 | +5 | 尽量避免，与行政班重叠 |
| - | 周五 | -30 | 周五只有8节，通常不安排 A-Level |

---

## 四、尚未处理的问题与潜在风险

### 4.1 🔴 高优先级

#### ISSUE-1: student_occupied 未从行政班排课结果传递

**现状**：`ScheduleEngine.run()` 中只构建了 `teacher_occupied` 传递给 `AlevelScheduleSolver`，**没有构建 `student_occupied`**。

**代码位置**：`backend/app/engine/core.py`

```python
# 当前代码（只有 teacher_occupied）
teacher_occupied = self._build_teacher_occupied(records)
alevel_solver = AlevelScheduleSolver(
    self.data,
    teacher_occupied=teacher_occupied,
    prefer_elective_slots=True,
)
```

**影响**：
- A-Level 排课时，只检查了教师是否被行政班占用
- **没有检查学生是否被行政班占用**
- 这可能导致 A-Level 课程与学生行政班课程冲突

**建议修复**：
```python
# 在 core.py 中新增 _build_student_occupied 方法
teacher_occupied = self._build_teacher_occupied(records)
student_occupied = self._build_student_occupied(records)  # 新增
alevel_solver = AlevelScheduleSolver(
    self.data,
    teacher_occupied=teacher_occupied,
    student_occupied=student_occupied,  # 新增
    prefer_elective_slots=True,
)
```

**状态**：⚠️ 待修复

---

#### ISSUE-2: A-Level 课程 duration 目前固定为 1

**现状**：`DatabaseLoader._load_alevel_sessions()` 中 `duration=1` 是硬编码的。

**代码位置**：`backend/app/engine/data/loader.py`

```python
sessions.append(AlevelScheduleSession(
    # ...
    duration=1,  # 默认单节，可后续扩展为连堂
    # ...
))
```

**影响**：
- 即使 `AlevelScheduleSolver` 已支持连堂课约束，但数据加载层没有根据科目配置生成连堂 session
- 当前所有 A-Level 课程都是单节（duration=1）

**建议修复**：
1. 在 `alevel_subjects` 表或 `course_classes` 表中增加 `is_continuous` / `class_duration` 字段
2. 修改 `DatabaseLoader._load_alevel_sessions()` 根据配置设置 duration
3. 或者根据 `weekly_hours` 自动拆分：如 weekly_hours=4，可拆分为 2 个 duration=2 的 session

**状态**：⚠️ 待修复（需要产品决策：连堂配置放在科目层还是课程班层）

---

### 4.2 🟡 中优先级

#### ISSUE-3: A-Level 场地约束未实现

**现状**：`AlevelScheduleSession.required_venue_type` 始终为 `None`。

**影响**：A-Level 课程（如物理实验、化学实验）可能需要特定场地，但当前不考虑场地容量限制。

**建议修复**：
1. 在 `alevel_subjects` 或 `course_classes` 中增加 `required_venue_type` 字段
2. 在 `AlevelScheduleSolver` 中增加场地容量约束（参考 `CPScheduleSolver` 的 `_rule_venue_dispersion`）

**状态**：📋 待规划

---

#### ISSUE-4: 同一 A-Level 科目多日连堂分布

**现状**：如果一个 A-Level 科目 weekly_hours=4，duration=2，会产生 2 个 session。但没有约束确保它们分散在不同天。

**影响**：同一科目的两个连堂课可能排在同一天（如周一第10-11节和周一第12-13节），对学生负担较大。

**建议修复**：在 `AlevelScheduleSolver` 中增加"同一科目每日最多1次"的软约束或硬约束。

**状态**：📋 待规划

---

#### ISSUE-5: G10-G12 行政班排课与 SENIOR 时间槽兼容性

**现状**：行政班排课（`CPScheduleSolver`）中的硬编码逻辑：
- `_get_valid_slots` 中 `10-11 节只允许 G8/G9 周四`
- `_get_max_period` 回退逻辑中 `day==4 and G8/G9` 才返回 11

**影响**：如果 G10-G12 也有行政班课程需要排课，这些硬编码约束会错误地限制它们。

**说明**：当前架构下，G10-G12 的行政班课程可能通过 `department="SECONDARY"` 处理，但时间槽应使用 `SENIOR`。需要确认 G10-G12 行政班是否也走主求解器。

**状态**：❓ 需确认（当前 A-Level 是选修课，走独立求解器；G10-G12 行政班是否走主求解器待确认）

---

### 4.3 🟢 低优先级

#### ISSUE-6: A-Level 教师班次约束未应用

**现状**：`CPScheduleSolver` 有 `_rule_teacher_shift`（早晚班教师约束），但 `AlevelScheduleSolver` 没有。

**影响**：如果 A-Level 教师有早晚班限制，A-Level 排课可能违反该限制。

**状态**：📋 待规划（A-Level 通常在下午/晚上，早晚班影响较小）

---

#### ISSUE-7: A-Level 教研组组会约束未应用

**现状**：`CPScheduleSolver` 有 `_rule_department_meeting`，但 `AlevelScheduleSolver` 没有。

**影响**：A-Level 教师的教研组组会时间可能被 A-Level 课程占用。

**状态**：📋 待规划

---

## 五、自动排课是否处理所有问题？

### ✅ 已正确处理

| 问题 | 处理状态 | 说明 |
|------|---------|------|
| 教师时间冲突 | ✅ | 行政班占用 + A-Level 内部冲突 |
| 学生时间冲突 | ⚠️ 部分 | A-Level 内部冲突已处理，但行政班占用未传递（ISSUE-1） |
| 时段边界 | ✅ | SENIOR 时间槽配置（Mon-Thu 13节 / Fri 8节） |
| 连堂课边界 | ✅ | 本次新增 AL-C1~C5 |
| 优先选修课时段 | ✅ | 软约束优先 10-11 节 |

### ⚠️ 部分处理 / 待修复

| 问题 | 状态 | 跟踪 |
|------|------|------|
| 学生行政班占用 | ⚠️ 未传递 | ISSUE-1 |
| A-Level 连堂配置 | ⚠️ 数据层未支持 | ISSUE-2 |
| 场地约束 | ❌ 未实现 | ISSUE-3 |
| 科目日内分布 | ❌ 未实现 | ISSUE-4 |
| G10-G12 行政班兼容性 | ❓ 待确认 | ISSUE-5 |
| 教师班次 | ❌ 未实现 | ISSUE-6 |
| 教研组组会 | ❌ 未实现 | ISSUE-7 |

---

## 六、下一步建议

1. **立即修复 ISSUE-1**：在 `core.py` 中增加 `_build_student_occupied` 并传递给 A-Level 求解器
2. **产品确认 ISSUE-2**：A-Level 连堂配置放在科目层还是课程班层？
3. **确认 ISSUE-5**：G10-G12 行政班是否走主求解器？如果是，需要调整 `CPScheduleSolver` 的年级判断逻辑
4. **规划 ISSUE-3/4/6/7**：根据实际使用反馈决定优先级

---

## 七、相关文件索引

| 文件 | 说明 |
|------|------|
| `backend/app/engine/alevel_solver.py` | A-Level 排课求解器（本次主要修改） |
| `backend/app/engine/core.py` | 排课引擎总控（需修复 ISSUE-1） |
| `backend/app/engine/data/loader.py` | 数据加载（需修改 ISSUE-2） |
| `backend/app/engine/solver/cp_solver.py` | 行政班 CP-SAT 求解器 |
| `backend/app/engine/constraints/hard.py` | 行政班硬约束（与 A-Level 独立） |
| `frontend/src/views/data/ClassManagement.vue` | 班级管理前端（本次修改 G12 支持） |
| `backend/app/modules/time_slots/init_data.py` | SENIOR 时间槽初始化数据 |
| `backend/app/modules/alevel_subjects/models.py` | A-Level 科目模型 |
| `backend/app/modules/course_classes/models.py` | 课程班模型 |
