全学段统一排课引擎改造 PLAN

当前项目理解

　　现有系统主线是 K-9 行政班/分层排课：后端从 [backend/app/engine/data/loader.py](backend/app/engine/data/loader.py) 加载教师、班级、科目、场地、分层组、教学任务，转换为 [backend/app/engine/data/models.py](backend/app/engine/data/models.py) 的 ScheduleData，再由 [backend/app/engine/solver/cp_solver.py](backend/app/engine/solver/cp_solver.py) 构建 ScheduleSession 并通过 CP-SAT 求解，结果写入 [backend/app/modules/schedules/models.py](backend/app/modules/schedules/models.py) 的 schedule_items。

　　A-Level 目前是另一条轨道：[backend/app/modules/course_classes/models.py](backend/app/modules/course_classes/models.py) 的 CourseClass.schedule_pattern 保存人工设定时间，[backend/app/modules/schedules/router.py](backend/app/modules/schedules/router.py) 的学生课表接口再把行政班 schedule_items 与 A-Level schedule_pattern 叠加展示。它没有进入求解器，也不会参与教师、学生、场地冲突计算。

　　当前时间模型仍以“星期 + 节次”为核心，且多处硬编码：[backend/app/engine/solver/cp_solver.py](backend/app/engine/solver/cp_solver.py) 中 _get_max_period() 写死周五 8 节、G8/G9 周四 10-11 节；[frontend/src/views/TimetableView.vue](frontend/src/views/TimetableView.vue) 写死 1-11 节时间与 G8/G9 选修占位；[frontend/src/views/ExportPage.vue](frontend/src/views/ExportPage.vue) 仍按 8 节导出。这会阻碍小学、中学、G9、A-Level 不同作息的统一协调。

目标架构

　　目标不是简单把 A-Level 塞进现有 1-9 节模型，而是建立真实钟点区间驱动的统一时间轴：每个学段可以有自己的作息表和显示节次，但求解器判断教师冲突、学生冲突、场地冲突时统一使用真实时间区间重叠关系。

flowchart TD
  StageCalendars[学段作息配置] --> TimeAxis[真实钟点时间轴]
  HomeroomTasks[行政班教学任务] --> UnifiedSessionBuilder[统一会话构建器]
  LayerGroups[跨年级分层组] --> UnifiedSessionBuilder
  G9Electives[G9走班课程] --> UnifiedSessionBuilder
  ALevelCourseClasses[A-Level课程班] --> UnifiedSessionBuilder
  TimeAxis --> UnifiedSessionBuilder
  UnifiedSessionBuilder --> CPSolver[CP-SAT统一求解]
  CPSolver --> ScheduleRecords[统一排课结果]
  ScheduleRecords --> Views[班级/教师/学生/场地课表]

分阶段实施

阶段 1：建立学段作息与真实时间轴

　　新增或扩展“作息日历/时间槽”模型，覆盖至少四类阶段：G1-G5 小学、G6-G8 跨年级分层、G9 过渡走班、G10-G12 A-Level。每个时间槽应包含 stage、适用年级、星期、显示节次、开始时间、结束时间、是否可排课、是否午休/晚课/选修池等元数据。

　　后端先引入纯内部模型与配置加载能力，不急于一次完成所有 UI。重点替换 [backend/app/engine/solver/cp_solver.py](backend/app/engine/solver/cp_solver.py) 里的 _get_max_period() 和 range(1, 6) / 节次硬编码，让求解器从 TimeSlotCatalog 获取候选槽位。

　　前端同步把 [frontend/src/views/TimetableView.vue](frontend/src/views/TimetableView.vue) 中硬编码 periods 与 ELECTIVE_CONFIG 抽象成由后端返回的学段课表结构，先保证展示不再假设所有年级共用同一张 1-11 节表。

        真实时间槽我会后续提供给，现在先按照课程节数安排来做好基础工作。





阶段 2：统一排课会话抽象

　　在 [backend/app/engine/data/models.py](backend/app/engine/data/models.py) 扩展 ScheduleSession / ScheduleRecord 的领域表达：支持 source_type（行政班、分层、课程班、走班）、participant_class_ids、participant_student_ids、teacher_ids、course_class_id、stage、allowed_slot_ids。

　　保留现有行政班任务入口，同时新增 CourseClass 加载路径，让 [backend/app/engine/data/loader.py](backend/app/engine/data/loader.py) 能读取 [backend/app/modules/course_classes/models.py](backend/app/modules/course_classes/models.py)、[backend/app/modules/course_selections/models.py](backend/app/modules/course_selections/models.py)、[backend/app/modules/students/models.py](backend/app/modules/students/models.py) 并构建课程班排课会话。

　　G6-G8 分层继续利用现有 [backend/app/modules/layers/models.py](backend/app/modules/layers/models.py)，但要明确它是“跨年级同步会话”；G9 需要补一个“过渡走班/选修课程班”的数据入口，避免继续用前端占位方式表达。

阶段 3：统一冲突与约束

　　教师冲突从“同 day-period 最多一节”改为“真实钟点区间不可重叠，可配置最小换场间隔”。这正对应你的选择：跨学段不再按节次编号判断，而按实际钟点时间判断。

　　班级冲突、学生冲突、场地冲突分层处理：行政班课程检查 class_ids，A-Level/走班课程检查 student_ids，所有课程共同检查 teacher_ids 与场地容量。对 G9 半行政班半走班，允许同一学生在某些时段跟行政班，在另一些时段跟课程班。

　　软约束继续复用现有框架，但扩展评分：跨学段教师空窗、换场时间、主科时段偏好、A-Level 连堂、课程分散、学生日负荷均衡。

阶段 4：统一结果存储与课表查询

　　优先方案是扩展 [backend/app/modules/schedules/models.py](backend/app/modules/schedules/models.py) 的 ScheduleItem，使其能记录 source_type、course_class_id、duration、slot_id，并保留行政班字段以兼容旧页面。若数据库迁移风险较高，可先新增独立 course_schedule_items，再逐步合并查询层。

　　重写 [backend/app/modules/schedules/router.py](backend/app/modules/schedules/router.py) 的学生课表逻辑：不再从 CourseClass.schedule_pattern 临时拼接，而从统一排课结果查询。班级、教师、学生、场地视图共享同一结果来源。

阶段 5：前端配置与诊断能力

　　新增“学段作息配置/时间轴诊断”入口，至少能查看各年级在一周内有哪些真实时间槽、哪些学段时间重叠、哪些教师跨学段存在冲突风险。

　　自动排课页面 [frontend/src/views/AutoSchedule.vue](frontend/src/views/AutoSchedule.vue) 增加排课对象选择：全校统一排、仅某学段、仅行政班、仅走班/A-Level、或保留已锁定课程后重排。

　　课表页面 [frontend/src/views/TimetableView.vue](frontend/src/views/TimetableView.vue) 支持按学段作息渲染不同行高/时间标签，并能显示统一约束诊断。

风险与控制

　　最大风险是一次性把所有课程类型纳入求解导致无解或性能急剧下降。因此实施时应先完成时间轴与冲突检测，再逐步接入课程类型：行政班/分层保持可运行，随后接 G9 课程班，最后接 G10-G12 A-Level。

　　数据库迁移应保持向后兼容：schedule_pattern 可以短期保留为人工排课草稿或导入字段，但统一排课结果不应再依赖它作为最终课表来源。

验收标准





系统可以配置小学、G6-G8、G9、G10-G12 不同作息，并用真实钟点判断跨学段教师冲突。



行政班、分层组、G9 走班、A-Level 课程班都能被表示为统一排课会话。



教师在不同学段任课时，不会因节次编号不同而漏判时间冲突。



学生个人课表不再依赖展示层临时叠加，而来自统一排课结果。



前端班级、教师、学生、场地视图读取同一套排课结果，并能显示冲突诊断。

