# 一生一课表（ALEVEL 选课制）整体思路文档

> 本文档为在现有排课系统基础上，扩展支持 ALEVEL 阶段（G10-G11）"一生一课表"选课模式的顶层设计方案。

---

## 一、项目背景与目标

### 1.1 背景

现有排课系统面向 K-9（小学至初中）的**行政班统一课表**模式设计：
- 每个班级有固定的课表
- 全班学生统一上同样的课程
- 教师按班级分配教学任务

但从 G10（对应 ALEVEL 的 AS 阶段）开始，学生进入 ALEVEL 课程体系：
- 学生从数学/物理/化学/生物/经济/商科/心理等科目中选择 **3-4 门**
- 不同学生选课组合完全不同
- 同一科目按选课学生数组成不同规模的**课程班**
- 需要为每个学生生成**个人专属课表**

### 1.2 目标

在现有排课系统架构基础上，扩展支持 **"一生一课表"** 模式：

| 维度 | 现有系统（G1-G9） | 扩展目标（G10-G11 ALEVEL） |
|------|------------------|---------------------------|
| 课表单位 | 班级（Class） | 学生（Student） |
| 课程分配 | 统一分配 | 自主选课 |
| 教学班组成 | 固定行政班 | 按选课动态组成课程班 |
| 教师任务 | 教某个班某科目 | 教某个课程班某科目 |
| 时间冲突检测 | 班级+教师 | 学生+教师+教室 |
| 场地约束 | 班级容量 | 课程班容量 |

### 1.3 设计原则

1. **最小侵入**：尽量复用现有数据库模型和业务逻辑，通过新增模块而非改造核心
2. **阶段隔离**：ALEVEL 模块与现有 K-9 模块在数据层面可区分，排课流程独立
3. **兼容并存**：学校可能同时运行 K-9 统一课表和 G10-G11 一生一课表
4. **复用引擎**：底层 OR-Tools 排课引擎能力可直接复用，只需调整输入数据构造方式

---

## 二、核心概念设计

### 2.1 概念总览

```
┌─────────────────────────────────────────────────────────────────┐
│                     ALEVEL 选课制概念模型                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   学生 (Student) ──选课──► 选课记录 (CourseSelection)            │
│        │                          │                             │
│        │                          ▼                             │
│        │              ┌─────────────────────┐                  │
│        │              │   ALEVEL 科目池      │                  │
│        │              │  (AleveSubject)     │                  │
│        │              └─────────────────────┘                  │
│        │                          │                             │
│        ▼                          ▼                             │
│   学生个人课表 ◄─────  课程班 (CourseClass)  ◄──── 教师分配     │
│   (StudentSchedule)    │  时间槽 + 教室 + 教师                  │
│                        │                                       │
│                        ▼                                       │
│              课程班成员 (CourseClassMember)                    │
│              (student_id + course_class_id)                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 核心实体定义

#### 学生 (Student)

> 注：现有系统没有 Student 实体，需要新增。

| 属性 | 类型 | 说明 |
|------|------|------|
| `id` | PK | 学生ID |
| `name` | string | 姓名 |
| `student_no` | string | 学号 |
| `grade` | string | 年级（G10=AS, G11=A2） |
| `class_id` | FK | 所属行政班ID（保留，用于班主任管理和活动） |
| `email` | string | 联系邮箱 |
| `status` | enum | `ACTIVE` / `INACTIVE` / `GRADUATED` |
| `created_at` | datetime | — |

> 行政班（Class）在 G10-G11 阶段仍然存在，但仅作为**管理单元**（班主任、班会、集体活动等），不再作为**教学单元**。

#### ALEVEL 科目 (AleveSubject)

> 扩展现有 Subject 模型，或新建独立表。

| 属性 | 类型 | 说明 |
|------|------|------|
| `id` | PK | ALEVEL 科目ID |
| `subject_id` | FK | 关联基础科目表（可选，用于与现有科目体系关联） |
| `code` | string | 科目代码，如 `MATHEMATICS`, `PHYSICS`, `ECONOMICS` |
| `name` | string | 科目名称 |
| `name_cn` | string | 中文名称 |
| `exam_board` | enum | 考试局：`CAIE` / `EDEXCEL` / `AQA` |
| `level` | enum | 阶段：`AS` / `A2` / `BOTH`（AS+A2连续两年） |
| `weekly_hours` | int | 标准周课时（如 AS 数学通常 6 课时） |
| `is_continuous` | bool | 是否需要连堂 |
| `required_room_type` | string | 教室类型要求 |
| `color` | string | 课表显示颜色 |
| `max_class_size` | int | 课程班最大人数 |
| `min_class_size` | int | 课程班最小人数（低于此人数不开班） |
| `prerequisites` | JSON | 先修科目要求（如 A2 数学需要先修 AS 数学） |
| `syllabus_code` | string | 考纲代码（如 CAIE 9709） |
| `is_active` | bool | 是否启用 |

#### 选课记录 (CourseSelection)

> 记录学生在某个学年/学期的选课意向或确认结果。

| 属性 | 类型 | 说明 |
|------|------|------|
| `id` | PK | — |
| `student_id` | FK | 学生ID |
| `aleve_subject_id` | FK | ALEVEL 科目ID |
| `academic_year` | string | 学年，如 `2025-2026` |
| `semester` | string | 学期：`FALL` / `SPRING` / `FULL_YEAR` |
| `status` | enum | 状态：`DRAFT` / `SUBMITTED` / `CONFIRMED` / `DROPPED` |
| `priority` | int | 学生填报优先级（1-5，用于冲突调解） |
| `submitted_at` | datetime | 提交时间 |
| `confirmed_at` | datetime | 确认时间 |
| `confirmed_by` | FK | 确认人（教师/管理员ID） |

#### 课程班 (CourseClass)

> ALEVEL 教学的基本单元。同一科目根据选课学生数可能开设多个平行班。

| 属性 | 类型 | 说明 |
|------|------|------|
| `id` | PK | 课程班ID |
| `aleve_subject_id` | FK | ALEVEL 科目ID |
| `code` | string | 课程班代码，如 `MAT-AS-A`, `PHY-AS-B` |
| `name` | string | 课程班名称，如 "AS数学A班" |
| `teacher_id` | FK | 授课教师ID |
| `co_teacher_id` | FK | 助教/协同教师ID（可选） |
| `max_size` | int | 最大人数 |
| `current_size` | int | 当前人数 |
| `weekly_hours` | int | 周课时（可覆盖科目的默认值） |
| `is_continuous` | bool | 是否连堂 |
| `academic_year` | string | 学年 |
| `semester` | string | 学期 |
| `status` | enum | `PLANNED` / `OPEN` / `CLOSED` / `CANCELLED` |
| `created_at` | datetime | — |

#### 课程班成员 (CourseClassMember)

> 学生与课程班的多对多关系。

| 属性 | 类型 | 说明 |
|------|------|
| `id` | PK | — |
| `course_class_id` | FK | 课程班ID |
| `student_id` | FK | 学生ID |
| `joined_at` | datetime | 加入时间 |
| `status` | enum | `ACTIVE` / `TRANSFERRED` / `DROPPED` |

#### 学生个人课表 (StudentScheduleItem)

> 一生一课表的最终输出。从课程班安排派生而来。

| 属性 | 类型 | 说明 |
|------|------|
| `id` | PK | — |
| `schedule_id` | FK | 关联排课方案ID |
| `student_id` | FK | 学生ID |
| `course_class_id` | FK | 课程班ID |
| `day` | int | 星期（1-5） |
| `period` | int | 节次（1-11） |
| `duration` | int | 时长（1=单节, 2=连堂） |
| `is_locked` | bool | 是否锁定 |
| `note` | string | 备注 |

---

### 2.3 关键业务规则

#### 选课规则

1. **选课数量**：G10（AS）学生至少选 3 门，最多选 4 门 ALEVEL 科目
2. **先修要求**：选 A2 级别科目必须先完成对应 AS 级别科目
3. **科目冲突**：某些科目因考试时间冲突不能同时选（由考试局规定）
4. **最低开班人数**：每门课程班最低人数（如 3 人），不足则取消或合并
5. **选课时间窗**：每学期有固定的选课开放/关闭时间

#### 课程班规则

1. **平行班**：同一科目选课人数超过最大班容量时，自动拆分为 A/B/C 班
2. **教师分配**：优先分配有资质的教师（需记录教师的 ALEVEL 科目资质）
3. **课时一致性**：同一课程班的所有学生课时完全相同
4. **跨年级混班**：允许 G10 和 G11 学生在某些科目上同班（如 AS 数学）

#### 排课规则（ALEVEL 特有）

1. **学生时间冲突**：同一学生同一时间不能安排两门课
2. **教师时间冲突**：同一教师同一时间不能安排两门课
3. **教室容量**：课程班人数不能超过教室容量
4. **科目连堂**：实验类科目（物理/化学/生物）建议连堂
5. **考试局协调**：同一考试局的科目考试时间可能冲突，排课时应尽量分散

---

## 三、数据模型扩展设计

### 3.1 新增数据表

```sql
-- ============================================
-- 学生表
-- ============================================
CREATE TABLE students (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    student_no VARCHAR(20) UNIQUE NOT NULL,
    grade VARCHAR(10) NOT NULL,           -- G10, G11
    class_id INTEGER REFERENCES classes(id), -- 所属行政班
    email VARCHAR(100),
    status VARCHAR(20) DEFAULT 'ACTIVE',  -- ACTIVE/INACTIVE/GRADUATED
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    is_deleted BOOLEAN DEFAULT FALSE
);

-- ============================================
-- ALEVEL 科目表
-- ============================================
CREATE TABLE aleve_subjects (
    id SERIAL PRIMARY KEY,
    subject_id INTEGER REFERENCES subjects(id), -- 关联基础科目（可选）
    code VARCHAR(20) UNIQUE NOT NULL,      -- MATHEMATICS, PHYSICS 等
    name VARCHAR(50) NOT NULL,
    name_cn VARCHAR(50),
    exam_board VARCHAR(20) NOT NULL,       -- CAIE, EDEXCEL, AQA
    level VARCHAR(10) NOT NULL,            -- AS, A2, BOTH
    weekly_hours INTEGER DEFAULT 6,
    is_continuous BOOLEAN DEFAULT FALSE,
    required_room_type VARCHAR(30),
    color VARCHAR(10) DEFAULT '#3b82f6',
    max_class_size INTEGER DEFAULT 20,
    min_class_size INTEGER DEFAULT 3,
    prerequisites JSON DEFAULT '[]',       -- 先修科目ID列表
    syllabus_code VARCHAR(20),             -- 考纲代码
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- 选课记录表
-- ============================================
CREATE TABLE course_selections (
    id SERIAL PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES students(id),
    aleve_subject_id INTEGER NOT NULL REFERENCES aleve_subjects(id),
    academic_year VARCHAR(20) NOT NULL,    -- 2025-2026
    semester VARCHAR(20) NOT NULL,         -- FALL, SPRING, FULL_YEAR
    status VARCHAR(20) DEFAULT 'DRAFT',    -- DRAFT/SUBMITTED/CONFIRMED/DROPPED
    priority INTEGER DEFAULT 1,            -- 学生优先级 1-5
    submitted_at TIMESTAMP,
    confirmed_at TIMESTAMP,
    confirmed_by INTEGER REFERENCES teachers(id),
    UNIQUE(student_id, aleve_subject_id, academic_year, semester)
);

-- ============================================
-- 课程班表
-- ============================================
CREATE TABLE course_classes (
    id SERIAL PRIMARY KEY,
    aleve_subject_id INTEGER NOT NULL REFERENCES aleve_subjects(id),
    code VARCHAR(20) NOT NULL,             -- MAT-AS-A
    name VARCHAR(50) NOT NULL,             -- AS数学A班
    teacher_id INTEGER REFERENCES teachers(id),
    co_teacher_id INTEGER REFERENCES teachers(id),
    max_size INTEGER DEFAULT 20,
    current_size INTEGER DEFAULT 0,
    weekly_hours INTEGER,
    is_continuous BOOLEAN DEFAULT FALSE,
    academic_year VARCHAR(20) NOT NULL,
    semester VARCHAR(20) NOT NULL,
    status VARCHAR(20) DEFAULT 'PLANNED',  -- PLANNED/OPEN/CLOSED/CANCELLED
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- 课程班成员表
-- ============================================
CREATE TABLE course_class_members (
    id SERIAL PRIMARY KEY,
    course_class_id INTEGER NOT NULL REFERENCES course_classes(id),
    student_id INTEGER NOT NULL REFERENCES students(id),
    joined_at TIMESTAMP DEFAULT NOW(),
    status VARCHAR(20) DEFAULT 'ACTIVE',   -- ACTIVE/TRANSFERRED/DROPPED
    UNIQUE(course_class_id, student_id)
);

-- ============================================
-- ALEVEL 排课方案表（复用现有 schedules 表）
-- ============================================
-- 复用 schedules 表，通过 type 字段区分：'CLASS_BASED' / 'STUDENT_BASED'
-- ALTER TABLE schedules ADD COLUMN type VARCHAR(20) DEFAULT 'CLASS_BASED';

-- ============================================
-- ALEVEL 课表项（新增）
-- ============================================
CREATE TABLE student_schedule_items (
    id SERIAL PRIMARY KEY,
    schedule_id INTEGER NOT NULL REFERENCES schedules(id),
    student_id INTEGER NOT NULL REFERENCES students(id),
    course_class_id INTEGER NOT NULL REFERENCES course_classes(id),
    day INTEGER NOT NULL,                  -- 1-5
    period INTEGER NOT NULL,               -- 1-11
    duration INTEGER DEFAULT 1,            -- 1=单节, 2=连堂
    is_locked BOOLEAN DEFAULT FALSE,
    note VARCHAR(200)
);
```

### 3.2 现有表扩展

| 表名 | 扩展字段 | 说明 |
|------|---------|------|
| `schedules` | `type` (VARCHAR(20)) | `'CLASS_BASED'`=行政班课表, `'STUDENT_BASED'`=一生一课表 |
| `teachers` | `aleve_subjects` (JSON) | 教师可教授的 ALEVEL 科目资质列表 |
| `teachers` | `exam_boards` (JSON) | 教师有资质的考试局列表 |
| `subjects` | `is_aleve` (BOOLEAN) | 是否可作为 ALEVEL 科目开设 |

---

## 四、与现有系统的衔接设计

### 4.1 模块架构

```
backend/app/
├── modules/
│   ├── ...existing modules...          # 现有模块保持不变
│   ├── students/                        # 【新增】学生管理
│   │   ├── models.py                    # Student
│   │   ├── schemas.py
│   │   ├── router.py
│   │   └── crud.py
│   ├── aleve_subjects/                  # 【新增】ALEVEL 科目管理
│   │   ├── models.py                    # AleveSubject
│   │   ├── schemas.py
│   │   ├── router.py
│   │   └── crud.py
│   ├── course_selections/               # 【新增】选课管理
│   │   ├── models.py                    # CourseSelection
│   │   ├── schemas.py
│   │   ├── router.py
│   │   └── crud.py
│   ├── course_classes/                  # 【新增】课程班管理
│   │   ├── models.py                    # CourseClass, CourseClassMember
│   │   ├── schemas.py
│   │   ├── router.py
│   │   └── crud.py
│   └── student_schedules/               # 【新增】学生课表管理
│       ├── models.py                    # StudentScheduleItem
│       ├── schemas.py
│       ├── router.py
│       └── crud.py
└── engine/
    ├── data/
    │   └── models.py                    # 扩展：新增 AleveTask, AleveSession, StudentScheduleRecord
    └── solver/
        └── cp_solver.py                 # 扩展：支持学生时间冲突约束
```

### 4.2 复用策略

| 现有能力 | 复用方式 | ALEVEL 扩展 |
|---------|---------|------------|
| Teacher 模型 | 直接复用 | 新增 `aleve_subjects`, `exam_boards` 字段 |
| Class 模型 | 复用为行政班 | G10-G11 班级作为管理单元 |
| Subject 模型 | 复用为基础科目 | 新增 AleveSubject 扩展 |
| Venue 模型 | 直接复用 | — |
| Schedule/ScheduleItem | 复用方案管理 | 新增 StudentScheduleItem 存储个人课表 |
| 排课引擎 CP-SAT | 直接复用核心求解器 | 调整 SessionBuilder：将 CourseClass 转为 Session |
| 约束配置 | 复用框架 | 新增 ALEVEL 特有约束 |
| 前端框架 | 完全复用 | 新增页面和组件 |

### 4.3 排课引擎适配

现有引擎的核心抽象 `ScheduleSession` 可以无缝适配 ALEVEL 模式：

```python
# 现有 Session（行政班模式）
class ScheduleSession:
    task_id: int
    teacher_id: int
    class_id: int           # ← 行政班ID
    subject_id: int
    duration: int
    required_venue_type: str

# ALEVEL 模式下的 Session
class AleveScheduleSession:
    course_class_id: int
    teacher_id: int
    student_ids: List[int]  # ← 课程班内所有学生ID
    aleve_subject_id: int
    duration: int
    required_venue_type: str
```

**约束转换**：

| 现有约束 | ALEVEL 等效约束 |
|---------|----------------|
| 班级不冲突（同一班级同一时刻最多一节课） | 学生不冲突（同一学生同一时刻最多一节课） |
| 教师不冲突 | 教师不冲突（不变） |
| 场地容量 | 场地容量（不变） |
| 课程必须排入 | 课程必须排入（不变） |

> 关键变化：将 "班级冲突" 替换为 "学生冲突"。在 CP-SAT 中，这意味着为每个学生-时间槽组合创建一个布尔变量，约束同一时刻该学生只能出现在一个课程班中。

---

## 五、排课流程设计

### 5.1 ALEVEL 排课完整流程

```
阶段一：数据准备
├── 1.1 导入/维护 ALEVEL 科目库（AleveSubject）
├── 1.2 导入学生名单并分配行政班（Student + Class）
├── 1.3 开放选课窗口，学生提交选课意向（CourseSelection）
├── 1.4 选课截止，管理员审核并确认选课（CONFIRMED）
└── 1.5 根据选课结果生成课程班（CourseClass + CourseClassMember）
    └── 自动分班算法：按科目聚合学生 → 按容量拆分为平行班 → 分配教师

阶段二：教学任务生成
├── 2.1 将每个 CourseClass 转为 TeachingTask（或 AleveTask）
│   └── 字段映射：course_class_id → task_id, teacher_id, weekly_hours, is_continuous
└── 2.2 加载场地、教师不可用时间等约束

阶段三：自动排课（复用现有引擎）
├── 3.1 SessionBuilder 构建 AleveScheduleSession
│   └── 每个 CourseClass 的一个 occurrence = 一个 Session
├── 3.2 添加硬约束
│   ├── H1：每个 Session 恰好安排到一个槽位
│   ├── H2：教师不冲突
│   ├── H3：学生不冲突（替代原班级不冲突）
│   └── H4：场地容量
├── 3.3 添加软约束
│   ├── 主科优先上午（如数学、进阶数学）
│   ├── 实验科目连堂（物理/化学/生物）
│   ├── 同一考试局科目分散排布
│   └── ...（可复用现有软约束框架）
└── 3.4 OR-Tools 求解

阶段四：结果输出
├── 4.1 保存 Schedule + StudentScheduleItem
├── 4.2 生成学生个人课表视图
├── 4.3 生成教师课表视图
└── 4.4 生成课程班课表视图

阶段五：调课与锁定
├── 5.1 手动调整课程位置
├── 5.2 锁定已确认的课程项
└── 5.3 重新排课（保留锁定项）
```

### 5.2 自动分班算法

```python
def auto_allocate_course_classes(selections: List[CourseSelection]) -> List[CourseClass]:
    """
    根据选课记录自动生成分班方案
    """
    # 1. 按科目聚合已确认选课的学生
    subject_students = group_by(selections, key=lambda s: s.aleve_subject_id)
    
    for subject_id, students in subject_students.items():
        subject = get_aleve_subject(subject_id)
        total = len(students)
        max_size = subject.max_class_size
        min_size = subject.min_class_size
        
        # 2. 检查是否达到最低开班人数
        if total < min_size:
            mark_as_cancelled(subject_id)
            continue
        
        # 3. 计算需要的平行班数量
        num_classes = ceil(total / max_size)
        
        # 4. 尽可能均匀分配学生到各班
        allocated = distribute_students(students, num_classes)
        
        # 5. 为每个班分配教师（考虑教师资质和负荷）
        for i, class_students in enumerate(allocated):
            teacher = allocate_teacher(subject_id, existing_assignments)
            course_class = create_course_class(
                subject_id=subject_id,
                code=f"{subject.code}-{subject.level}-{chr(65+i)}",  # MAT-AS-A
                teacher_id=teacher.id,
                max_size=max_size,
                current_size=len(class_students),
                weekly_hours=subject.weekly_hours
            )
            add_members(course_class.id, class_students)
```

---

## 六、前端界面设计思路

### 6.1 新增页面路由

```js
// router/index.js 新增路由
const routes = [
  // ... 现有路由
  
  // ALEVEL 一生一课表模块
  { path: '/alevel', name: 'AleveDashboard', component: () => import('@/views/alevel/Dashboard.vue'), meta: { title: 'ALEVEL 管理' } },
  { path: '/alevel/students', name: 'StudentManagement', component: () => import('@/views/alevel/StudentManagement.vue'), meta: { title: '学生管理' } },
  { path: '/alevel/subjects', name: 'AleveSubjectManagement', component: () => import('@/views/alevel/SubjectManagement.vue'), meta: { title: 'ALEVEL 科目' } },
  { path: '/alevel/selection', name: 'CourseSelection', component: () => import('@/views/alevel/CourseSelection.vue'), meta: { title: '选课管理' } },
  { path: '/alevel/classes', name: 'CourseClassManagement', component: () => import('@/views/alevel/CourseClassManagement.vue'), meta: { title: '课程班管理' } },
  { path: '/alevel/schedule', name: 'AleveSchedule', component: () => import('@/views/alevel/AutoSchedule.vue'), meta: { title: 'ALEVEL 排课' } },
  { path: '/alevel/timetable', name: 'StudentTimetable', component: () => import('@/views/alevel/StudentTimetable.vue'), meta: { title: '学生课表' } },
]
```

### 6.2 核心页面设计

#### 学生管理 (StudentManagement)

- 学生列表：姓名、学号、年级、行政班、选课数量
- 批量导入：从 Excel 导入学生名单
- 学生详情：基本信息 + 选课历史 + 个人课表

#### ALEVEL 科目管理 (AleveSubjectManagement)

- 科目卡片网格：代码、名称、考试局、阶段、标准课时
- 配置项：最大/最小学班人数、先修要求、颜色、考纲代码
- 教师资质关联：哪些教师可以教授该科目

#### 选课管理 (CourseSelection)

- **学生视角**（学生登录后）：
  - 可选科目列表（带图标、描述、教师信息）
  - 已选科目篮（3-4门，实时校验冲突）
  - 提交/修改选课
  
- **管理员视角**：
  - 选课概览：各科目选课人数统计
  - 学生选课明细表
  - 批量确认/拒绝/调剂
  - 导出选课报表

#### 课程班管理 (CourseClassManagement)

- 自动分班：一键根据选课结果生成分班方案
- 分班结果列表：班代码、科目、教师、人数、容量
- 手动调整：修改教师、转移学生、合并/拆班
- 学生分配视图：以科目为维度，拖拽学生调整班级

#### 学生课表查看 (StudentTimetable)

- **三种视图模式**：
  1. **学生个人视图**：搜索学号/姓名，显示该学生的一周课表
  2. **课程班视图**：选择课程班，显示该班的所有课时安排
  3. **教师视图**：选择教师，显示其所有 ALEVEL 授课安排
  
- **课表单元格显示**：
  - 科目名称 + 课程班代码
  - 授课教师
  - 教室位置
  - 同班学生人数

- **冲突提示**：
  - 红色高亮：学生时间冲突
  - 黄色警告：教师时间冲突
  - 橙色提示：场地容量不足

### 6.3 关键组件设计

```
src/views/alevel/
├── Dashboard.vue                 # ALEVEL 管理首页
├── StudentManagement.vue         # 学生CRUD + 导入
├── SubjectManagement.vue         # ALEVEL 科目CRUD
├── CourseSelection.vue           # 选课界面（学生/管理员双模式）
├── CourseClassManagement.vue     # 课程班管理 + 自动分班
├── AutoSchedule.vue              # ALEVEL 自动排课向导
├── StudentTimetable.vue          # 学生课表查看（三种视图）
└── components/
    ├── StudentSelector.vue       # 学生搜索选择器
    ├── SubjectCard.vue           # ALEVEL 科目卡片
    ├── SelectionBasket.vue       # 已选科目篮
    ├── ClassAllocationPanel.vue  # 分班结果面板
    ├── StudentTimetableGrid.vue  # 学生课表网格
    ├── ConflictHighlighter.vue   # 冲突高亮组件
    └── TeacherWorkloadChart.vue  # 教师负荷图表
```

---

## 七、API 接口设计

### 7.1 学生管理 API

```
GET    /api/v1/students                    学生列表（page, page_size, grade, class_id, search）
GET    /api/v1/students/{id}               学生详情
POST   /api/v1/students                    创建学生（body: StudentCreate）
PUT    /api/v1/students/{id}               更新学生
DELETE /api/v1/students/{id}               删除
POST   /api/v1/students/import             批量导入（multipart/form-data）
GET    /api/v1/students/{id}/selections    学生选课记录
GET    /api/v1/students/{id}/timetable     学生个人课表
```

### 7.2 ALEVEL 科目 API

```
GET    /api/v1/aleve-subjects              科目列表（page, page_size, exam_board, level）
GET    /api/v1/aleve-subjects/{id}         详情
POST   /api/v1/aleve-subjects              创建（body: AleveSubjectCreate）
PUT    /api/v1/aleve-subjects/{id}         更新
DELETE /api/v1/aleve-subjects/{id}         删除
GET    /api/v1/aleve-subjects/{id}/teachers  可教授该科目的教师列表
```

### 7.3 选课 API

```
GET    /api/v1/course-selections           选课列表（student_id, aleve_subject_id, status, academic_year）
POST   /api/v1/course-selections           提交选课（body: CourseSelectionCreate）
PUT    /api/v1/course-selections/{id}      修改选课
POST   /api/v1/course-selections/batch     批量提交
PUT    /api/v1/course-selections/{id}/confirm  管理员确认
PUT    /api/v1/course-selections/{id}/drop     退选
GET    /api/v1/course-selections/stats     选课统计（各科目人数）
```

### 7.4 课程班 API

```
POST   /api/v1/course-classes/allocate     自动分班（body: {academic_year, semester}）
GET    /api/v1/course-classes              课程班列表
GET    /api/v1/course-classes/{id}         详情
PUT    /api/v1/course-classes/{id}         更新（教师、容量等）
POST   /api/v1/course-classes/{id}/members 添加学生
DELETE /api/v1/course-classes/{id}/members/{student_id} 移除学生
GET    /api/v1/course-classes/{id}/timetable 课程班课表
```

### 7.5 ALEVEL 排课 API

```
POST   /api/v1/schedules/generate          触发排课（body: AleveScheduleRequest）
                                      新增参数：type="STUDENT_BASED", academic_year, semester
GET    /api/v1/student-schedules/{schedule_id}  学生课表列表
GET    /api/v1/student-schedules/{schedule_id}/by-student/{student_id}  某学生课表
```

---

## 八、实施路线图

### Phase 1：基础数据层（2-3 周）

1. **数据库迁移**
   - 创建 `students`, `aleve_subjects`, `course_selections`, `course_classes`, `course_class_members`, `student_schedule_items` 表
   - 扩展现有表（`schedules.type`, `teachers.aleve_subjects`）
   
2. **后端基础 API**
   - 学生管理 CRUD
   - ALEVEL 科目管理 CRUD
   
3. **前端基础页面**
   - 学生管理界面
   - ALEVEL 科目管理界面

### Phase 2：选课系统（2-3 周）

1. **后端**
   - 选课提交/修改/退选 API
   - 选课冲突校验（先修要求、科目互斥、数量限制）
   - 选课统计报表
   
2. **前端**
   - 学生选课界面（科目列表 + 选课篮）
   - 管理员选课审核界面
   - 选课数据统计面板

### Phase 3：分班与排课（3-4 周）

1. **后端**
   - 自动分班算法
   - 教师分配算法
   - ALEVEL 排课引擎适配（SessionBuilder 改造）
   - 学生冲突约束实现
   
2. **前端**
   - 课程班管理界面
   - 自动排课向导
   - 学生课表查看（三种视图）

### Phase 4：调课与优化（2 周）

1. **手动调课**：拖拽调课、锁定、交换
2. **冲突检测**：学生冲突、教师冲突、场地冲突可视化
3. **报表导出**：学生个人课表 PDF、教师授课表、教室使用表

### Phase 5：集成测试与上线（2 周）

1. 与现有 K-9 排课系统并行运行测试
2. 性能测试（学生数 > 200，科目 > 20，课程班 > 80）
3. 用户验收测试
4. 正式上线

---

## 九、风险评估与应对

| 风险 | 影响 | 应对措施 |
|------|------|---------|
| 排课引擎性能不足 | 高 | 学生冲突变量数 = 学生数 × 时间槽数，200学生×43槽=8600变量，在 OR-Tools 能力范围内 |
| 学生选课波动大 | 中 | 设计"选课冻结期"，冻结后才生成分班；支持后期微调 |
| 教师ALEVEL资质不足 | 中 | 在教师管理中增加资质标记，分班时自动筛选可用教师 |
| 与现有系统耦合 | 低 | 采用新增模块策略，不影响现有 K-9 排课流程 |
| 数据迁移复杂 | 低 | 新模块独立建表，无需迁移历史数据 |

---

## 十、附录

### 10.1 典型 ALEVEL 科目清单（参考）

| 代码 | 英文名称 | 中文名称 | 常见考试局 | AS/A2 |
|------|---------|---------|-----------|-------|
| MAT | Mathematics | 数学 | CAIE/EDEXCEL | AS+A2 |
| FMA | Further Mathematics | 进阶数学 | CAIE/EDEXCEL | AS+A2 |
| PHY | Physics | 物理 | CAIE/EDEXCEL | AS+A2 |
| CHE | Chemistry | 化学 | CAIE/EDEXCEL | AS+A2 |
| BIO | Biology | 生物 | CAIE/EDEXCEL | AS+A2 |
| ECO | Economics | 经济 | CAIE/EDEXCEL | AS+A2 |
| BUS | Business | 商科 | CAIE/EDEXCEL | AS+A2 |
| PSY | Psychology | 心理 | CAIE | AS+A2 |
| ACC | Accounting | 会计 | CAIE | AS+A2 |
| ART | Art & Design | 艺术 | CAIE | AS+A2 |
| HIS | History | 历史 | CAIE | AS+A2 |
| GEO | Geography | 地理 | CAIE | AS+A2 |
| CSC | Computer Science | 计算机 | CAIE | AS+A2 |
| ELL | English Language | 英语语言 | CAIE | AS+A2 |
| ESL | English as Second Language | 英语二语 | CAIE | AS |

### 10.2 典型选课组合示例

| 学生 | 选课组合 | 发展方向 |
|------|---------|---------|
| A | 数学 + 物理 + 化学 + 进阶数学 | 理工科 |
| B | 数学 + 经济 + 商科 + 英语 | 商科管理 |
| C | 数学 + 生物 + 化学 + 心理 | 医学/生物 |
| D | 艺术 + 数学 + 英语 | 艺术设计 |

### 10.3 数据量预估

| 数据项 | 预估数量 | 说明 |
|--------|---------|------|
| 学生（G10-G11） | 80-120 人 | 每届 40-60 人 |
| ALEVEL 科目 | 15-20 门 | 视学校开设情况而定 |
| 选课记录（每届） | 240-480 条 | 每人 3-4 门 |
| 课程班（每届） | 50-80 个 | 含平行班 |
| 学生课表项 | ~15,000 条 | 200人 × 平均每周 15 节课 |

---

> 文档版本：v1.0 | 生成日期：2026-05-12 | 状态：设计阶段
