<template>
  <div class="timetable-view">
    <!-- 课表选择器 -->
    <div class="schedule-selector-bar card">
      <div class="selector-left">
        <el-icon><Calendar /></el-icon>
        <span class="selector-label">当前课表:</span>
        <el-select
          v-model="currentScheduleId"
          placeholder="选择课表"
          style="width: 220px"
          @change="onScheduleChange"
        >
          <el-option
            v-for="s in scheduleList"
            :key="s.id"
            :label="s.name + (s.is_active ? ' (使用中)' : '')"
            :value="s.id"
          >
            <span>{{ s.name }}</span>
            <el-tag v-if="s.is_active" type="success" size="small" style="margin-left: 8px">使用中</el-tag>
            <span class="schedule-score" v-if="s.score">评分 {{ s.score }}</span>
          </el-option>
        </el-select>
        <span v-if="currentSchedule" class="schedule-meta">
          {{ formatDate(currentSchedule.created_at) }}
        </span>
      </div>
      <div class="selector-right">
        <el-button
          v-if="currentSchedule && !currentSchedule.is_active"
          type="primary"
          size="small"
          @click="activateCurrentSchedule"
        >
          <el-icon><Check /></el-icon>设为使用
        </el-button>
        <el-button
          v-if="scheduleList.length > 1 && currentScheduleId"
          type="danger"
          plain
          size="small"
          @click="confirmDeleteSchedule(currentScheduleId)"
        >
          <el-icon><Delete /></el-icon>删除此课表
        </el-button>
      </div>
    </div>

    <div class="page-header">
      <div class="page-title">
        <h1>{{ pageTitle }}</h1>
        <span class="subtitle">{{ pageSubtitle }}</span>
      </div>
      <div class="header-actions">
        <el-button @click="printSchedule"><el-icon><Printer /></el-icon>打印</el-button>
        <el-button type="primary" @click="$router.push('/export')"><el-icon><Download /></el-icon>导出</el-button>
      </div>
    </div>

    <!-- 视图切换和筛选 -->
    <div class="view-controls card">
      <div class="view-tabs">
        <div 
          v-for="view in viewTypes" 
          :key="view.key"
          class="view-tab"
          :class="{ active: currentView === view.key }"
          @click="currentView = view.key"
        >
          <el-icon><component :is="view.icon" /></el-icon>
          <span>{{ view.label }}</span>
        </div>
      </div>
      <div class="view-filters">
        <el-select v-model="selectedTarget" :placeholder="filterPlaceholder" style="width: 200px">
          <el-option v-for="opt in filterOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
        </el-select>
        <el-button-group>
          <el-button :icon="ArrowLeft" @click="prevTarget" />
          <el-button :icon="ArrowRight" @click="nextTarget" />
        </el-button-group>
      </div>
    </div>

    <!-- 约束摘要条（仅班级视图） -->
    <div v-if="currentView === 'class' && validationSummary && (validationSummary.hard_count || validationSummary.soft_count)" class="validation-bar card">
      <span v-if="validationSummary.hard_count" class="vb-hard">
        <el-icon><CircleClose /></el-icon> 硬约束违反 {{ validationSummary.hard_count }} 处
      </span>
      <span v-if="validationSummary.soft_count" class="vb-soft">
        <el-icon><Warning /></el-icon> 软约束提醒 {{ validationSummary.soft_count }} 处
      </span>
      <span class="vb-score">综合评分: {{ validationSummary.score }}/100</span>
    </div>
    
    <!-- 教研组组会信息（教师视图） -->
    <div v-if="currentView === 'teacher' && meetingInfo" class="meeting-info-bar card">
      <el-icon><InfoFilled /></el-icon>
      <span>所属教研组：<b>{{ meetingInfo.group_name }}</b></span>
      <el-divider direction="vertical" />
      <span>组会时间：<b>{{ ['', '周一','周二','周三','周四','周五'][meetingInfo.day] }} 第{{ meetingInfo.periods[0] }}-{{ meetingInfo.periods[1] }}节</b></span>
    </div>

    <!-- 课表展示 -->
    <div class="timetable-wrapper card">
      <div class="timetable">
        <div class="timetable-header">
          <div class="time-column header-cell">时间</div>
          <div class="day-column header-cell" v-for="day in weekDays" :key="day">{{ day }}</div>
        </div>
        
        <div class="timetable-body">
          <template v-for="(period, idx) in periods" :key="idx">
            <!-- 上午下午分隔 -->
            <div v-if="period.isBreak" class="break-row">
              <div class="break-content">{{ period.label }}</div>
            </div>
            
            <!-- 课程行 -->
            <div v-else class="period-row" :class="{ 'elective-row': period.isElective }">
              <div class="time-column">
                <div class="period-num">第{{ period.num }}节</div>
                <div class="period-time">{{ period.time }}</div>
                <div v-if="period.isElective" class="elective-label">选修</div>
              </div>
              <div 
                class="day-column"
                v-for="day in 5" 
                :key="day"
                :class="{ 
                  'friday-hidden': day === 5 && period.num > 8 && currentView !== 'student',
                  'elective-placeholder': isElectivePlaceholder(period.num, day),
                  'elective-available': period.isElective && !isElectivePlaceholder(period.num, day) && currentView !== 'student'
                }"
                @click="currentView === 'class' && !isElectivePlaceholder(period.num, day) && handleCellClick(period.num, day)"
                @dragover.prevent
                @drop="currentView === 'class' && !isElectivePlaceholder(period.num, day) && handleDrop(period.num, day, $event)"
              >
                <!-- 选修课占位显示 -->
                <div v-if="isElectivePlaceholder(period.num, day)" class="elective-slot">
                  <span class="elective-text">选修课</span>
                </div>
                <!-- 有课程时显示 -->
                <el-tooltip 
                  v-else-if="getScheduleCell(period.num, day)"
                  :content="buildTooltip(period.num, day)" 
                  placement="top"
                  raw-content
                  :disabled="!hasAnyInfo(period.num, day)"
                >
                  <div 
                    class="schedule-cell"
                    :class="[
                      currentView === 'class' ? getCellViolationClass(period.num, day) : '',
                      currentView !== 'class' ? 'readonly-cell' : ''
                    ]"
                    :style="getCellStyle(getScheduleCell(period.num, day))"
                    :draggable="currentView === 'class'"
                    @dragstart="currentView === 'class' && handleDragStart(period.num, day, $event)"
                  >
                    <div class="subject-name">{{ getScheduleCell(period.num, day)?.subject }}</div>
                    <div class="teacher-name">{{ getScheduleCell(period.num, day)?.teacher }}</div>
                    <!-- 锁定图标 -->
                    <div v-if="getScheduleCell(period.num, day)?.isLocked" class="lock-badge" title="已锁定">
                      <el-icon :size="12"><Lock /></el-icon>
                    </div>
                    <!-- 连堂标记 -->
                    <div v-if="getScheduleCell(period.num, day)?.isContinuous" class="continuous-badge">
                      连堂
                    </div>
                    <!-- 违反角标（仅班级视图） -->
                    <div v-if="currentView === 'class' && getViolations(period.num, day).length"
                         class="violation-badge"
                         :class="getViolationSeverity(period.num, day)">
                      {{ getViolations(period.num, day).length }}
                    </div>
                  </div>
                </el-tooltip>
                <!-- 组会时段标记（教师视图，空单元格） -->
                <div v-else-if="currentView === 'teacher' && isMeetingSlot(day, period.num)"
                     class="meeting-slot">
                  <el-icon :size="14"><Calendar /></el-icon>
                  <span>组会</span>
                </div>
              </div>
            </div>
          </template>
        </div>
      </div>
    </div>
    
    <!-- 操作提示 -->
    <div class="operation-hint">
      <el-icon><InfoFilled /></el-icon>
      <span v-if="currentView === 'class'">提示：点击课程可查看详情/锁定/调换。拖拽课程可快速调换位置。红框=硬约束违反，橙框=软约束提醒。</span>
      <span v-else-if="currentView === 'student'">提示：当前为学生个人课表视图，展示行政班课程与 A-Level 选修课程。</span>
      <span v-else>提示：当前为{{ currentView === 'teacher' ? '教师' : '教室' }}视图，仅供查看。课程调换请切换到班级视图。</span>
    </div>
    
    <!-- 课程详情对话框 -->
    <el-dialog v-model="showCellDetail" title="课程详情" width="420px">
      <div class="cell-detail" v-if="selectedCell">
        <div class="detail-row">
          <span class="label">科目:</span>
          <span class="value">{{ selectedCell.subject }}</span>
        </div>
        <div class="detail-row">
          <span class="label">教师:</span>
          <span class="value">{{ selectedCell.teacher }}</span>
        </div>
        <div class="detail-row">
          <span class="label">时间:</span>
          <span class="value">周{{ ['一','二','三','四','五'][selectedCell.day-1] }} 第{{ selectedCell.period }}节</span>
        </div>
        <div class="detail-row">
          <span class="label">状态:</span>
          <span class="value">
            <el-tag v-if="selectedCell.isLocked" type="warning" size="small">已锁定</el-tag>
            <el-tag v-else type="success" size="small">未锁定</el-tag>
          </span>
        </div>
        <!-- 该位置的约束违反信息（仅班级视图） -->
        <div v-if="currentView === 'class' && getViolations(selectedCell.period, selectedCell.day).length" class="detail-violations">
          <div class="detail-row" style="border-bottom:none; padding-bottom:4px">
            <span class="label">约束检测:</span>
          </div>
          <div v-for="(v, i) in getViolations(selectedCell.period, selectedCell.day)" :key="i"
               class="violation-item" :class="v.severity">
            <el-icon v-if="v.severity === 'hard'"><CircleClose /></el-icon>
            <el-icon v-else><Warning /></el-icon>
            <span>{{ v.message }}</span>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="showCellDetail = false">关闭</el-button>
        <el-button
          :type="selectedCell?.isLocked ? 'info' : 'warning'"
          @click="toggleLock"
        >
          <el-icon><Lock /></el-icon>
          {{ selectedCell?.isLocked ? '解除锁定' : '锁定位置' }}
        </el-button>
        <el-button type="primary" @click="openSwapGrid">
          <el-icon><Switch /></el-icon>调换位置
        </el-button>
      </template>
    </el-dialog>
    
    <!-- 调换对话框 — 网格视图 -->
    <el-dialog v-model="showSwapDialog" title="选择调换目标" width="860px" @open="loadSwapCandidates">
      <div v-loading="swapLoading" class="swap-grid-wrapper">
        <div class="swap-source-info">
          当前选中：<strong>{{ selectedCell?.subject }}</strong>
          （{{ selectedCell?.teacher }}，
          周{{ ['一','二','三','四','五'][(selectedCell?.day || 1) - 1] }}第{{ selectedCell?.period }}节）
        </div>
        <div class="swap-legend">
          <span class="legend-item lg-available">可用</span>
          <span class="legend-item lg-soft-risk">有软约束风险</span>
          <span class="legend-item lg-conflict">不可用</span>
          <span class="legend-item lg-occupied">已占用(可交换)</span>
          <span class="legend-item lg-locked">已锁定</span>
          <span class="legend-item lg-self">当前位置</span>
        </div>
        <div class="swap-grid">
          <div class="sg-header">
            <div class="sg-time-col"></div>
            <div class="sg-day-col" v-for="d in 5" :key="d">周{{ ['一','二','三','四','五'][d-1] }}</div>
          </div>
          <template v-for="p in 11" :key="p">
            <div v-if="p === 6" class="sg-break">午休</div>
            <div class="sg-row">
              <div class="sg-time-col">第{{ p }}节</div>
              <div
                v-for="d in 5" :key="d"
                class="sg-cell"
                :class="getSwapCellClass(d, p)"
                @click="onSwapCellClick(d, p)"
              >
                <el-tooltip :content="getSwapTooltip(d, p)" placement="top" :disabled="!getSwapTooltip(d, p)">
                  <div class="sg-cell-inner">
                    <template v-if="swapCandidates[`${d}-${p}`]?.status === 'self'">
                      <span class="sg-self-mark">当前</span>
                    </template>
                    <template v-else-if="swapCandidates[`${d}-${p}`]?.current_subject">
                      <div class="sg-subj">{{ swapCandidates[`${d}-${p}`].current_subject }}</div>
                      <div class="sg-teacher">{{ swapCandidates[`${d}-${p}`].current_teacher }}</div>
                    </template>
                    <template v-else>
                      <span class="sg-empty">空</span>
                    </template>
                  </div>
                </el-tooltip>
              </div>
            </div>
          </template>
        </div>
      </div>
      <template #footer>
        <el-button @click="showSwapDialog = false">取消</el-button>
        <el-button
          type="primary"
          @click="confirmSwapFromGrid"
          :disabled="!selectedSwapTarget"
        >
          确认调换到 {{ selectedSwapTarget ? `周${['一','二','三','四','五'][selectedSwapTarget.day-1]}第${selectedSwapTarget.period}节` : '...' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  Printer, Download, Delete, ArrowLeft, ArrowRight, InfoFilled, Lock, Switch,
  OfficeBuilding, User, UserFilled, Calendar, Warning, CircleClose, Check
} from '@element-plus/icons-vue'
import {
  getScheduleList, getClassTimetable,
  getTeacherTimetable, getVenueTimetable, getStudentTimetable,
  swapScheduleItems, toggleLockItem, getSwapCandidates,
  validateSchedule, deleteSchedule, activateSchedule,
} from '@/api/schedules'
import { getTeachers } from '@/api/teachers'
import { getClasses } from '@/api/classes'
import { getVenues } from '@/api/venues'
import { getStudents } from '@/api/students'

const route = useRoute()
const router = useRouter()

// ========== 基础状态 ==========
const loading = ref(false)
const hasSchedule = ref(false)
const currentScheduleId = ref(null)
const scheduleList = ref([])

const viewTypes = [
  { key: 'class', label: '班级视图', icon: 'OfficeBuilding' },
  { key: 'teacher', label: '教师视图', icon: 'User' },
  { key: 'student', label: '学生视图', icon: 'UserFilled' },
  { key: 'room', label: '教室视图', icon: 'Calendar' }
]
const currentView = ref('class')

const selectedTarget = ref(null)
const teacherList = ref([])
const classList = ref([])
const venueList = ref([])
const studentList = ref([])

const currentSchedule = computed(() =>
  scheduleList.value.find(s => s.id === currentScheduleId.value) || null
)

const pageTitle = computed(() => {
  if (currentView.value === 'student' && selectedTarget.value) {
    const s = studentList.value.find(st => st.id === selectedTarget.value)
    return s ? `${s.name} 的个人课表` : '学生课表'
  }
  if (currentView.value === 'teacher' && selectedTarget.value) {
    const t = teacherList.value.find(te => te.id === selectedTarget.value)
    return t ? `${t.name} 的教师课表` : '教师课表'
  }
  if (currentView.value === 'class' && selectedTarget.value) {
    const c = classList.value.find(cl => cl.id === selectedTarget.value)
    return c ? `${c.name} 班级课表` : '班级课表'
  }
  return '课表管理'
})

const pageSubtitle = computed(() => {
  if (currentView.value === 'student' && selectedTarget.value) {
    const s = studentList.value.find(st => st.id === selectedTarget.value)
    return s ? `学号: ${s.student_no || '-'} | 年级: ${s.grade || '-'}` : '查看学生个人课表'
  }
  return '查看和调整课程表'
})

const filterPlaceholder = computed(() => {
  const placeholders = { class: '选择班级', teacher: '选择教师', student: '选择学生', room: '选择教室' }
  return placeholders[currentView.value]
})

const filterOptions = computed(() => {
  if (currentView.value === 'class') {
    return classList.value.map(c => ({ value: c.id, label: c.name }))
  } else if (currentView.value === 'teacher') {
    return teacherList.value.map(t => ({ value: t.id, label: t.name }))
  } else if (currentView.value === 'student') {
    return studentList.value.map(s => ({ value: s.id, label: `${s.name} (${s.student_no || s.grade || ''})` }))
  } else if (currentView.value === 'room') {
    return venueList.value.map(v => ({ value: v.id, label: v.name }))
  }
  return []
})

const weekDays = ['周一', '周二', '周三', '周四', '周五']

const periods = [
  { num: 1, time: '08:00-08:45' },
  { num: 2, time: '08:55-09:40' },
  { num: 3, time: '10:00-10:45' },
  { num: 4, time: '10:55-11:40' },
  { num: 5, time: '11:50-12:35' },
  { isBreak: true, label: '午 休' },
  { num: 6, time: '14:00-14:45' },
  { num: 7, time: '14:55-15:40' },
  { num: 8, time: '16:00-16:45' },
  { num: 9, time: '16:55-17:40' },
  { num: 10, time: '17:50-18:35', isElective: true },
  { num: 11, time: '18:45-19:30', isElective: true }
]

const ELECTIVE_CONFIG = {
  periods: [10, 11], day: 4, grades: ['G8', 'G9']
}

const currentGrade = computed(() => {
  if (currentView.value !== 'class' || !selectedTarget.value) return null
  const cls = classList.value.find(c => c.id === selectedTarget.value)
  return cls?.grade || null
})

const isElectivePlaceholder = (period, day) => {
  if (!ELECTIVE_CONFIG.periods.includes(period)) return false
  // 学生视图直接显示合并后的课表，不需要占位符
  if (currentView.value === 'student') return false
  if (day === 5) return true
  if (day === ELECTIVE_CONFIG.day && ELECTIVE_CONFIG.grades.includes(currentGrade.value)) return false
  return true
}

// ========== 课表数据 ==========
const timetableData = ref({})
const violations = ref({})
const validationSummary = ref(null)
const meetingInfo = ref(null)

const getScheduleCell = (period, day) => timetableData.value[`${day}-${period}`]

const isMeetingSlot = (day, period) => {
  if (!meetingInfo.value) return false
  return meetingInfo.value.day === day && meetingInfo.value.periods.includes(period)
}

/**
 * 根据科目 hex 颜色生成内联样式
 */
const getCellStyle = (cell) => {
  if (!cell || !cell.color || cell.color === '#ccc') {
    return { background: '#f8fafc', border: '1px solid #e2e8f0', color: '#64748b' }
  }
  const hex = cell.color.replace('#', '')
  const r = parseInt(hex.substring(0, 2), 16)
  const g = parseInt(hex.substring(2, 4), 16)
  const b = parseInt(hex.substring(4, 6), 16)
  return {
    background: `rgba(${r},${g},${b},0.10)`,
    border: `1px solid rgba(${r},${g},${b},0.35)`,
    color: `rgb(${Math.max(0, r - 70)},${Math.max(0, g - 70)},${Math.max(0, b - 70)})`
  }
}

// ========== 约束违反相关 ==========
const getViolations = (period, day) => violations.value[`${day}-${period}`] || []

const hasHardViolation = (period, day) =>
  getViolations(period, day).some(v => v.severity === 'hard')

const hasSoftViolation = (period, day) =>
  getViolations(period, day).some(v => v.severity === 'soft')

const getCellViolationClass = (period, day) => {
  if (hasHardViolation(period, day)) return 'violation-hard'
  if (hasSoftViolation(period, day)) return 'violation-soft'
  return ''
}

const getViolationSeverity = (period, day) => {
  if (hasHardViolation(period, day)) return 'hard'
  return 'soft'
}

const hasAnyInfo = (period, day) => {
  const cell = getScheduleCell(period, day)
  return (cell?.note) || getViolations(period, day).length > 0
}

const buildTooltip = (period, day) => {
  const parts = []
  const cell = getScheduleCell(period, day)
  if (cell?.note) parts.push(cell.note)
  for (const v of getViolations(period, day)) {
    const icon = v.severity === 'hard' ? '⛔' : '⚠️'
    parts.push(`${icon} ${v.message}`)
  }
  return parts.join('<br/>')
}

// ========== 对话框状态 ==========
const showCellDetail = ref(false)
const showSwapDialog = ref(false)
const selectedCell = ref(null)
const selectedSwapTarget = ref(null)
const swapCandidates = ref({})
const swapLoading = ref(false)

// ========== API 调用 ==========

const loadScheduleList = async (autoSelect = true) => {
  try {
    const res = await getScheduleList()
    scheduleList.value = res.data.items || []
    if (autoSelect) {
      const urlScheduleId = route.query.schedule_id
      if (urlScheduleId) {
        currentScheduleId.value = parseInt(urlScheduleId)
      } else if (scheduleList.value.length > 0) {
        currentScheduleId.value = scheduleList.value[0].id
      }
    }
    hasSchedule.value = scheduleList.value.length > 0
  } catch (error) {
    console.error('加载课表列表失败:', error)
    ElMessage.error('加载课表列表失败')
  }
}

const loadBasicData = async () => {
  try {
    const [teachersRes, classesRes, venuesRes] = await Promise.all([
      getTeachers({ page_size: 500 }),
      getClasses({ page_size: 500 }),
      getVenues({ page_size: 100 })
    ])
    teacherList.value = teachersRes.data.items || []
    classList.value = classesRes.data.items || []
    venueList.value = venuesRes.data.items || []
    classList.value.sort((a, b) => {
      const gradeOrder = ['PK','KG','G1','G2','G3','G4','G5','G6','G7','G8','G9','G10','G11','G12']
      const aIdx = gradeOrder.indexOf(a.grade)
      const bIdx = gradeOrder.indexOf(b.grade)
      if (aIdx !== bIdx) return aIdx - bIdx
      return a.class_no - b.class_no
    })
    if (currentView.value === 'class' && classList.value.length > 0) {
      selectedTarget.value = classList.value[0].id
    } else if (currentView.value === 'teacher' && teacherList.value.length > 0) {
      selectedTarget.value = teacherList.value[0].id
    } else if (currentView.value === 'room' && venueList.value.length > 0) {
      selectedTarget.value = venueList.value[0].id
    }
  } catch (error) {
    console.error('加载基础数据失败:', error)
  }
}

const loadStudents = async () => {
  try {
    const res = await getStudents({ page: 1, page_size: 500 })
    studentList.value = (res.data?.items || []).map(s => ({
      ...s,
      studentNo: s.student_no,
      classId: s.class_id,
    }))
    if (currentView.value === 'student' && studentList.value.length > 0) {
      selectedTarget.value = studentList.value[0].id
    }
  } catch (error) {
    console.error('加载学生数据失败:', error)
    studentList.value = []
  }
}

const loadTimetable = async () => {
  if (!currentScheduleId.value || !selectedTarget.value) {
    timetableData.value = {}
    violations.value = {}
    validationSummary.value = null
    return
  }
  loading.value = true
  try {
    let res
    if (currentView.value === 'class') {
      res = await getClassTimetable(currentScheduleId.value, selectedTarget.value)
    } else if (currentView.value === 'teacher') {
      res = await getTeacherTimetable(currentScheduleId.value, selectedTarget.value)
    } else if (currentView.value === 'student') {
      res = await getStudentTimetable(currentScheduleId.value, selectedTarget.value)
    } else if (currentView.value === 'room') {
      res = await getVenueTimetable(currentScheduleId.value, selectedTarget.value)
    }
    if (res && res.data && res.data.timetable) {
      timetableData.value = {}
      if (currentView.value === 'room') {
        for (const [key, items] of Object.entries(res.data.timetable)) {
          if (Array.isArray(items) && items.length > 0) {
            const first = items[0]
            timetableData.value[key] = {
              itemId: null,
              subject: first.subject_name,
              teacher: items.length > 1
                ? `${first.class_name} 等${items.length}班`
                : first.class_name,
              color: first.subject_color,
              count: items.length,
              allClasses: items.map(i => i.class_name).join('、'),
              note: '',
              isLocked: false,
            }
          }
        }
      } else {
        for (const [key, value] of Object.entries(res.data.timetable)) {
          timetableData.value[key] = {
            itemId: value.item_id,
            subject: value.subject_name,
            teacher: currentView.value === 'class' ? value.teacher_name : (value.class_name || value.teacher_name),
            color: value.subject_color,
            note: value.note || '',
            isLocked: value.is_locked || false,
          }
        }
      }
    } else {
      timetableData.value = {}
    }
    // 教师视图：读取组会信息
    if (currentView.value === 'teacher' && res?.data?.meeting_info) {
      meetingInfo.value = res.data.meeting_info
    } else {
      meetingInfo.value = null
    }
    // 加载约束验证
    await loadValidation()
  } catch (error) {
    console.error('加载课表详情失败:', error)
    timetableData.value = {}
  } finally {
    loading.value = false
  }
}

const loadValidation = async () => {
  // 仅班级视图加载约束验证，教师/教室视图不需要冲突检测
  if (!currentScheduleId.value || currentView.value !== 'class') {
    violations.value = {}
    validationSummary.value = null
    return
  }
  try {
    const res = await validateSchedule(currentScheduleId.value, selectedTarget.value)
    violations.value = res.data.violations || {}
    validationSummary.value = res.data.summary || null
  } catch (error) {
    console.error('约束验证失败:', error)
    violations.value = {}
    validationSummary.value = null
  }
}

// ========== 监听 ==========
watch(currentView, () => {
  if (currentView.value === 'class' && classList.value.length > 0) {
    selectedTarget.value = classList.value[0].id
  } else if (currentView.value === 'teacher' && teacherList.value.length > 0) {
    selectedTarget.value = teacherList.value[0].id
  } else if (currentView.value === 'student' && studentList.value.length > 0) {
    selectedTarget.value = studentList.value[0].id
  } else if (currentView.value === 'room' && venueList.value.length > 0) {
    selectedTarget.value = venueList.value[0].id
  } else {
    selectedTarget.value = null
    timetableData.value = {}
    violations.value = {}
  }
})

watch(selectedTarget, () => { if (selectedTarget.value) loadTimetable() })
watch(currentScheduleId, () => {
  if (currentScheduleId.value && selectedTarget.value) loadTimetable()
})

onMounted(async () => {
  await loadScheduleList()
  await loadBasicData()
  await loadStudents()
  const urlClassId = route.query.class_id
  if (urlClassId) {
    currentView.value = 'class'
    selectedTarget.value = parseInt(urlClassId)
  }
  if (currentScheduleId.value && selectedTarget.value) {
    await loadTimetable()
  }
})

// ========== 交互 ==========

const handleCellClick = (period, day) => {
  const cell = getScheduleCell(period, day)
  if (cell) {
    selectedCell.value = { ...cell, period, day }
    showCellDetail.value = true
  }
}

// --- 锁定 ---
const toggleLock = async () => {
  if (!selectedCell.value?.itemId || !currentScheduleId.value) {
    ElMessage.warning('无法操作此课程')
    return
  }
  const newLocked = !selectedCell.value.isLocked
  try {
    await toggleLockItem(currentScheduleId.value, selectedCell.value.itemId, newLocked)
    ElMessage.success(newLocked ? '课程已锁定' : '课程已解锁')
    selectedCell.value.isLocked = newLocked
    // 更新 timetableData 中的锁定状态
    const key = `${selectedCell.value.day}-${selectedCell.value.period}`
    if (timetableData.value[key]) {
      timetableData.value[key].isLocked = newLocked
    }
  } catch (error) {
    ElMessage.error('操作失败: ' + (error.response?.data?.detail || error.message))
  }
}

// --- 拖拽调换 ---
const dragSource = ref(null)

const handleDragStart = (period, day, event) => {
  dragSource.value = { period, day }
  event.dataTransfer.setData('text/plain', JSON.stringify({ period, day }))
}

const handleDrop = async (targetPeriod, targetDay, event) => {
  const data = JSON.parse(event.dataTransfer.getData('text/plain'))
  if (data.period === targetPeriod && data.day === targetDay) return
  if (currentView.value !== 'class' || !selectedTarget.value || !currentScheduleId.value) {
    ElMessage.warning('请在班级视图下进行课程调换')
    return
  }
  try {
    const res = await swapScheduleItems(currentScheduleId.value, {
      item1_day: data.day, item1_period: data.period,
      item1_class_id: selectedTarget.value,
      item2_day: targetDay, item2_period: targetPeriod,
      item2_class_id: selectedTarget.value
    })
    if (res.code === 200) {
      ElMessage.success('课程调换成功')
      await loadTimetable()
    }
  } catch (error) {
    if (error.message === 'Network Error' || !error.response) {
      ElMessage.error('网络连接失败，请检查后端服务是否启动')
    } else if (error.response?.status >= 400 && error.response?.status < 500) {
      ElMessage.warning(error.response?.data?.detail || '调换失败：存在排课冲突')
    } else {
      ElMessage.error('服务器错误: ' + (error.response?.data?.detail || error.message))
    }
  }
  dragSource.value = null
}

// --- 调换网格 ---

const openSwapGrid = () => {
  selectedSwapTarget.value = null
  swapCandidates.value = {}
  showSwapDialog.value = true
}

const loadSwapCandidates = async () => {
  if (!selectedCell.value || !currentScheduleId.value || !selectedTarget.value) return
  swapLoading.value = true
  try {
    const res = await getSwapCandidates(currentScheduleId.value, {
      day: selectedCell.value.day,
      period: selectedCell.value.period,
      class_id: selectedTarget.value,
    })
    swapCandidates.value = res.data.candidates || {}
  } catch (error) {
    console.error('加载候选位置失败:', error)
    ElMessage.error('加载候选位置失败')
  } finally {
    swapLoading.value = false
  }
}

const getSwapCellClass = (day, period) => {
  const c = swapCandidates.value[`${day}-${period}`]
  if (!c) return 'sg-unknown'
  const isSelected = selectedSwapTarget.value?.day === day && selectedSwapTarget.value?.period === period
  return {
    'sg-self': c.status === 'self',
    'sg-available': c.status === 'available',
    'sg-soft-risk': c.status === 'soft_risk',
    'sg-conflict': c.status === 'conflict',
    'sg-locked': c.status === 'locked',
    'sg-occupied': !['self','available','soft_risk','conflict','locked'].includes(c.status),
    'sg-selected': isSelected,
  }
}

const getSwapTooltip = (day, period) => {
  const c = swapCandidates.value[`${day}-${period}`]
  if (!c) return ''
  const parts = []
  if (c.conflicts?.length) parts.push(...c.conflicts.map(x => `⛔ ${x}`))
  if (c.warnings?.length) parts.push(...c.warnings.map(x => `⚠️ ${x}`))
  if (!parts.length && c.status === 'available') parts.push('✅ 无冲突，可安全调换')
  return parts.join('\n')
}

const onSwapCellClick = (day, period) => {
  const c = swapCandidates.value[`${day}-${period}`]
  if (!c || c.status === 'self') return
  selectedSwapTarget.value = { day, period }
}

const confirmSwapFromGrid = async () => {
  if (!selectedSwapTarget.value || !selectedCell.value) return
  if (!currentScheduleId.value || !selectedTarget.value) return
  try {
    const res = await swapScheduleItems(currentScheduleId.value, {
      item1_day: selectedCell.value.day,
      item1_period: selectedCell.value.period,
      item1_class_id: selectedTarget.value,
      item2_day: selectedSwapTarget.value.day,
      item2_period: selectedSwapTarget.value.period,
      item2_class_id: selectedTarget.value
    })
    if (res.code === 200) {
      ElMessage.success('课程调换成功')
      showSwapDialog.value = false
      showCellDetail.value = false
      selectedSwapTarget.value = null
      await loadTimetable()
    }
  } catch (error) {
    if (error.response?.status >= 400 && error.response?.status < 500) {
      ElMessage.warning(error.response?.data?.detail || '调换失败')
    } else {
      ElMessage.error('服务器错误: ' + (error.response?.data?.detail || error.message))
    }
  }
}

// --- 导航 ---
const prevTarget = () => {
  const idx = filterOptions.value.findIndex(o => o.value === selectedTarget.value)
  if (idx > 0) selectedTarget.value = filterOptions.value[idx - 1].value
}
const nextTarget = () => {
  const idx = filterOptions.value.findIndex(o => o.value === selectedTarget.value)
  if (idx < filterOptions.value.length - 1) selectedTarget.value = filterOptions.value[idx + 1].value
}

const formatDate = (dateStr) => {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return d.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

const onScheduleChange = async (scheduleId) => {
  currentScheduleId.value = scheduleId
  if (selectedTarget.value) {
    await loadTimetable()
  }
}

const activateCurrentSchedule = async () => {
  if (!currentScheduleId.value) return
  try {
    await activateSchedule(currentScheduleId.value)
    ElMessage.success('已设为当前使用课表')
    await loadScheduleList(false)
  } catch (error) {
    ElMessage.error('激活失败')
  }
}

const confirmDeleteSchedule = async (scheduleId) => {
  try {
    await ElMessageBox.confirm(
      '确定要删除此课表吗？此操作不可撤销。',
      '删除课表',
      { confirmButtonText: '确定删除', cancelButtonText: '取消', type: 'warning' }
    )
    await deleteSchedule(scheduleId)
    ElMessage.success('课表已删除')
    currentScheduleId.value = null
    timetableData.value = {}
    await loadScheduleList(false)
    // 自动选择第一个课表
    if (scheduleList.value.length > 0) {
      currentScheduleId.value = scheduleList.value[0].id
      if (selectedTarget.value) await loadTimetable()
    }
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}

const printSchedule = () => {
  const title = pageTitle.value
  const subtitle = pageSubtitle.value
  const printWindow = window.open('', '_blank')
  if (!printWindow) {
    ElMessage.warning('请允许弹窗以使用打印功能')
    return
  }

  // 构建课表HTML
  let html = `
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8">
      <title>${title}</title>
      <style>
        body { font-family: 'Microsoft YaHei', sans-serif; padding: 24px; }
        .print-header { text-align: center; margin-bottom: 20px; }
        .print-header h2 { margin: 0; font-size: 22px; }
        .print-header p { margin: 4px 0 0; color: #666; font-size: 13px; }
        table { width: 100%; border-collapse: collapse; margin-top: 16px; }
        th { background: #1e3a5f; color: #fff; padding: 10px; font-size: 13px; }
        td { border: 1px solid #ddd; padding: 8px; text-align: center; min-height: 60px; vertical-align: middle; }
        .time-col { background: #f8fafc; font-weight: 600; width: 80px; }
        .cell-subject { font-weight: 600; font-size: 13px; }
        .cell-teacher { font-size: 11px; color: #666; margin-top: 3px; }
        .cell-note { font-size: 10px; color: #999; margin-top: 2px; }
        .break-row { background: #fef3c7; text-align: center; font-size: 12px; color: #92400e; }
        .elective-placeholder { background: #f1f5f9; color: #94a3b8; font-size: 12px; }
        .friday-hidden { background: #f1f5f9; }
        @media print { body { padding: 0; } }
      </style>
    </head>
    <body>
      <div class="print-header">
        <h2>${title}</h2>
        <p>${subtitle}</p>
      </div>
      <table>
        <thead>
          <tr>
            <th>时间</th>
            <th>周一</th><th>周二</th><th>周三</th><th>周四</th><th>周五</th>
          </tr>
        </thead>
        <tbody>
  `

  for (const period of periods) {
    if (period.isBreak) {
      html += `<tr><td colspan="6" class="break-row">${period.label}</td></tr>`
      continue
    }
    html += `<tr>`
    html += `<td class="time-col"><div>第${period.num}节</div><div style="font-size:10px;color:#999">${period.time}</div></td>`
    for (let day = 1; day <= 5; day++) {
      if (day === 5 && period.num > 8) {
        html += `<td class="friday-hidden">-</td>`
        continue
      }
      if (isElectivePlaceholder(period.num, day)) {
        html += `<td class="elective-placeholder">选修课</td>`
        continue
      }
      const cell = getScheduleCell(period.num, day)
      if (cell) {
        const style = cell.color && cell.color !== '#ccc'
          ? `style="background:${cell.color}15;border-color:${cell.color}55"`
          : ''
        html += `<td ${style}>
          <div class="cell-subject">${cell.subject || ''}</div>
          <div class="cell-teacher">${cell.teacher || ''}</div>
          ${cell.note ? `<div class="cell-note">${cell.note}</div>` : ''}
        </td>`
      } else {
        html += `<td></td>`
      }
    }
    html += `</tr>`
  }

  html += `
        </tbody>
      </table>
      <div style="margin-top:16px;font-size:11px;color:#999;text-align:center">
        打印时间: ${new Date().toLocaleString('zh-CN')}
      </div>
      <script>window.onload = () => { setTimeout(() => window.print(), 300) }<\/script>
    </body>
    </html>
  `

  printWindow.document.write(html)
  printWindow.document.close()
}


</script>

<style lang="scss" scoped>
.timetable-view { width: 100%; margin: 0 auto; }

.schedule-selector-bar {
  display: flex; justify-content: space-between; align-items: center;
  padding: 12px 20px; margin-bottom: 16px;
  .selector-left {
    display: flex; align-items: center; gap: 10px;
    .selector-label { font-size: 14px; color: var(--text-secondary); font-weight: 500; }
    .schedule-meta { font-size: 12px; color: var(--text-muted); margin-left: 8px; }
  }
  .selector-right { display: flex; gap: 8px; }
  .schedule-score { font-size: 11px; color: var(--text-muted); margin-left: 8px; }
}

.page-header {
  display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px;
  h1 { font-size: 24px; font-weight: 600; }
  .subtitle { font-size: 14px; color: var(--text-secondary); margin-left: 12px; }
  .header-actions { display: flex; gap: 8px; }
}

.view-controls {
  display: flex; justify-content: space-between; align-items: center;
  padding: 12px 20px; margin-bottom: 20px;
  .view-tabs {
    display: flex; gap: 4px;
    .view-tab {
      display: flex; align-items: center; gap: 6px; padding: 8px 16px;
      border-radius: 8px; cursor: pointer; transition: all 0.2s ease;
      color: var(--text-secondary);
      &:hover { background: var(--bg-color); }
      &.active { background: var(--primary-color); color: #fff; }
    }
  }
  .view-filters { display: flex; gap: 12px; }
}

// 约束摘要条
.validation-bar {
  display: flex; align-items: center; gap: 20px;
  padding: 10px 20px; margin-bottom: 16px; font-size: 13px;
  .vb-hard { color: #ef4444; display: flex; align-items: center; gap: 4px; font-weight: 600; }
  .vb-soft { color: #f59e0b; display: flex; align-items: center; gap: 4px; }
  .vb-score { margin-left: auto; font-weight: 600; color: var(--text-primary); }
}

.timetable-wrapper { padding: 0; overflow: hidden; }

.timetable {
  .timetable-header {
    display: flex; background: linear-gradient(135deg, #1e3a5f 0%, #2563eb 100%);
    .header-cell {
      flex: 1; padding: 16px; text-align: center;
      color: #fff; font-weight: 600;
      &.time-column { flex: none; width: 100px; }
    }
  }
  .timetable-body {
    .period-row {
      display: flex; border-bottom: 1px solid var(--border-color);
      &:last-child { border-bottom: none; }
      &:hover { background: #fafbfc; }
    }
    .time-column {
      width: 100px; padding: 12px; text-align: center;
      background: var(--bg-color); border-right: 1px solid var(--border-color);
      .period-num { font-weight: 600; color: var(--text-primary); }
      .period-time { font-size: 11px; color: var(--text-muted); margin-top: 4px; }
    }
    .day-column {
      flex: 1; padding: 8px; min-height: 80px;
      border-right: 1px solid var(--border-color);
      cursor: pointer; transition: background 0.15s ease;
      &:last-child { border-right: none; }
      &:hover { background: #f0f7ff; }
    }
    .break-row {
      background: linear-gradient(90deg, #fef3c7 0%, #fef9c3 50%, #fef3c7 100%);
      .break-content {
        padding: 8px; text-align: center;
        color: #92400e; font-weight: 500; font-size: 13px;
      }
    }
    .elective-row {
      background: #f8fafc;
      .time-column {
        background: #f1f5f9;
        .elective-label { font-size: 10px; color: #64748b; margin-top: 2px; }
      }
    }
    .friday-hidden { background: #f1f5f9; pointer-events: none; }
    .elective-placeholder {
      background: #f1f5f9; pointer-events: none;
      display: flex; align-items: center; justify-content: center;
      .elective-slot { .elective-text { color: #94a3b8; font-size: 13px; font-weight: 500; } }
    }
    .elective-available { background: #fefce8; border-left: 2px dashed #fbbf24; }
  }
}

// 课程单元格
.schedule-cell {
  height: 100%; padding: 8px 10px; border-radius: 8px;
  position: relative; cursor: grab;
  &:active { cursor: grabbing; }
  &.readonly-cell { cursor: default; }
  .subject-name { font-weight: 600; font-size: 14px; }
  .teacher-name { font-size: 12px; margin-top: 4px; opacity: 0.8; }
  .continuous-badge {
    position: absolute; top: 4px; right: 4px;
    font-size: 10px; padding: 1px 4px;
    background: rgba(255,255,255,0.5); border-radius: 3px;
  }
  .lock-badge {
    position: absolute; top: 4px; left: 4px;
    color: #92400e; opacity: 0.7;
  }
  // 违反标记
  &.violation-hard {
    box-shadow: 0 0 0 2.5px #ef4444 !important;
  }
  &.violation-soft {
    box-shadow: 0 0 0 2px #f59e0b !important;
  }
  .violation-badge {
    position: absolute; top: -6px; right: -6px;
    width: 18px; height: 18px; border-radius: 50%;
    font-size: 10px; font-weight: bold; z-index: 2;
    display: flex; align-items: center; justify-content: center;
    &.hard { background: #ef4444; color: #fff; }
    &.soft { background: #f59e0b; color: #fff; }
  }
}

.operation-hint {
  display: flex; align-items: center; gap: 8px; margin-top: 16px;
  padding: 12px 16px; background: #eff6ff; border-radius: 8px;
  color: var(--primary-color); font-size: 13px;
}

// 课程详情
.cell-detail {
  .detail-row {
    display: flex; padding: 12px 0; border-bottom: 1px solid var(--border-color);
    &:last-child { border-bottom: none; }
    .label { width: 80px; color: var(--text-secondary); }
    .value { font-weight: 500; }
  }
  .detail-violations {
    margin-top: 8px; padding: 8px; background: #fef2f2; border-radius: 8px;
    .violation-item {
      display: flex; align-items: flex-start; gap: 6px;
      font-size: 12px; padding: 4px 0;
      &.hard { color: #dc2626; }
      &.soft { color: #d97706; }
    }
  }
}

// 调换网格
.swap-grid-wrapper {
  .swap-source-info {
    margin-bottom: 12px; font-size: 14px; color: var(--text-secondary);
    strong { color: var(--text-primary); }
  }
  .swap-legend {
    display: flex; gap: 12px; margin-bottom: 12px; font-size: 12px; flex-wrap: wrap;
    .legend-item {
      padding: 2px 10px; border-radius: 4px; font-weight: 500;
      &.lg-available { background: #dcfce7; color: #166534; }
      &.lg-soft-risk { background: #fef9c3; color: #854d0e; }
      &.lg-conflict { background: #fee2e2; color: #991b1b; }
      &.lg-occupied { background: #e2e8f0; color: #475569; }
      &.lg-locked { background: #cbd5e1; color: #334155; }
      &.lg-self { background: #dbeafe; color: #1e40af; }
    }
  }
}

.swap-grid {
  border: 1px solid var(--border-color); border-radius: 8px; overflow: hidden;
  .sg-header {
    display: flex; background: #f1f5f9;
    .sg-time-col { width: 60px; padding: 8px; font-weight: 600; font-size: 12px; text-align: center; }
    .sg-day-col { flex: 1; padding: 8px; font-weight: 600; font-size: 13px; text-align: center; }
  }
  .sg-break {
    text-align: center; padding: 4px; background: #fef3c7; color: #92400e;
    font-size: 12px; font-weight: 500;
  }
  .sg-row {
    display: flex; border-top: 1px solid #e2e8f0;
    .sg-time-col {
      width: 60px; padding: 6px; font-size: 11px; text-align: center;
      background: #f8fafc; display: flex; align-items: center; justify-content: center;
      font-weight: 500; color: var(--text-secondary);
    }
  }
  .sg-cell {
    flex: 1; padding: 4px; min-height: 44px;
    border-left: 1px solid #e2e8f0; cursor: pointer;
    display: flex; align-items: center; justify-content: center;
    transition: all 0.15s ease;
    &.sg-self { background: #dbeafe; cursor: default; }
    &.sg-available { background: #dcfce7; &:hover { background: #bbf7d0; } }
    &.sg-soft-risk { background: #fef9c3; &:hover { background: #fde68a; } }
    &.sg-conflict { background: #fee2e2; &:hover { background: #fecaca; } }
    &.sg-locked { background: #cbd5e1; &:hover { background: #b0bec5; } }
    &.sg-occupied { background: #f1f5f9; &:hover { background: #e2e8f0; } }
    &.sg-selected { box-shadow: inset 0 0 0 3px #2563eb; border-radius: 4px; }
    .sg-cell-inner { text-align: center; font-size: 11px; line-height: 1.3; }
    .sg-self-mark { color: #1e40af; font-weight: 600; font-size: 12px; }
    .sg-subj { font-weight: 600; color: var(--text-primary); }
    .sg-teacher { color: var(--text-secondary); font-size: 10px; }
    .sg-empty { color: #94a3b8; }
  }
}

// 教研组组会信息栏
.meeting-info-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  background: #ecf5ff;
  border: 1px solid #b3d8ff;
  border-radius: 8px;
  margin-bottom: 16px;
  color: #409eff;
  font-size: 14px;
  b { color: #1d3557; }
}

// 组会时段标记
.meeting-slot {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  height: 100%;
  min-height: 52px;
  background: repeating-linear-gradient(
    -45deg,
    #ecf5ff,
    #ecf5ff 4px,
    #d9ecff 4px,
    #d9ecff 8px
  );
  border-radius: 6px;
  color: #409eff;
  font-size: 11px;
  font-weight: 600;
}
</style>
