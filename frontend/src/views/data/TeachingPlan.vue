<template>
  <div class="teaching-plan">
    <div class="toolbar">
      <div class="toolbar-left">
        <el-select v-model="selectedGrade" placeholder="选择年级" @change="onGradeChange">
          <el-option v-for="g in availableGrades" :key="g.value" :label="g.label" :value="g.value" />
        </el-select>
        <el-select v-model="selectedClass" placeholder="选择班级" style="margin-left: 12px" :disabled="!selectedGrade">
          <el-option v-for="c in filteredClasses" :key="c.id" :label="c.name" :value="c.id" />
        </el-select>
      </div>
      <div class="toolbar-right">
        <el-button @click="loadExistingTasks" :disabled="!selectedClass">
          <el-icon><Refresh /></el-icon>加载已有任务
        </el-button>
        <el-button type="primary" @click="savePlan" :loading="saving" :disabled="!selectedClass">
          <el-icon><Check /></el-icon>保存计划
        </el-button>
      </div>
    </div>
    
    <el-alert v-if="!selectedClass" title="请先选择年级和班级，然后为该班级配置各科目的任课教师" type="info" :closable="false" show-icon style="margin-bottom: 20px" />
    
    <el-alert v-if="selectedClass && layeredSubjectCount > 0" type="warning" :closable="false" show-icon style="margin-bottom: 20px">
      <template #title>
        当前年级有 <strong>{{ layeredSubjectCount }}</strong> 门科目已在「分层课程」中配置，不在此处显示。
        <el-button type="primary" link @click="$router.push('/data/layers')">前往分层课程</el-button>
      </template>
    </el-alert>
    
    <div class="plan-table-wrapper" v-loading="loading">
      <el-table :data="planData" border stripe>
        <el-table-column prop="subject" label="科目" width="120" fixed>
          <template #default="{ row }">
            <div class="subject-cell">
              <span class="subject-dot" :style="{ background: row.color }"></span>
              <span>{{ row.subject }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="weeklyHours" label="周课时" width="100">
          <template #default="{ row }">
            <el-input-number v-model="row.weeklyHours" :min="0" :max="10" size="small" controls-position="right" />
          </template>
        </el-table-column>
        <el-table-column prop="isContinuous" label="连堂" width="80">
          <template #default="{ row }">
            <el-switch v-model="row.isContinuous" size="small" />
          </template>
        </el-table-column>
        <el-table-column prop="continuousCount" label="连堂节数" width="100">
          <template #default="{ row }">
            <el-select v-model="row.continuousCount" size="small" :disabled="!row.isContinuous" style="width: 70px">
              <el-option :value="2" label="2节" />
              <el-option :value="3" label="3节" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column prop="preferredTime" label="优先时段" width="120">
          <template #default="{ row }">
            <el-select v-model="row.preferredTime" size="small" style="width: 90px">
              <el-option value="MORNING" label="上午" />
              <el-option value="AFTERNOON" label="下午" />
              <el-option value="" label="不限" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="任课教师" min-width="200">
          <template #default="{ row }">
            <el-select 
              v-model="row.teacherId" 
              placeholder="选择教师" 
              size="small" 
              style="width: 100%" 
              clearable
              filterable
              :filter-method="filterTeacher"
              @visible-change="(visible) => { if(visible) teacherFilterText = '' }"
            >
              <el-option 
                v-for="t in filteredTeachers" 
                :key="t.id" 
                :label="t.name" 
                :value="t.id"
              >
                <span>{{ t.name }}</span>
                <span style="color: #999; font-size: 12px; margin-left: 8px">{{ t.type === 'CN' ? '中教' : '外教' }}</span>
              </el-option>
            </el-select>
          </template>
        </el-table-column>
        <el-table-column prop="remark" label="备注" min-width="150">
          <template #default="{ row }">
            <el-input v-model="row.remark" size="small" placeholder="备注" />
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag v-if="row.existingTaskId" type="success" size="small">已配置</el-tag>
            <el-tag v-else-if="row.teacherId" type="warning" size="small">待保存</el-tag>
            <el-tag v-else type="info" size="small">未配置</el-tag>
          </template>
        </el-table-column>
      </el-table>
    </div>
    
    <div class="plan-summary">
      <div class="summary-item">
        <span class="label">周总课时:</span>
        <span class="value">{{ totalHours }}</span>
      </div>
      <div class="summary-item">
        <span class="label">已配置科目:</span>
        <span class="value">{{ configuredCount }} / {{ planData.length }}</span>
      </div>
      <div class="summary-item">
        <span class="label">连堂课程:</span>
        <span class="value">{{ continuousCount }} 门</span>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * 行政课程页面（原教学计划）
 * 
 * 功能：
 * - 选择年级和班级
 * - 为每个科目配置任课教师、周课时、连堂设置
 * - 保存时创建/更新教学任务
 * - 自动排除已在分层课程中配置的科目
 */
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Check, Refresh } from '@element-plus/icons-vue'
import { getTeachers } from '@/api/teachers'
import { getSubjects } from '@/api/subjects'
import { getClasses } from '@/api/classes'
import { createTasksBatch, getTasksWithDetails, updateTask } from '@/api/tasks'
import { getLayerGroups } from '@/api/layers'

const selectedGrade = ref('')
const selectedClass = ref(null)
const loading = ref(false)
const saving = ref(false)

// 数据列表
const classList = ref([])
const teacherOptions = ref([])
const planData = ref([])
const allSubjects = ref([]) // 存储所有科目（含适用范围信息）
const layerGroups = ref([])  // 存储分层课程配置

// 教师搜索
const teacherFilterText = ref('')

// 根据搜索文本筛选教师
const filteredTeachers = computed(() => {
  if (!teacherFilterText.value) return teacherOptions.value
  const text = teacherFilterText.value.toLowerCase()
  return teacherOptions.value.filter(t => 
    t.name.toLowerCase().includes(text) || 
    (t.pinyin && t.pinyin.toLowerCase().includes(text))
  )
})

// 教师搜索方法
const filterTeacher = (query) => {
  teacherFilterText.value = query
}

// 年级配置 - 按学校实际年级设置
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
  { value: 'G11', label: 'G11 (十一年级)' },
  { value: 'G12', label: 'G12 (十二年级)' }
]

// 从班级数据中获取实际存在的年级
const availableGrades = computed(() => {
  const gradesInData = new Set(classList.value.map(c => c.grade))
  // 只显示实际存在班级的年级，按配置顺序排列
  return gradeConfig.filter(g => gradesInData.has(g.value))
})

// 科目颜色映射
const subjectColors = {
  '语文': '#ef4444', '数学': '#3b82f6', '英语': '#f59e0b',
  '体育': '#10b981', '音乐': '#8b5cf6', '美术': '#ec4899',
  '科学': '#06b6d4', '品德': '#84cc16', '物理': '#10b981',
  '化学': '#8b5cf6', '生物': '#06b6d4', '历史': '#64748b',
  '地理': '#84cc16', '政治': '#ec4899'
}

// 过滤当前年级的班级
const filteredClasses = computed(() => {
  if (!selectedGrade.value) return []
  return classList.value.filter(c => c.grade === selectedGrade.value)
})

// 统计
const totalHours = computed(() => planData.value.reduce((sum, p) => sum + (p.weeklyHours || 0), 0))
const configuredCount = computed(() => planData.value.filter(p => p.teacherId).length)
const continuousCount = computed(() => planData.value.filter(p => p.isContinuous).length)

// 当前年级在分层课程中配置的科目数量
const layeredSubjectCount = computed(() => {
  if (!selectedGrade.value) return 0
  return layerGroups.value.filter(lg => lg.grades && lg.grades.includes(selectedGrade.value)).length
})

/**
 * 加载基础数据
 */
const loadBasicData = async () => {
  loading.value = true
  try {
    const [teachersRes, classesRes, subjectsRes, layersRes] = await Promise.all([
      getTeachers({ page: 1, page_size: 200 }),
      getClasses({ page: 1, page_size: 200 }),
      getSubjects({ page: 1, page_size: 100 }),
      getLayerGroups({ page: 1, page_size: 100 })
    ])
    
    teacherOptions.value = teachersRes.data.items.map(t => ({ 
      id: t.id, 
      name: t.name, 
      type: t.type || 'CN',  // 教师类型：CN=中教, FN=外教
      pinyin: t.pinyin || ''  // 拼音，用于搜索
    }))
    // 保存班级类型信息（I=国际班, N=综素班）
    // 从班级名称解析年级（如 IG3-1 -> G3，NG2-1 -> G2）
    classList.value = classesRes.data.items.map(c => {
      let grade = c.grade
      // 如果 grade 为空，尝试从班级名称解析
      if (!grade && c.name) {
        const match = c.name.match(/[IN]?(PK|KG|G\d+)/i)
        if (match) {
          grade = match[1].toUpperCase()
        }
      }
      return { 
        id: c.id, 
        name: c.name, 
        grade: grade,
        type: c.type || (c.name?.startsWith('I') ? 'I' : 'N')
      }
    }).filter(c => c.grade) // 过滤掉无法解析年级的班级
    
    console.log('加载班级数据:', classList.value.length, '个班级')
    console.log('年级列表:', [...new Set(classList.value.map(c => c.grade))])
    
    // 存储完整的科目信息（用于筛选）
    allSubjects.value = subjectsRes.data.items.map(s => ({
      id: s.id,
      name: s.name,
      color: s.color || subjectColors[s.name] || '#3b82f6',
      is_main: s.is_main,
      applicable_grades: s.applicable_grades || [],
      applicable_class_types: s.applicable_class_types || []
    }))
    
    // 存储分层课程配置（用于排除已配置的科目）
    layerGroups.value = layersRes.data.items || []
    console.log('加载分层课程:', layerGroups.value.length, '个')
    
    // 初始化为空（等选择班级后再根据筛选结果显示）
    planData.value = []
  } catch (error) {
    ElMessage.error('加载数据失败: ' + error.message)
  } finally {
    loading.value = false
  }
}

/**
 * 根据选中班级筛选适用的科目
 */
const filterSubjectsForClass = (classId) => {
  if (!classId) {
    planData.value = []
    return
  }
  
  const selectedClassInfo = classList.value.find(c => c.id === classId)
  if (!selectedClassInfo) {
    planData.value = []
    return
  }
  
  const classGrade = selectedClassInfo.grade
  // 将班级类型转换为科目设置中的班型标识
  const classTypeMapping = { 'I': 'INTERNATIONAL', 'N': 'COMPREHENSIVE' }
  const classType = classTypeMapping[selectedClassInfo.type] || 'INTERNATIONAL'
  
  // 获取该年级已在分层课程中配置的科目ID列表
  const layeredSubjectIds = layerGroups.value
    .filter(lg => lg.grades && lg.grades.includes(classGrade))
    .map(lg => lg.subject_id)
  
  console.log(`年级 ${classGrade} 的分层课程科目ID:`, layeredSubjectIds)
  
  // 筛选适用的科目（排除已在分层课程中配置的）
  const applicableSubjects = allSubjects.value.filter(s => {
    // 年级筛选：空数组表示适用所有年级
    const gradeMatch = s.applicable_grades.length === 0 || s.applicable_grades.includes(classGrade)
    // 班型筛选：空数组表示适用所有班型
    const typeMatch = s.applicable_class_types.length === 0 || s.applicable_class_types.includes(classType)
    // 排除已在分层课程中配置的科目
    const notLayered = !layeredSubjectIds.includes(s.id)
    return gradeMatch && typeMatch && notLayered
  })
  
  // 生成计划数据
  planData.value = applicableSubjects.map(s => ({
    subjectId: s.id,
    subject: s.name,
    color: s.color,
    weeklyHours: s.is_main ? 5 : 2,
    isContinuous: ['体育', '美术'].includes(s.name),
    continuousCount: 2,
    preferredTime: s.is_main ? 'MORNING' : '',
    teacherId: null,
    remark: '',
    existingTaskId: null
  }))
}

/**
 * 年级变化时重置班级选择
 */
const onGradeChange = () => {
  selectedClass.value = null
  planData.value = []
}

/**
 * 加载已有的教学任务
 */
const loadExistingTasks = async () => {
  if (!selectedClass.value) return
  
  loading.value = true
  try {
    const res = await getTasksWithDetails({ class_id: selectedClass.value })
    const existingTasks = res.data.items || []
    
    planData.value.forEach(p => {
      const task = existingTasks.find(t => t.subject_id === p.subjectId)
      if (task) {
        p.teacherId = task.teacher_id
        p.weeklyHours = task.weekly_hours
        p.isContinuous = task.is_continuous
        p.continuousCount = task.continuous_count || 2
        p.preferredTime = task.preferred_period || ''
        p.remark = task.note || ''
        p.existingTaskId = task.id
      } else {
        p.teacherId = null
        p.existingTaskId = null
      }
    })
    
    ElMessage.success(`已加载 ${existingTasks.length} 个教学任务`)
  } catch (error) {
    ElMessage.error('加载任务失败: ' + error.message)
  } finally {
    loading.value = false
  }
}

/**
 * 班级变化时筛选科目并加载已有任务
 */
watch(selectedClass, (newVal) => {
  if (newVal) {
    filterSubjectsForClass(newVal)
    loadExistingTasks()
  } else {
    planData.value = []
  }
})

/**
 * 保存行政课程
 */
const savePlan = async () => {
  if (!selectedClass.value) {
    ElMessage.warning('请先选择班级')
    return
  }
  
  const toCreate = []
  const toUpdate = []
  
  for (const p of planData.value) {
    if (p.teacherId) {
      const taskData = {
        teacher_id: p.teacherId,
        class_id: selectedClass.value,
        subject_id: p.subjectId,
        weekly_hours: p.weeklyHours,
        is_continuous: p.isContinuous,
        continuous_count: p.isContinuous ? p.continuousCount : 2,
        preferred_period: p.preferredTime || null,
        note: p.remark || null
      }
      
      if (p.existingTaskId) {
        toUpdate.push({ id: p.existingTaskId, ...taskData })
      } else {
        toCreate.push(taskData)
      }
    }
  }
  
  if (toCreate.length === 0 && toUpdate.length === 0) {
    ElMessage.warning('没有需要保存的教学任务')
    return
  }
  
  saving.value = true
  try {
    let createdCount = 0
    let updatedCount = 0
    
    if (toCreate.length > 0) {
      await createTasksBatch(toCreate)
      createdCount = toCreate.length
    }
    
    for (const task of toUpdate) {
      const { id, ...data } = task
      await updateTask(id, data)
      updatedCount++
    }
    
    ElMessage.success(`保存成功！新建 ${createdCount} 个，更新 ${updatedCount} 个`)
    await loadExistingTasks()
    
  } catch (error) {
    ElMessage.error('保存失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  loadBasicData()
})
</script>

<style lang="scss" scoped>
.teaching-plan { padding: 24px; }
.toolbar { display: flex; justify-content: space-between; margin-bottom: 24px; }

.plan-table-wrapper {
  background: #fff; border-radius: 12px; overflow: hidden;
  :deep(.el-table) { --el-table-border-color: #e2e8f0; }
}

.subject-cell {
  display: flex; align-items: center; gap: 8px;
  .subject-dot { width: 8px; height: 8px; border-radius: 50%; }
}

.plan-summary {
  display: flex; gap: 32px; margin-top: 20px; padding: 16px 20px;
  background: #fff; border-radius: 12px;
  .summary-item {
    .label { color: var(--text-secondary); margin-right: 8px; }
    .value { font-size: 18px; font-weight: 600; color: var(--primary-color); }
  }
}
</style>
