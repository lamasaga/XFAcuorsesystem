<template>
  <div class="export-page">
    <div class="page-header">
      <div class="page-title">
        <h1>导出课表</h1>
        <span class="subtitle">将课表导出为多种格式</span>
      </div>
    </div>
    
    <div class="export-container">
      <div class="export-options card">
        <h3>导出设置</h3>
        
        <el-form label-width="100px" class="export-form">
          <el-form-item label="选择课表">
            <el-select v-model="selectedScheduleId" placeholder="选择要导出的课表" style="width: 100%">
              <el-option 
                v-for="s in scheduleList" 
                :key="s.id" 
                :label="s.name + (s.is_active ? ' (当前激活)' : '')" 
                :value="s.id" 
              />
            </el-select>
          </el-form-item>
          
          <el-form-item label="导出范围">
            <el-radio-group v-model="exportOptions.scope">
              <el-radio value="all">全部班级</el-radio>
              <el-radio value="class">指定班级</el-radio>
              <el-radio value="teacher">指定教师</el-radio>
            </el-radio-group>
          </el-form-item>
          
          <el-form-item v-if="exportOptions.scope === 'class'" label="选择班级">
            <el-select v-model="exportOptions.targetClass" placeholder="选择班级">
              <el-option v-for="c in classList" :key="c.id" :label="c.name" :value="c.id" />
            </el-select>
          </el-form-item>
          
          <el-form-item v-if="exportOptions.scope === 'teacher'" label="选择教师">
            <el-select v-model="exportOptions.targetTeacher" placeholder="选择教师">
              <el-option v-for="t in teacherList" :key="t.id" :label="t.name" :value="t.id" />
            </el-select>
          </el-form-item>
          
          <el-divider />
          
          <el-form-item label="导出格式">
            <div class="format-options">
              <div 
                v-for="format in formatOptions" 
                :key="format.key"
                class="format-card"
                :class="{ selected: exportOptions.format === format.key, disabled: !format.supported }"
                @click="format.supported && (exportOptions.format = format.key)"
              >
                <el-icon class="format-icon" :style="{ color: format.color }">
                  <component :is="format.icon" />
                </el-icon>
                <div class="format-info">
                  <div class="format-name">{{ format.name }}</div>
                  <div class="format-ext">{{ format.ext }}</div>
                </div>
                <el-tag v-if="!format.supported" size="small" type="info">开发中</el-tag>
                <el-icon v-else-if="exportOptions.format === format.key" class="check-icon"><CircleCheck /></el-icon>
              </div>
            </div>
          </el-form-item>
          
          <el-divider />
          
          <el-form-item label="导出选项">
            <div class="extra-options">
              <el-checkbox v-model="exportOptions.includeTeacher">包含教师姓名</el-checkbox>
              <el-checkbox v-model="exportOptions.includeTime">包含上课时间</el-checkbox>
            </div>
          </el-form-item>
        </el-form>
        
        <div class="export-actions">
          <el-button @click="loadPreview" :loading="previewLoading">
            <el-icon><View /></el-icon>
            刷新预览
          </el-button>
          <el-button type="primary" @click="startExport" :loading="exporting" :disabled="!selectedScheduleId">
            <el-icon><Download /></el-icon>
            {{ exporting ? '导出中...' : '开始导出' }}
          </el-button>
        </div>
      </div>
      
      <div class="export-preview card">
        <h3>预览</h3>
        <div class="preview-content" v-loading="previewLoading">
          <div class="preview-timetable">
            <div class="preview-header">
              <span class="preview-title">{{ previewTitle }}</span>
            </div>
            <table class="preview-table" v-if="Object.keys(previewData).length > 0">
              <thead>
                <tr>
                  <th>时间</th>
                  <th>周一</th>
                  <th>周二</th>
                  <th>周三</th>
                  <th>周四</th>
                  <th>周五</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="period in 8" :key="period">
                  <td class="time-cell">第{{ period }}节</td>
                  <td v-for="day in 5" :key="day" class="schedule-cell">
                    <span class="subject">{{ getPreviewCell(period, day).subject }}</span>
                    <span class="teacher" v-if="exportOptions.includeTeacher">{{ getPreviewCell(period, day).teacher }}</span>
                  </td>
                </tr>
              </tbody>
            </table>
            <el-empty v-else description="请选择课表和目标后点击刷新预览" />
          </div>
        </div>
      </div>
    </div>
    
    <!-- 导出成功对话框 -->
    <el-dialog v-model="showSuccessDialog" title="导出成功" width="400px" center>
      <div class="success-content">
        <el-icon class="success-icon"><CircleCheck /></el-icon>
        <p class="success-text">课表已成功导出</p>
        <p class="success-hint">文件已下载到您的浏览器默认下载目录</p>
      </div>
      <template #footer>
        <el-button type="primary" @click="showSuccessDialog = false">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Download, View, CircleCheck, Document, Grid, Picture, Link } from '@element-plus/icons-vue'
import { getScheduleList, getScheduleDetail, getClassTimetable, getTeacherTimetable } from '@/api/schedules'
import { getClasses } from '@/api/classes'
import { getTeachers } from '@/api/teachers'

// 数据
const scheduleList = ref([])
const classList = ref([])
const teacherList = ref([])
const selectedScheduleId = ref(null)

const exportOptions = ref({
  scope: 'class',
  targetClass: null,
  targetTeacher: null,
  format: 'xlsx',
  includeTeacher: true,
  includeTime: true
})

const formatOptions = [
  { key: 'xlsx', name: 'Excel 文件', ext: '.xlsx', icon: 'Grid', color: '#16a34a', supported: true },
  { key: 'csv', name: 'CSV 文件', ext: '.csv', icon: 'Document', color: '#2563eb', supported: true },
  { key: 'pdf', name: 'PDF 文件', ext: '.pdf', icon: 'Document', color: '#dc2626', supported: false },
  { key: 'html', name: '网页文件', ext: '.html', icon: 'Link', color: '#7c3aed', supported: false }
]

// 预览数据
const previewData = ref({})
const previewLoading = ref(false)

const previewTitle = computed(() => {
  if (exportOptions.value.scope === 'all') return '全部班级课表'
  if (exportOptions.value.scope === 'class') {
    const cls = classList.value.find(c => c.id === exportOptions.value.targetClass)
    return cls ? `${cls.name} 课表` : '班级课表'
  }
  if (exportOptions.value.scope === 'teacher') {
    const teacher = teacherList.value.find(t => t.id === exportOptions.value.targetTeacher)
    return teacher ? `${teacher.name} 课表` : '教师课表'
  }
  return '课表预览'
})

const getPreviewCell = (period, day) => {
  const key = `${day}-${period}`
  return previewData.value[key] || { subject: '', teacher: '' }
}

// 加载基础数据
const loadBasicData = async () => {
  try {
    const [schedulesRes, classesRes, teachersRes] = await Promise.all([
      getScheduleList(),
      getClasses({ page: 1, page_size: 200 }),
      getTeachers({ page: 1, page_size: 200 })
    ])
    
    scheduleList.value = schedulesRes.data.items || []
    classList.value = classesRes.data.items || []
    teacherList.value = teachersRes.data.items || []
    
    // 默认选择激活的课表
    const activeSchedule = scheduleList.value.find(s => s.is_active)
    if (activeSchedule) {
      selectedScheduleId.value = activeSchedule.id
    } else if (scheduleList.value.length > 0) {
      selectedScheduleId.value = scheduleList.value[0].id
    }
    
    // 默认选择第一个班级
    if (classList.value.length > 0) {
      exportOptions.value.targetClass = classList.value[0].id
    }
    if (teacherList.value.length > 0) {
      exportOptions.value.targetTeacher = teacherList.value[0].id
    }
  } catch (error) {
    console.error('加载基础数据失败:', error)
    ElMessage.error('加载数据失败')
  }
}

// 加载预览数据
const loadPreview = async () => {
  if (!selectedScheduleId.value) {
    ElMessage.warning('请先选择课表')
    return
  }
  
  previewLoading.value = true
  try {
    let res
    if (exportOptions.value.scope === 'class' && exportOptions.value.targetClass) {
      res = await getClassTimetable(selectedScheduleId.value, exportOptions.value.targetClass)
    } else if (exportOptions.value.scope === 'teacher' && exportOptions.value.targetTeacher) {
      res = await getTeacherTimetable(selectedScheduleId.value, exportOptions.value.targetTeacher)
    } else {
      // 全部班级模式，先获取第一个班级的数据作为预览
      if (classList.value.length > 0) {
        res = await getClassTimetable(selectedScheduleId.value, classList.value[0].id)
      }
    }
    
    if (res && res.data && res.data.timetable) {
      previewData.value = {}
      for (const [key, value] of Object.entries(res.data.timetable)) {
        previewData.value[key] = {
          subject: value.subject_name || '',
          teacher: value.teacher_name || value.class_name || ''
        }
      }
    } else {
      previewData.value = {}
    }
  } catch (error) {
    console.error('加载预览失败:', error)
    previewData.value = {}
  } finally {
    previewLoading.value = false
  }
}

// 监听选择变化自动加载预览
watch([selectedScheduleId, () => exportOptions.value.scope, () => exportOptions.value.targetClass, () => exportOptions.value.targetTeacher], () => {
  if (selectedScheduleId.value) {
    loadPreview()
  }
})

// 导出相关
const exporting = ref(false)
const showSuccessDialog = ref(false)

const startExport = async () => {
  if (!selectedScheduleId.value) {
    ElMessage.warning('请先选择课表')
    return
  }
  
  exporting.value = true
  try {
    // 获取完整的课表数据
    const res = await getScheduleDetail(selectedScheduleId.value)
    const items = res.data.items || []
    
    if (items.length === 0) {
      ElMessage.warning('课表没有数据')
      return
    }
    
    // 根据导出范围过滤数据
    let filteredItems = items
    let filename = '课表'
    
    if (exportOptions.value.scope === 'class' && exportOptions.value.targetClass) {
      filteredItems = items.filter(item => item.class_id === exportOptions.value.targetClass)
      const cls = classList.value.find(c => c.id === exportOptions.value.targetClass)
      filename = cls ? cls.name : '班级课表'
    } else if (exportOptions.value.scope === 'teacher' && exportOptions.value.targetTeacher) {
      filteredItems = items.filter(item => item.teacher_id === exportOptions.value.targetTeacher)
      const teacher = teacherList.value.find(t => t.id === exportOptions.value.targetTeacher)
      filename = teacher ? teacher.name + '老师' : '教师课表'
    }
    
    // 生成导出文件
    if (exportOptions.value.format === 'xlsx' || exportOptions.value.format === 'csv') {
      exportToFile(filteredItems, filename, exportOptions.value.format)
    }
    
    showSuccessDialog.value = true
  } catch (error) {
    console.error('导出失败:', error)
    ElMessage.error('导出失败: ' + error.message)
  } finally {
    exporting.value = false
  }
}

// 导出为文件
const exportToFile = (items, filename, format) => {
  // 构建课表矩阵
  const weekDays = ['周一', '周二', '周三', '周四', '周五']
  const periods = ['第1节', '第2节', '第3节', '第4节', '第5节', '第6节', '第7节', '第8节']
  
  // 按班级分组
  const classTimetables = {}
  for (const item of items) {
    const classId = item.class_id
    if (!classTimetables[classId]) {
      classTimetables[classId] = {
        className: item.class_name,
        data: {}
      }
    }
    const key = `${item.day}-${item.period}`
    classTimetables[classId].data[key] = {
      subject: item.subject_name,
      teacher: item.teacher_name
    }
  }
  
  // 生成 CSV 内容
  let csvContent = ''
  
  for (const [classId, timetable] of Object.entries(classTimetables)) {
    csvContent += `\n${timetable.className}\n`
    csvContent += '时间,' + weekDays.join(',') + '\n'
    
    for (let p = 1; p <= 8; p++) {
      const row = [periods[p-1]]
      for (let d = 1; d <= 5; d++) {
        const cell = timetable.data[`${d}-${p}`]
        if (cell) {
          let cellValue = cell.subject
          if (exportOptions.value.includeTeacher && cell.teacher) {
            cellValue += `(${cell.teacher})`
          }
          row.push(cellValue)
        } else {
          row.push('')
        }
      }
      csvContent += row.join(',') + '\n'
    }
    csvContent += '\n'
  }
  
  // 处理中文编码
  const BOM = '\uFEFF'
  const blob = new Blob([BOM + csvContent], { type: 'text/csv;charset=utf-8;' })
  
  // 下载文件
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = `${filename}_${new Date().toLocaleDateString().replace(/\//g, '-')}.csv`
  link.click()
  URL.revokeObjectURL(link.href)
}

// 初始化
onMounted(async () => {
  await loadBasicData()
  if (selectedScheduleId.value) {
    loadPreview()
  }
})
</script>

<style lang="scss" scoped>
.export-page { max-width: 1200px; margin: 0 auto; }

.page-header {
  margin-bottom: 24px;
  h1 { font-size: 24px; font-weight: 600; }
  .subtitle { font-size: 14px; color: var(--text-secondary); margin-left: 12px; }
}

.export-container { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }

.export-options {
  padding: 24px;
  h3 { font-size: 16px; font-weight: 600; margin-bottom: 20px; padding-bottom: 12px; border-bottom: 1px solid var(--border-color); }
}

.format-options { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }

.format-card {
  display: flex; align-items: center; gap: 12px;
  padding: 12px; border: 2px solid var(--border-color); border-radius: 10px;
  cursor: pointer; transition: all 0.2s ease;
  &:hover:not(.disabled) { border-color: var(--primary-light); }
  &.selected { border-color: var(--primary-color); background: #f0f7ff; }
  &.disabled { opacity: 0.6; cursor: not-allowed; }
  .format-icon { font-size: 28px; }
  .format-info { flex: 1; .format-name { font-weight: 600; font-size: 14px; } .format-ext { font-size: 12px; color: var(--text-muted); } }
  .check-icon { color: var(--primary-color); font-size: 20px; }
}

.extra-options { display: flex; flex-direction: column; gap: 12px; }

.export-actions { display: flex; justify-content: flex-end; gap: 12px; margin-top: 24px; padding-top: 20px; border-top: 1px solid var(--border-color); }

.export-preview {
  padding: 24px;
  h3 { font-size: 16px; font-weight: 600; margin-bottom: 20px; padding-bottom: 12px; border-bottom: 1px solid var(--border-color); }
}

.preview-content {
  .preview-header { margin-bottom: 16px; .preview-title { font-size: 15px; font-weight: 600; } }
}

.preview-table {
  width: 100%; border-collapse: collapse; font-size: 12px;
  th, td { border: 1px solid var(--border-color); padding: 8px; text-align: center; }
  th { background: var(--bg-color); font-weight: 600; }
  .time-cell { background: var(--bg-color); width: 60px; }
  .schedule-cell {
    .subject { display: block; font-weight: 500; }
    .teacher { display: block; font-size: 11px; color: var(--text-muted); }
  }
}

.success-content {
  text-align: center; padding: 20px;
  .success-icon { font-size: 64px; color: #16a34a; margin-bottom: 16px; }
  .success-text { font-size: 16px; font-weight: 600; margin-bottom: 8px; }
  .success-hint { font-size: 14px; color: var(--text-secondary); }
}

@media (max-width: 900px) {
  .export-container { grid-template-columns: 1fr; }
  .format-options { grid-template-columns: 1fr; }
}
</style>
