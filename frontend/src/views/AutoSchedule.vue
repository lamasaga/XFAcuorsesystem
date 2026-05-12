<template>
  <div class="auto-schedule">
    <div class="page-header">
      <div class="page-title">
        <h1>自动排课</h1>
        <span class="subtitle">智能生成课程表</span>
      </div>
    </div>
    
    <!-- 步骤条 -->
    <div class="steps-wrapper card">
      <el-steps :active="currentStep" finish-status="success" align-center>
        <el-step title="数据检查" description="验证基础数据" />
        <el-step title="参数设置" description="配置排课参数" />
        <el-step title="开始排课" description="执行排课算法" />
        <el-step title="结果确认" description="查看并应用结果" />
      </el-steps>
    </div>
    
    <!-- 步骤内容 -->
    <div class="step-content card">
      <!-- Step 1: 数据检查 -->
      <div v-if="currentStep === 0" class="step-panel">
        <h3>基础数据检查</h3>
        <p class="desc">系统正在检查排课所需的基础数据是否完整...</p>
        
        <div class="check-list">
          <div v-for="check in dataChecks" :key="check.key" class="check-item">
            <div class="check-icon" :class="check.status">
              <el-icon v-if="check.status === 'success'"><CircleCheck /></el-icon>
              <el-icon v-else-if="check.status === 'warning'"><Warning /></el-icon>
              <el-icon v-else-if="check.status === 'loading'"><Loading /></el-icon>
              <el-icon v-else><CircleClose /></el-icon>
            </div>
            <div class="check-info">
              <div class="check-title">{{ check.title }}</div>
              <div class="check-detail">{{ check.detail }}</div>
            </div>
            <el-button v-if="check.action" type="primary" link @click="check.action">
              {{ check.actionText }}
            </el-button>
          </div>
        </div>
        
        <div class="check-summary" v-if="checkComplete">
          <el-alert
            :title="allChecksPassed ? '所有检查通过，可以开始排课' : '存在问题需要处理'"
            :type="allChecksPassed ? 'success' : 'warning'"
            :closable="false"
            show-icon
          />
        </div>
      </div>
      
      <!-- Step 2: 参数设置 -->
      <div v-if="currentStep === 1" class="step-panel">
        <h3>排课参数设置</h3>
        
        <el-form label-width="120px" class="param-form">
          <el-form-item label="排课范围">
            <el-radio-group v-model="scheduleParams.scope">
              <el-radio value="all">全校排课（重新生成所有课表）</el-radio>
              <el-radio value="grade">指定年级</el-radio>
              <el-radio value="class">指定班级</el-radio>
            </el-radio-group>
          </el-form-item>
          
          <el-form-item v-if="scheduleParams.scope === 'grade'" label="选择年级">
            <el-checkbox-group v-model="scheduleParams.grades">
              <el-checkbox v-for="g in availableGrades" :key="g.value" :value="g.value">{{ g.label }}</el-checkbox>
            </el-checkbox-group>
          </el-form-item>
          
          <el-form-item v-if="scheduleParams.scope === 'class'" label="选择班级">
            <el-select v-model="scheduleParams.classes" multiple placeholder="选择班级">
              <el-option v-for="c in classList" :key="c.value" :label="c.label" :value="c.value" />
            </el-select>
          </el-form-item>
          
          <el-divider />
          
          <el-form-item label="其他选项">
            <el-checkbox v-model="scheduleParams.keepManual">保留已手动调整的课程位置</el-checkbox>
          </el-form-item>
        </el-form>
      </div>
      
      <!-- Step 3: 排课进行中 -->
      <div v-if="currentStep === 2" class="step-panel">
        <h3>正在排课...</h3>
        
        <div class="progress-section">
          <div class="progress-header">
            <span class="current-stage">{{ currentStage }}</span>
            <span class="progress-percent">{{ Math.min(Math.round(progressPercent), 99) }}%</span>
          </div>
          <el-progress :percentage="Math.min(progressPercent, 99)" :stroke-width="12" :show-text="false" />
        </div>
        
        <div class="stage-list">
          <div v-for="stage in stages" :key="stage.key" class="stage-item" :class="stage.status">
            <el-icon v-if="stage.status === 'done'"><CircleCheck /></el-icon>
            <el-icon v-else-if="stage.status === 'running'" class="is-loading"><Loading /></el-icon>
            <el-icon v-else><Clock /></el-icon>
            <span class="stage-name">{{ stage.name }}</span>
            <span class="stage-time">{{ stage.time }}</span>
          </div>
        </div>
        
        <div class="realtime-stats">
          <div class="stat-item">
            <div class="stat-label">排课范围</div>
            <div class="stat-value">{{ scopeLabel }}</div>
          </div>
        </div>
        
        <div class="estimated-time">
          预计求解时间: <strong>{{ estimatedTime }}</strong>
          <span class="time-hint">（实际耗时取决于数据复杂度，可能提前完成）</span>
        </div>
      </div>
      
      <!-- Step 4: 结果确认 -->
      <div v-if="currentStep === 3" class="step-panel">
        <h3>排课完成 - 方案对比</h3>
        <p class="desc">生成了 {{ results.length }} 个可行方案，请选择最适合的方案</p>
        
        <div class="results-grid">
          <div 
            v-for="(result, idx) in results" 
            :key="idx"
            class="result-card"
            :class="{ selected: selectedResult === idx, recommended: result.recommended }"
            @click="selectedResult = idx"
          >
            <div class="result-header">
              <span class="result-title">方案 {{ String.fromCharCode(65 + idx) }}</span>
              <el-tag v-if="result.recommended" type="warning" size="small">推荐</el-tag>
            </div>
            <div class="result-score">
              <span class="score-value">{{ result.score }}</span>
              <span class="score-label">总分</span>
            </div>
            <div class="result-metrics">
              <div class="metric">
                <span class="metric-label">任务完成</span>
                <span class="metric-value">{{ result.scheduledTasks }}/{{ result.totalTasks }}</span>
              </div>
              <div class="metric">
                <span class="metric-label">主科上午率</span>
                <span class="metric-value">{{ result.mainMorningRate }}%</span>
              </div>
              <div class="metric">
                <span class="metric-label">教师空窗期</span>
                <span class="metric-value">{{ result.teacherGaps }}</span>
              </div>
              <div class="metric">
                <span class="metric-label">连堂完整性</span>
                <span class="metric-value">{{ result.continuousRate }}%</span>
              </div>
            </div>
            <el-button type="primary" link @click.stop="previewResult(idx)">预览课表</el-button>
          </div>
        </div>
        
        <div class="result-detail card" v-if="results.length > 0">
          <h4>详细评估报告 — 方案 {{ String.fromCharCode(65 + selectedResult) }}</h4>
          <div class="detail-list">
            <div class="detail-item" :class="results[selectedResult].failedTasks === 0 ? 'success' : 'warning'">
              <el-icon><component :is="results[selectedResult].failedTasks === 0 ? CircleCheck : Warning" /></el-icon>
              <span>排课任务: {{ results[selectedResult].scheduledTasks }} / {{ results[selectedResult].totalTasks }} 个
                <template v-if="results[selectedResult].failedTasks > 0">（{{ results[selectedResult].failedTasks }} 个未排入）</template>
              </span>
            </div>
            <div class="detail-item success">
              <el-icon><CircleCheck /></el-icon>
              <span>总排课节数: {{ results[selectedResult].totalPeriods }} 节</span>
            </div>
            <div class="detail-item success">
              <el-icon><CircleCheck /></el-icon>
              <span>主科上午率: {{ results[selectedResult].mainMorningRate }}%</span>
            </div>
            <div class="detail-item" :class="results[selectedResult].teacherGaps < 10 ? 'success' : 'warning'">
              <el-icon><component :is="results[selectedResult].teacherGaps < 10 ? CircleCheck : Warning" /></el-icon>
              <span>教师空窗期: {{ results[selectedResult].teacherGaps }} 个</span>
            </div>
            <div class="detail-item success">
              <el-icon><CircleCheck /></el-icon>
              <span>连堂完整率: {{ results[selectedResult].continuousRate }}%</span>
            </div>
            <div class="detail-item success">
              <el-icon><CircleCheck /></el-icon>
              <span>排课总耗时: {{ totalDurationSeconds }} 秒</span>
            </div>
          </div>
        </div>

        <!-- 历史批次 -->
        <div class="history-section" v-if="historyBatches.length > 0">
          <div class="history-header">
            <h4>历史排课批次 (最近 {{ historyBatches.length }} 次)</h4>
            <el-button link type="primary" @click="loadHistory">刷新</el-button>
          </div>
          <div class="batch-list">
            <div
              v-for="batch in historyBatches"
              :key="batch.batchId"
              class="batch-card"
              :class="{ active: batch.hasActive }"
            >
              <div class="batch-meta">
                <span class="batch-time">{{ batch.createdAt }}</span>
                <el-tag v-if="batch.hasActive" type="success" size="small">已激活</el-tag>
                <el-tag size="small" type="info">{{ batch.plans.length }} 个方案</el-tag>
              </div>
              <div class="batch-plans">
                <div
                  v-for="plan in batch.plans"
                  :key="plan.id"
                  class="batch-plan-item"
                  :class="{ 'is-active': plan.is_active }"
                >
                  <span class="plan-name">{{ plan.name }}</span>
                  <span class="plan-score">{{ plan.score }} 分</span>
                  <el-button size="small" link type="primary" @click="previewSchedule(plan.id)">预览</el-button>
                  <el-button size="small" link type="success" @click="activateHistoryPlan(plan.id)" :disabled="plan.is_active">应用</el-button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 底部操作栏 -->
    <div class="step-actions card">
      <el-button v-if="currentStep > 0 && currentStep < 3" @click="prevStep">上一步</el-button>
      <el-button v-if="currentStep === 2" @click="cancelSchedule" type="danger" plain>取消排课</el-button>
      <div style="flex: 1"></div>
      <el-button v-if="currentStep < 2" type="primary" @click="nextStep" :disabled="!canProceed">
        {{ currentStep === 1 ? '开始排课' : '下一步' }}
      </el-button>
      <el-button v-if="currentStep === 3" @click="reschedule">重新排课</el-button>
      <el-button v-if="currentStep === 3" type="primary" @click="applyResult">
        应用选中方案
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { CircleCheck, Warning, CircleClose, Loading, Clock } from '@element-plus/icons-vue'
import { generateSchedule, activateSchedule, getScheduleList } from '@/api/schedules'
import { checkDataReadiness } from '@/api/stats'
import { getClasses } from '@/api/classes'

const router = useRouter()
const currentStep = ref(0)
const isScheduling = ref(false)
const checkLoading = ref(false)

// Step 1: 数据检查
const dataChecks = ref([])
const checkComplete = ref(false)
const allChecksPassed = ref(false)
const canSchedule = ref(false)

/**
 * 从后端加载数据检查状态
 */
const loadDataChecks = async () => {
  checkLoading.value = true
  try {
    const res = await checkDataReadiness()
    const data = res.data
    
    // 将后端返回的检查结果转换为前端格式
    dataChecks.value = data.checks.map(check => ({
      key: check.key,
      title: check.title,
      detail: check.detail,
      status: check.status,
      // 为某些检查项添加跳转操作
      action: check.status === 'error' || check.status === 'warning' ? getActionForCheck(check.key) : null,
      actionText: check.status === 'error' ? '去配置' : (check.status === 'warning' ? '查看' : null)
    }))
    
    allChecksPassed.value = data.all_passed
    canSchedule.value = data.can_schedule
    checkComplete.value = true
  } catch (error) {
    console.error('数据检查失败:', error)
    // 使用默认的模拟数据
    dataChecks.value = [
      { key: 'teacher', title: '教师数据', detail: '无法连接后端，请检查服务', status: 'error' },
      { key: 'class', title: '班级数据', detail: '无法连接后端，请检查服务', status: 'error' }
    ]
    checkComplete.value = true
  } finally {
    checkLoading.value = false
  }
}

/**
 * 根据检查项返回对应的跳转操作
 */
const getActionForCheck = (key) => {
  const routes = {
    teacher: () => router.push('/data/teachers'),
    class: () => router.push('/data/classes'),
    subject: () => router.push('/data/subjects'),
    task: () => router.push('/data/plan'),
    venue: () => router.push('/data/venues'),
    layer: () => router.push('/data/layers')
  }
  return routes[key] || null
}

// 页面加载时执行数据检查
onMounted(() => {
  loadDataChecks()
  loadClassList()
})

// Step 2: 参数设置
const scheduleParams = ref({
  scope: 'all',
  grades: [],
  classes: [],
  keepManual: false
})
const classList = ref([])

// 年级配置
const gradeConfig = [
  { value: 'PK', label: 'PK (学前班)' },
  { value: 'KG', label: 'KG (幼儿园)' },
  { value: 'G1', label: 'G1 (一年级)' },
  { value: 'G2', label: 'G2 (二年级)' },
  { value: 'G3', label: 'G3 (三年级)' },
  { value: 'G4', label: 'G4 (四年级)' },
  { value: 'G5', label: 'G5 (五年级)' },
  { value: 'G6', label: 'G6 (六年级)' },
  { value: 'G7', label: 'G7 (七年级)' },
  { value: 'G8', label: 'G8 (八年级)' },
  { value: 'G9', label: 'G9 (九年级)' },
  { value: 'G10', label: 'G10 (十年级)' },
  { value: 'G11', label: 'G11 (十一年级)' }
]

// 从班级数据中获取实际存在的年级
const availableGrades = computed(() => {
  const gradesInData = new Set(classList.value.map(c => c.grade).filter(Boolean))
  return gradeConfig.filter(g => gradesInData.has(g.value))
})

/**
 * 加载班级列表
 */
const loadClassList = async () => {
  try {
    const res = await getClasses({ page: 1, page_size: 200 })
    classList.value = res.data.items.map(c => ({
      value: c.id,
      label: c.name,
      grade: c.grade  // 保留年级信息
    }))
  } catch (error) {
    console.error('加载班级列表失败:', error)
  }
}

// Step 3: 排课进行中
const currentStage = ref('排课引擎启动中...')
const progressPercent = ref(0)
const stages = ref([
  { key: 'load', name: '加载数据', status: 'pending', time: '-' },
  { key: 'build', name: '构建约束模型', status: 'pending', time: '-' },
  { key: 'solve', name: 'CP-SAT 求解', status: 'pending', time: '-' },
  { key: 'evaluate', name: '方案评估', status: 'pending', time: '-' },
  { key: 'save', name: '保存结果', status: 'pending', time: '-' }
])
const estimatedTime = ref('计算中...')

// 排课范围标签
const scopeLabel = computed(() => {
  const labels = { all: '全校', grade: '指定年级', class: '指定班级' }
  return labels[scheduleParams.value.scope] || '全校'
})

let progressTimer = null

// Step 4: 结果
const results = ref([])
const selectedResult = ref(0)
const scheduleResult = ref(null) // 保存后端返回的排课结果
const actualTotalDuration = ref(0) // 实际总耗时（秒）

// 总耗时显示（优先用实际记录的总耗时）
const totalDurationSeconds = computed(() => {
  if (actualTotalDuration.value > 0) {
    return actualTotalDuration.value.toFixed(1)
  }
  // 降级：用各方案的 durationSeconds 加总
  const total = results.value.reduce((sum, r) => sum + (r.durationSeconds || 0), 0)
  return total.toFixed(1)
})

const canProceed = computed(() => {
  if (currentStep.value === 0) return canSchedule.value
  if (currentStep.value === 1) return true
  return false
})

const nextStep = () => {
  if (currentStep.value === 1) {
    currentStep.value = 2
    startScheduling()
  } else {
    currentStep.value++
  }
}

const prevStep = () => {
  currentStep.value--
}

const updateStageStatus = (stageKey, status) => {
  const stage = stages.value.find(s => s.key === stageKey)
  if (stage) stage.status = status
}

const startScheduling = async () => {
  isScheduling.value = true
  progressPercent.value = 0
  actualTotalDuration.value = 0
  const startTime = Date.now()
  
  // 固定求解时间预估（优化程度=5, 1个方案）
  const totalEstimatedSeconds = 600
  
  // 格式化预计时间
  if (totalEstimatedSeconds < 60) {
    estimatedTime.value = `约 ${totalEstimatedSeconds} 秒`
  } else {
    const mins = Math.round(totalEstimatedSeconds / 60)
    estimatedTime.value = `约 ${mins} 分钟`
  }
  
  // 进度条动画：根据预计时间自适应速度
  const progressInterval = 500 // 每 500ms 更新一次
  const totalTicks = (totalEstimatedSeconds * 1000) / progressInterval
  const progressPerTick = 90 / Math.max(totalTicks, 1)
  
  progressTimer = setInterval(() => {
    if (progressPercent.value < 90) {
      progressPercent.value += progressPerTick * (0.5 + Math.random())
    }
  }, progressInterval)

  try {
    updateStageStatus('load', 'running')
    currentStage.value = '正在加载排课数据...'
    
    // 模拟阶段进度（按时间比例推进）
    setTimeout(() => {
      updateStageStatus('load', 'done')
      updateStageStatus('build', 'running')
      currentStage.value = '正在构建约束模型...'
    }, 2000)
    setTimeout(() => {
      updateStageStatus('build', 'done')
      updateStageStatus('solve', 'running')
      currentStage.value = '求解器正在优化排课方案...'
    }, 5000)
    
    // 调用后端 API，传递参数
    const response = await generateSchedule({
      scope: scheduleParams.value.scope,
      grades: scheduleParams.value.grades,
      classes: scheduleParams.value.classes,
      optimization: 5,
      planCount: 1,
      keepManual: scheduleParams.value.keepManual
    })
    scheduleResult.value = response.data
    
    // 记录实际耗时
    actualTotalDuration.value = (Date.now() - startTime) / 1000
    
    // 更新各阶段状态为已完成
    stages.value.forEach(s => { s.status = 'done' })
    currentStage.value = '排课完成！'
    progressPercent.value = 100
    clearInterval(progressTimer)
    
    ElMessage.success('排课成功！')
    
    // 使用后端返回的真实数据构建结果展示（支持多方案）
    const data = scheduleResult.value
    if (data.plans && data.plans.length > 0) {
      results.value = data.plans.map((plan, idx) => ({
        scheduleId: plan.schedule_id,
        score: plan.score,
        teacherGaps: plan.teacher_gaps,
        mainMorningRate: plan.main_morning_rate || 0,
        continuousRate: plan.continuous_rate || 0,
        recommended: plan.recommended || idx === 0,
        totalTasks: plan.total_tasks,
        scheduledTasks: plan.scheduled_tasks,
        failedTasks: plan.failed_tasks,
        totalPeriods: plan.total_periods,
        durationSeconds: plan.duration_seconds
      }))
    } else {
      // 兼容旧格式（单方案）
      results.value = [{
        scheduleId: data.schedule_id,
        score: data.score,
        teacherGaps: data.teacher_gaps,
        mainMorningRate: data.main_morning_rate || 100,
        continuousRate: data.continuous_rate || 100,
        recommended: true,
        totalTasks: data.total_tasks,
        scheduledTasks: data.scheduled_tasks,
        failedTasks: data.failed_tasks,
        totalPeriods: data.total_periods,
        durationSeconds: data.duration_seconds
      }]
    }
    
    setTimeout(() => {
      currentStep.value = 3
      loadHistory()
    }, 1000)
    
  } catch (error) {
    clearInterval(progressTimer)
    const detail = error.response?.data?.detail || error.message
    // 422 = 无解(带诊断信息)，用弹窗展示详情
    if (error.response?.status === 422) {
      ElMessageBox.alert(detail, '排课无解', {
        confirmButtonText: '我知道了',
        type: 'warning',
        dangerouslyUseHTMLString: false,
      })
    } else {
      ElMessage.error('排课失败: ' + detail)
    }
    currentStep.value = 1
  } finally {
    isScheduling.value = false
  }
}

const cancelSchedule = () => {
  clearInterval(progressTimer)
  currentStep.value = 1
  ElMessage.info('排课已取消')
}

const reschedule = () => {
  currentStep.value = 1
  results.value = []
  scheduleResult.value = null
  actualTotalDuration.value = 0
  // 重置阶段状态
  stages.value.forEach(s => {
    s.status = 'pending'
    s.time = '-'
  })
}

const previewResult = (idx) => {
  const result = results.value[idx]
  if (result && result.scheduleId) {
    router.push(`/timetable?schedule_id=${result.scheduleId}`)
  } else {
    ElMessage.info(`预览方案 ${String.fromCharCode(65 + idx)}`)
  }
}

const applyResult = async () => {
  const selected = results.value[selectedResult.value]
  if (!selected || !selected.scheduleId) {
    ElMessage.error('无法激活课表：缺少课表ID')
    return
  }
  
  try {
    await activateSchedule(selected.scheduleId)
    ElMessage.success('方案已应用，正在跳转到课表管理...')
    setTimeout(() => {
      router.push(`/timetable?schedule_id=${selected.scheduleId}`)
    }, 1000)
  } catch (error) {
    ElMessage.error('激活课表失败: ' + error.message)
  }
}

// ---- 历史批次管理 ----
const historyBatches = ref([])

const loadHistory = async () => {
  try {
    const res = await getScheduleList()
    const items = res.data?.items || []
    // 按 batch_id 分组
    const batchMap = {}
    items.forEach(s => {
      const bid = s.batch_id || `single_${s.id}`
      if (!batchMap[bid]) {
        batchMap[bid] = {
          batchId: bid,
          createdAt: s.created_at ? new Date(s.created_at).toLocaleString('zh-CN') : '-',
          hasActive: false,
          plans: [],
        }
      }
      batchMap[bid].plans.push(s)
      if (s.is_active) batchMap[bid].hasActive = true
    })
    historyBatches.value = Object.values(batchMap).slice(0, 6)
  } catch (e) {
    console.warn('加载历史批次失败', e)
  }
}

const previewSchedule = (scheduleId) => {
  router.push(`/timetable?schedule_id=${scheduleId}`)
}

const activateHistoryPlan = async (scheduleId) => {
  try {
    await activateSchedule(scheduleId)
    ElMessage.success('方案已激活')
    loadHistory()
  } catch (e) {
    ElMessage.error('激活失败: ' + (e.message || e))
  }
}

onUnmounted(() => {
  if (progressTimer) clearInterval(progressTimer)
})
</script>

<style lang="scss" scoped>
.auto-schedule { max-width: 1000px; margin: 0 auto; }

.page-header {
  margin-bottom: 24px;
  h1 { font-size: 24px; font-weight: 600; }
  .subtitle { font-size: 14px; color: var(--text-secondary); margin-left: 12px; }
}

.steps-wrapper { padding: 24px 40px; margin-bottom: 20px; }

.step-content { padding: 32px; min-height: 400px; }

.step-panel {
  h3 { font-size: 18px; font-weight: 600; margin-bottom: 8px; }
  .desc { color: var(--text-secondary); margin-bottom: 24px; }
}

// Step 1 样式
.check-list { margin-bottom: 24px; }
.check-item {
  display: flex; align-items: center; gap: 16px;
  padding: 16px; background: var(--bg-color); border-radius: 10px; margin-bottom: 12px;
  .check-icon {
    width: 40px; height: 40px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 20px;
    &.success { background: #dcfce7; color: #16a34a; }
    &.warning { background: #fef3c7; color: #d97706; }
    &.error { background: #fee2e2; color: #dc2626; }
    &.loading { background: #e0e7ff; color: #4f46e5; }
  }
  .check-info { flex: 1; .check-title { font-weight: 600; margin-bottom: 2px; } .check-detail { font-size: 13px; color: var(--text-secondary); } }
}

// Step 2 样式
.param-form { max-width: 600px; }

// Step 3 样式
.progress-section {
  margin-bottom: 32px;
  .progress-header { display: flex; justify-content: space-between; margin-bottom: 12px; .current-stage { font-weight: 600; } .progress-percent { color: var(--primary-color); font-weight: 600; } }
}
.stage-list { margin-bottom: 24px; }
.stage-item {
  display: flex; align-items: center; gap: 12px; padding: 10px 0;
  border-bottom: 1px solid var(--border-color);
  &:last-child { border-bottom: none; }
  .el-icon { font-size: 18px; }
  &.done { color: #16a34a; }
  &.running { color: var(--primary-color); .el-icon { animation: spin 1s linear infinite; } }
  &.pending { color: var(--text-muted); }
  .stage-name { flex: 1; }
  .stage-time { font-size: 13px; color: var(--text-muted); }
}
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

.realtime-stats {
  display: flex; gap: 32px; padding: 20px; background: var(--bg-color); border-radius: 10px; margin-bottom: 20px;
  .stat-item { text-align: center; .stat-label { font-size: 13px; color: var(--text-secondary); margin-bottom: 4px; } .stat-value { font-size: 24px; font-weight: 700; color: var(--primary-color); &.success { color: #16a34a; } } }
}
.estimated-time {
  text-align: center; color: var(--text-secondary);
  strong { color: var(--text-primary); }
  .time-hint { font-size: 12px; color: var(--text-muted); }
}

// Step 4 样式
.results-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 24px; }
.result-card {
  padding: 20px; border: 2px solid var(--border-color); border-radius: 12px;
  cursor: pointer; transition: all 0.2s ease;
  &:hover { border-color: var(--primary-color); }
  &.selected { border-color: var(--primary-color); background: #f0f7ff; }
  &.recommended { position: relative; }
  .result-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; .result-title { font-weight: 600; } }
  .result-score { text-align: center; margin-bottom: 16px; .score-value { font-size: 36px; font-weight: 700; color: var(--primary-color); } .score-label { display: block; font-size: 12px; color: var(--text-muted); } }
  .result-metrics { .metric { display: flex; justify-content: space-between; padding: 6px 0; font-size: 13px; .metric-label { color: var(--text-secondary); } .metric-value { font-weight: 600; } } }
}

.result-detail {
  padding: 20px;
  h4 { font-size: 15px; font-weight: 600; margin-bottom: 16px; }
  .detail-list { .detail-item { display: flex; align-items: center; gap: 8px; padding: 8px 0; &.success { color: #16a34a; } &.warning { color: #d97706; } } }
}

// 历史批次
.history-section {
  margin-top: 32px;

  .history-header {
    display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;
    h4 { font-size: 16px; font-weight: 600; }
  }
}

.batch-list { display: flex; flex-direction: column; gap: 12px; }

.batch-card {
  padding: 16px; background: #f9fafb; border-radius: 10px; border: 1px solid var(--border-color);

  &.active { border-color: #86efac; background: #f0fdf4; }

  .batch-meta {
    display: flex; align-items: center; gap: 10px; margin-bottom: 10px;
    .batch-time { font-size: 13px; color: var(--text-secondary); }
  }

  .batch-plans { display: flex; flex-direction: column; gap: 6px; }

  .batch-plan-item {
    display: flex; align-items: center; gap: 12px; padding: 8px 12px;
    background: #fff; border-radius: 6px;

    &.is-active { background: #dcfce7; }

    .plan-name { flex: 1; font-size: 13px; font-weight: 500; }
    .plan-score { font-weight: 700; color: var(--primary-color); min-width: 50px; }
  }
}

.step-actions {
  display: flex; align-items: center; gap: 12px;
  padding: 16px 24px; margin-top: 20px;
}
</style>
