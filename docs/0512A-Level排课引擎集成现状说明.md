# A-Level 排课与现有引擎集成现状说明

> **本文档记录 A-Level（课程班/选课）与行政班排课引擎的解耦现状，供后续架构决策参考。**
>
> 整理日期: 2026-05-12 | 适用范围: 排课引擎架构、A-Level 模块扩展

---

## 一、核心结论：双轨制架构

当前系统中，**行政班排课**与 **A-Level 排课**运行在两条完全独立的轨道上：

| 维度 | 行政班排课 | A-Level 排课 |
|------|-----------|-------------|
| **数据入口** | `TeachingTask`（教学任务） | `CourseClass.schedule_pattern`（预定义 JSON） |
| **引擎加载** | ✅ `loader.py` 加载到 `ScheduleData` | ❌ 引擎完全不可见 |
| **约束求解** | ✅ CP-SAT 自动求解（H1-H4 + R1-R9） | ❌ 不参与任何约束计算 |
| **冲突检查** | ✅ 教师/班级/场地冲突自动避免 | ❌ 零冲突检查 |
| **结果存储** | ✅ `schedule_items` 表 | ❌ 存在 `course_classes.schedule_pattern` |
| **学生课表** | 基础数据 | 展示层内存拼接叠加 |

**一句话总结**：A-Level 课程的时间安排是「人工预定义」的，排课引擎不知道 A-Level 课程的存在，也不会为其计算最优时间或检查约束冲突。

---

## 二、技术现状详细分析

### 2.1 排课引擎不加载 A-Level 数据

**关键代码位置**：`backend/app/engine/data/loader.py`

```python
class DatabaseLoader:
    def load(self, db: Session) -> ScheduleData:
        """加载六类核心数据"""
        return ScheduleData(
            teachers=self._load_teachers(db),
            classes=self._load_classes(db),      # ← 只加载行政班 classes
            subjects=self._load_subjects(db),
            venues=self._load_venues(db),
            layer_groups=self._load_layer_groups(db),
            tasks=self._load_tasks(db),          # ← 只加载 TeachingTask（行政班任务）
        )
```

**未加载的数据**：
- `CourseClass`（课程班）— 完全未查询
- `CourseSelection`（选课记录）— 完全未查询
- `AlevelSubject`（A-Level 科目）— 完全未查询
- `CourseClassMember`（课程班成员）— 完全未查询

**引擎内部模型**：`backend/app/engine/data/models.py` 中的 `ScheduleData` 没有任何 A-Level 相关字段。

### 2.2 A-Level 课程的时间靠 `schedule_pattern` 预定义

**关键代码位置**：`backend/app/modules/course_classes/models.py`

```python
class CourseClass(Base):
    __tablename__ = "course_classes"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)
    alevel_subject_id = Column(Integer, ForeignKey("alevel_subjects.id"))
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=True)
    schedule_pattern = Column(JSON, default={})   # ← A-Level 课的时间存在这里
    # ... 其他字段
```

`schedule_pattern` 的典型内容：
```json
{
  "slots": [
    {"day": 1, "period": 6},
    {"day": 3, "period": 6},
    {"day": 5, "period": 6}
  ]
}
```

这意味着 A-Level 课程的时间是：
- **人工指定**：创建课程班时由用户在 UI 中选择时间槽
- **不参与求解**：CP-SAT 求解器不会为 A-Level 课程寻找最优时间
- **不检查冲突**：即使 A-Level 课与行政班课在同一时间，系统也不会告警

### 2.3 学生个人课表是「展示层拼接」

**关键代码位置**：`backend/app/modules/schedules/router.py` 第 453-593 行，`get_student_timetable()`

#### 拼接逻辑（两步）

**Step 1：加载行政班课程**
```python
# 从 schedule_items 查询该学生行政班的课表
items = db.query(ScheduleItem).filter(
    ScheduleItem.schedule_id == schedule_id,
    ScheduleItem.class_id == student.class_id
).all()

# 放入 timetable 字典，key = "{day}-{period}"
for item in items:
    key = f"{item.day}-{item.period}"
    timetable[key] = {
        "subject_name": subject.name,
        "teacher_name": teacher.name,
        "type": "homeroom",
        "note": "行政班课程"
    }
```

**Step 2：加载 A-Level 课程并叠加**
```python
# a) 找到学生 enrolled 的所有课程班
members = db.query(CourseClassMember).filter(
    CourseClassMember.student_id == student_id,
    CourseClassMember.status == "ENROLLED"
).all()

# b) 解析每个课程班的 schedule_pattern
for member in members:
    course_class = member.course_class
    pattern = course_class.schedule_pattern or {}
    slots = pattern.get("slots", [])
    
    for slot in slots:
        key = f"{slot['day']}-{slot['period']}"
        
        if key in timetable:
            # 冲突：行政班已有课 → 叠加 A-Level 信息
            timetable[key]["alevel_subject"] = subject_name
            timetable[key]["alevel_teacher"] = teacher_name
            timetable[key]["note"] = f"行政班: {homeroom_subject} | A-Level: {subject_name}"
        else:
            # 无冲突：直接插入 A-Level 课程
            timetable[key] = {
                "subject_name": subject_name,
                "teacher_name": teacher_name,
                "type": "alevel",
                "note": f"A-Level: {subject_name}"
            }
```

#### 冲突处理策略

| 场景 | 处理方式 | 风险 |
|------|---------|------|
| A-Level 与行政班同时间段 | 行政班优先显示，A-Level 作为附加标记 | 用户可能看不到冲突 |
| A-Level 课之间同时间段 | 后加载的覆盖先加载的（无合并） | 学生同时上两门 A-Level 课 |
| 教师同时教两个 A-Level 班 | 不做任何检查 | 教师时间冲突 |
| A-Level 需要特殊场地 | 不做任何检查 | 场地超容 |

**本质**：这只是一个「数据拼接」操作，不是约束满足计算。

---

## 三、已识别的具体问题

### 🔴 高风险问题

| # | 问题 | 影响 | 触发条件 |
|---|------|------|---------|
| 1 | **A-Level 与行政班课程时间冲突无告警** | 学生课表显示两门课同时上，实际无法分身 | 只要 schedule_pattern 与 schedule_items 有重叠 day-period |
| 2 | **A-Level 教师时间冲突无检查** | 同一教师被分配到两个同时段的 A-Level 班 | 同一 teacher_id 的两个 CourseClass 有重叠 slot |
| 3 | **学生 A-Level 课之间时间冲突无检查** | 学生同时选了多门时间重叠的 A-Level | 同一学生的多个 CourseClass 有重叠 slot |
| 4 | **场地冲突无检查** | 特殊场地（如实验室）同时被多个 A-Level 班使用 | 多个 CourseClass 在同一时段使用同一 venue |

### 🟡 中风险问题

| # | 问题 | 影响 |
|---|------|------|
| 5 | **A-Level 课无法使用自动排课优化** | 无法利用 CP-SAT 的软约束（如主科上午优先、均匀分布等）优化 A-Level 时间安排 |
| 6 | **A-Level 课无法参与调课/锁定** | 前端调课界面（TimetableView）只能操作行政班 schedule_items，A-Level 课无法拖拽调整 |
| 7 | **排课方案不包含 A-Level** | 导出/打印的课表如果不用 by-student 接口，会丢失所有 A-Level 课程 |
| 8 | **schedule_pattern 无版本管理** | 修改 A-Level 时间后无历史记录，无法回滚 |

---

## 四、架构对比图

### 当前架构（双轨制）

```
┌─────────────────────────────────────────────────────────────────┐
│                        行政班排课轨道                            │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐ │
│  │TeachingTask│ → │CP-SAT求解│ → │schedule_ │ → │ 课表查看  │ │
│  │ (行政班)  │    │ (H1-R9)  │    │ items   │    │ (by-class)│ │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              ↑
                              │ 展示层合并（by-student）
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                        A-Level 排课轨道                          │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐                 │
│  │CourseClass│ → │schedule_ │ → │ 内存拼接  │                 │
│  │(手工录入) │    │ pattern  │    │ (router) │                 │
│  └──────────┘    └──────────┘    └──────────┘                 │
│       ↑                                                          │
│   CourseSelection (学生选课后确定成员)                            │
└─────────────────────────────────────────────────────────────────┘
```

### 理想架构（统一轨道）

```
┌─────────────────────────────────────────────────────────────────┐
│                      统一排课引擎                                │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │Teaching  │  │ Course   │  │ Layer    │  │  Venue   │       │
│  │Task      │  │ Class    │  │ Group    │  │          │       │
│  │(行政班)   │  │(A-Level) │  │(分层/合班)│  │(场地)    │       │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘       │
│       └─────────────┴─────────────┴─────────────┘              │
│                         ↓                                        │
│                  ┌──────────────┐                               │
│                  │ SessionBuilder │ ← 统一构建 ScheduleSession   │
│                  └──────┬───────┘                               │
│                         ↓                                        │
│                  ┌──────────────┐                               │
│                  │  CP-SAT 求解  │ ← 统一约束（含A-Level规则）   │
│                  └──────┬───────┘                               │
│                         ↓                                        │
│                  ┌──────────────┐                               │
│                  │ schedule_items│ ← 统一存储所有课程            │
│                  └──────┬───────┘                               │
│                         ↓                                        │
│                  ┌──────────────┐                               │
│                  │  课表查看/导出  │ ← 统一查询，无需拼接         │
│                  └──────────────┘                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## 五、扩展方案（如需要统一排课）

如果业务上需要 A-Level 课程也纳入自动排课，需要以下改造：

### 5.1 数据层改造

**文件**：`backend/app/engine/data/loader.py`

```python
def load(self, db: Session) -> ScheduleData:
    return ScheduleData(
        teachers=self._load_teachers(db),
        classes=self._load_classes(db),
        subjects=self._load_subjects(db),
        venues=self._load_venues(db),
        layer_groups=self._load_layer_groups(db),
        tasks=self._load_tasks(db),
        # 新增：加载 A-Level 数据
        alevel_classes=self._load_alevel_classes(db),
        alevel_selections=self._load_alevel_selections(db),
    )
```

### 5.2 引擎内部模型扩展

**文件**：`backend/app/engine/data/models.py`

```python
@dataclass
class AlevelSession:
    """A-Level 课程会话（引擎内部表示）"""
    id: int
    subject_id: int
    subject_name: str
    teacher_id: Optional[int]
    teacher_name: str
    student_ids: List[int]          # 哪些学生上这门课
    weekly_hours: int
    preferred_slots: List[Tuple[int, int]]  # (day, period) 偏好
    required_room_type: Optional[str]

@dataclass
class ScheduleData:
    # ... 原有字段 ...
    alevel_sessions: List[AlevelSession] = field(default_factory=list)
```

### 5.3 约束层新增规则

**文件**：`backend/app/engine/solver/cp_solver.py`

建议新增以下约束（Tier 2/3）：

| 约束ID | 类型 | 说明 |
|--------|------|------|
| `alevel_no_homeroom_conflict` | Hard | A-Level 课不与行政班主科（语数英）冲突 |
| `alevel_teacher_no_conflict` | Hard | A-Level 教师同一时间只能上一门课 |
| `alevel_student_no_conflict` | Hard | 同一学生的 A-Level 课时间不重叠 |
| `alevel_venue_capacity` | Hard | A-Level 课使用场地不超过容量 |
| `alevel_afternoon_preference` | Soft | A-Level 课优先安排在下午（避免与行政班主科抢上午） |
| `alevel_continuous_preference` | Soft | A-Level 同科目连堂课尽量安排在相邻时段 |

### 5.4 SessionBuilder 扩展

**文件**：`backend/app/engine/solver/session_builder.py`

```python
def build(self) -> List[ScheduleSession]:
    sessions = []
    # 原有：行政班任务 → Session
    for task in self.data.tasks:
        sessions.extend(self._task_to_sessions(task))
    
    # 新增：分层组任务 → Session
    for layer in self.data.layer_groups:
        sessions.extend(self._layer_to_sessions(layer))
    
    # 新增：A-Level 课程 → Session
    for alevel in self.data.alevel_sessions:
        sessions.extend(self._alevel_to_sessions(alevel))
    
    return sessions
```

### 5.5 存储层扩展

**文件**：`backend/app/engine/core.py`

```python
def _save_results(self, records: List[ScheduleRecord]):
    for record in records:
        item = ScheduleItem(
            schedule_id=self.schedule_id,
            task_id=record.task_id,
            # 新增：区分行政班和 A-Level
            course_class_id=record.course_class_id,  # ← 新增字段
            day=record.day,
            period=record.period,
            # ...
        )
        db.add(item)
```

> ⚠️ 需要修改 `schedule_items` 表结构：新增 `course_class_id` 字段（nullable），或创建独立的 `alevel_schedule_items` 表。

### 5.6 前端层扩展

**文件**：`frontend/src/views/TimetableView.vue`

- 调课/拖拽逻辑需要支持 A-Level 课程
- 锁定/解锁功能需要支持 A-Level 课程
- 约束违反验证需要包含 A-Level 规则

---

## 六、工作量估算

| 阶段 | 内容 | 预估时间 |
|------|------|---------|
| **数据层** | loader 加载 A-Level 数据 | 0.5 天 |
| **模型层** | 引擎内部模型扩展 | 0.5 天 |
| **求解层** | SessionBuilder + CP-SAT 约束新增 | 2-3 天 |
| **存储层** | schedule_items 表扩展 + 保存逻辑 | 1 天 |
| **前端层** | 调课/锁定/验证支持 A-Level | 1-2 天 |
| **测试** | 回归测试 + 冲突场景测试 | 1-2 天 |
| **总计** | | **6-10 天** |

---

## 七、建议的决策路径

### 路径 A：保持现状（推荐如果当前够用）

**适用条件**：
- A-Level 课程数量少（< 30 门），时间固定（如固定在每天第 6 节）
- 学校已有成熟的 A-Level 手工排课流程
- 行政班与 A-Level 的时间冲突可以靠人工经验避免

**需要做的最小改进**：
1. ✅ 在 `by-student` 课表查看中增加**冲突红色高亮**（已有合并，缺冲突提示）
2. ✅ 在 A-Level 课程管理页面增加**教师时间冲突检查**
3. ✅ 在选课提交时增加**学生时间冲突检查**

### 路径 B：轻度集成（推荐如果需要自动化）

**适用条件**：
- A-Level 课程数量中等（30-60 门）
- 希望减少人工排课工作量
- 可以接受 A-Level 课在特定时段池内自动分配

**改造范围**：
- 不改造 CP-SAT 求解器
- 新增一个独立的 **A-Level 排课预处理器**：在行政班排课后，为 A-Level 课程在剩余空闲时段中做贪心分配，检查硬约束冲突
- 结果存入 `schedule_items`（新增字段或独立表）

### 路径 C：完全统一（推荐如果追求长期架构）

**适用条件**：
- A-Level 课程数量多（> 60 门），与行政班深度交错
- 需要全局最优解（如最大化场地利用率、最小化教师空窗期）
- 愿意投入 1-2 周开发时间

**改造范围**：
- 完整执行第 5 节的所有改造
- A-Level 与行政班统一走 CP-SAT 求解

---

## 八、相关代码索引

| 文件 | 作用 |
|------|------|
| `backend/app/engine/data/loader.py` | 引擎数据加载（不加载 A-Level） |
| `backend/app/engine/data/models.py` | 引擎内部数据模型（无 A-Level） |
| `backend/app/engine/core.py` | ScheduleEngine 主控、结果保存 |
| `backend/app/engine/solver/cp_solver.py` | CP-SAT 约束求解 |
| `backend/app/engine/solver/session_builder.py` | ScheduleSession 构建 |
| `backend/app/modules/schedules/router.py:453-593` | by-student 课表拼接逻辑 |
| `backend/app/modules/course_classes/models.py` | CourseClass（含 schedule_pattern） |
| `backend/app/modules/course_selections/models.py` | CourseSelection（学生选课记录） |
| `frontend/src/views/TimetableView.vue` | 课表查看/调课前端 |

---

> 文档版本: v1.0 | 整理于 2026-05-12
