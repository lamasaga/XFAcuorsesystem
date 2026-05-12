<template>
  <div class="subject-management">
    <div class="toolbar">
      <div class="toolbar-left">
        <el-input v-model="searchQuery" placeholder="搜索科目" prefix-icon="Search" clearable style="width: 200px" />
      </div>
      <div class="toolbar-right">
        <el-button type="primary" @click="openAddDialog"><el-icon><Plus /></el-icon>添加科目</el-button>
      </div>
    </div>
    
    <div class="subjects-grid">
      <div v-for="subject in filteredSubjects" :key="subject.id" class="subject-card" :style="{ '--subject-color': subject.color }">
        <div class="subject-icon">
          <el-icon><component :is="subject.icon" /></el-icon>
        </div>
        <div class="subject-info">
          <div class="subject-name">{{ subject.name }}</div>
          <div class="subject-meta">
            <span>{{ subject.category || '文化课' }}</span>
            <span v-if="subject.required_room_type">• {{ subject.required_room_type }}</span>
          </div>
          <div class="subject-scope" v-if="getSubjectScope(subject)">
            <span class="scope-text">{{ getSubjectScope(subject) }}</span>
          </div>
        </div>
        <div class="subject-tags">
          <el-tag v-if="subject.isMain" type="danger" size="small">主科</el-tag>
          <el-tag v-if="subject.needContinuous" type="warning" size="small">连堂</el-tag>
        </div>
        <el-dropdown trigger="click">
          <el-button class="more-btn" link><el-icon><More /></el-icon></el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="editSubject(subject)"><el-icon><Edit /></el-icon>编辑</el-dropdown-item>
              <el-dropdown-item @click="deleteSubject(subject)"><el-icon><Delete /></el-icon>删除</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>
    
    <el-dialog v-model="showAddDialog" :title="editingSubject ? '编辑科目' : '添加科目'" width="600px">
      <el-form :model="subjectForm" label-width="100px">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="科目代码"><el-input v-model="subjectForm.code" placeholder="如 CHINESE（可留空自动生成）" /></el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="科目名称"><el-input v-model="subjectForm.name" placeholder="请输入科目名称" /></el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="科目分类">
              <el-select v-model="subjectForm.category" placeholder="选择分类" style="width: 100%">
                <el-option label="文化课" value="文化课" />
                <el-option label="艺术" value="艺术" />
                <el-option label="体育" value="体育" />
                <el-option label="综合" value="综合" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="教室类型">
              <el-select v-model="subjectForm.requiredRoomType" placeholder="选择所需教室类型（可选）" clearable style="width: 100%">
                <el-option 
                  v-for="type in roomTypes" 
                  :key="type.value" 
                  :label="type.label" 
                  :value="type.value" 
                />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-divider content-position="left">适用范围</el-divider>
        
        <el-form-item label="适用班型">
          <el-checkbox-group v-model="subjectForm.applicableClassTypes">
            <el-checkbox value="INTERNATIONAL">国际班</el-checkbox>
            <el-checkbox value="COMPREHENSIVE">综素班</el-checkbox>
          </el-checkbox-group>
          <div class="form-hint">不选择表示适用于所有班型</div>
        </el-form-item>
        
        <el-form-item label="适用年级">
          <el-checkbox-group v-model="subjectForm.applicableGrades" class="grade-checkbox-group">
            <el-checkbox v-for="g in gradeOptions" :key="g.value" :value="g.value">{{ g.label }}</el-checkbox>
          </el-checkbox-group>
          <div class="form-hint">不选择表示适用于所有年级</div>
        </el-form-item>
        
        <el-divider content-position="left">其他设置</el-divider>
        
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="科目类型">
              <el-checkbox v-model="subjectForm.isMain">主科（优先安排上午）</el-checkbox>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="主题色">
              <el-color-picker v-model="subjectForm.color" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="saveSubject">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
/**
 * 科目管理页面
 * 
 * 功能：
 * - 从后端 API 获取科目数据
 * - 支持搜索、筛选
 * - 支持添加、编辑、删除科目
 */
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, More, Edit, Delete, Reading, Basketball, Headset, Picture, Cpu, Flag } from '@element-plus/icons-vue'
// 导入 API
import { getSubjects, createSubject, updateSubject, deleteSubject as deleteSubjectApi } from '@/api/subjects'
import { getVenues } from '@/api/venues'

const searchQuery = ref('')
const showAddDialog = ref(false)
const editingSubject = ref(null)
const loading = ref(false)
const useMockData = ref(false)

const subjectForm = ref({ 
  code: '',
  name: '', 
  category: '文化课',
  requiredRoomType: '',
  isMain: false, 
  color: '#3b82f6',
  applicableGrades: [],
  applicableClassTypes: []
})

// 年级选项
const gradeOptions = [
  { value: 'PK', label: 'PK' },
  { value: 'KG', label: 'KG' },
  { value: 'G1', label: 'G1' },
  { value: 'G2', label: 'G2' },
  { value: 'G3', label: 'G3' },
  { value: 'G4', label: 'G4' },
  { value: 'G5', label: 'G5' },
  { value: 'G6', label: 'G6' },
  { value: 'G7', label: 'G7' },
  { value: 'G8', label: 'G8' },
  { value: 'G9', label: 'G9' },
  { value: 'G10', label: 'G10' },
  { value: 'G11', label: 'G11' }
]

// 科目数据
const subjects = ref([])

// 教室类型选项（从场地管理动态加载）
const roomTypes = ref([
  { value: '普通教室', label: '普通教室' }  // 默认选项
])

// Mock 数据 - 当后端未启动时使用
const mockSubjects = [
  { id: 1, code: 'CHINESE', name: '语文', category: '文化课', color: '#ef4444', is_main: true },
  { id: 2, code: 'MATH', name: '数学', category: '文化课', color: '#3b82f6', is_main: true },
  { id: 3, code: 'ENGLISH', name: '英语', category: '文化课', color: '#f59e0b', is_main: true },
  { id: 4, code: 'PE', name: '体育', category: '体育', color: '#10b981', is_main: false },
  { id: 5, code: 'MUSIC', name: '音乐', category: '艺术', color: '#8b5cf6', is_main: false },
  { id: 6, code: 'ART', name: '美术', category: '艺术', color: '#ec4899', is_main: false }
]

// 图标映射
const getIcon = (name) => {
  const icons = {
    '语文': 'Reading', '数学': 'Cpu', '英语': 'Flag',
    '体育': 'Basketball', '音乐': 'Headset', '美术': 'Picture'
  }
  return icons[name] || 'Reading'
}

// 获取科目适用范围描述
const getSubjectScope = (subject) => {
  const parts = []
  
  // 班型
  const classTypes = subject.applicable_class_types || []
  if (classTypes.length > 0 && classTypes.length < 2) {
    const typeLabels = { INTERNATIONAL: '国际班', COMPREHENSIVE: '综素班' }
    parts.push(classTypes.map(t => typeLabels[t] || t).join('/'))
  }
  
  // 年级
  const grades = subject.applicable_grades || []
  if (grades.length > 0) {
    if (grades.length <= 3) {
      parts.push(grades.join(', '))
    } else {
      parts.push(`${grades[0]}-${grades[grades.length - 1]}`)
    }
  }
  
  return parts.length > 0 ? parts.join(' · ') : ''
}

/**
 * 从 API 加载科目数据
 */
const loadSubjects = async () => {
  loading.value = true
  try {
    const res = await getSubjects({ page: 1, page_size: 100 })
    
    console.log('科目 API 响应:', res)
    
    useMockData.value = false
    // 转换字段名并添加显示所需的额外字段
    const items = res.data?.items || res.items || []
    console.log('科目数据:', items.length, '个')
    
    subjects.value = items.map(s => ({
      ...s,
      icon: getIcon(s.name),
      isMain: s.is_main
    }))
  } catch (error) {
    console.warn('后端 API 未启动，使用 Mock 数据', error.message)
    useMockData.value = true
    
    subjects.value = mockSubjects.map(s => ({
      ...s,
      icon: getIcon(s.name),
      isMain: s.is_main
    }))
  } finally {
    loading.value = false
  }
}

/**
 * 从场地管理加载教室类型
 */
const loadRoomTypes = async () => {
  try {
    const res = await getVenues({ page: 1, page_size: 100 })
    const venues = res.data?.items || res.items || []
    
    // 提取不重复的场地名称作为教室类型
    const types = new Set(['普通教室'])  // 始终包含普通教室
    venues.forEach(v => {
      if (v.name) types.add(v.name)
    })
    
    roomTypes.value = Array.from(types).map(name => ({
      value: name,
      label: name
    }))
  } catch (error) {
    console.warn('加载场地类型失败，使用默认选项', error.message)
  }
}

// 页面加载时获取数据
onMounted(() => {
  loadSubjects()
  loadRoomTypes()
})

const filteredSubjects = computed(() => {
  if (!searchQuery.value) return subjects.value
  return subjects.value.filter(s => s.name.includes(searchQuery.value))
})

// 打开添加对话框
const openAddDialog = () => {
  editingSubject.value = null
  subjectForm.value = { 
    code: '',
    name: '', 
    category: '文化课',
    requiredRoomType: '',
    isMain: false, 
    color: '#3b82f6',
    applicableGrades: [],
    applicableClassTypes: []
  }
  showAddDialog.value = true
}

// 编辑科目
const editSubject = (subject) => {
  editingSubject.value = subject
  subjectForm.value = {
    code: subject.code,
    name: subject.name,
    category: subject.category || '文化课',
    requiredRoomType: subject.required_room_type || '',
    isMain: subject.isMain || subject.is_main || false,
    color: subject.color || '#3b82f6',
    applicableGrades: subject.applicable_grades || [],
    applicableClassTypes: subject.applicable_class_types || []
  }
  showAddDialog.value = true
}

// 删除科目
const deleteSubject = async (subject) => {
  try {
    await ElMessageBox.confirm(`确定要删除科目 ${subject.name} 吗？`, '确认删除', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    if (!useMockData.value) {
      await deleteSubjectApi(subject.id)
    }
    
    const index = subjects.value.findIndex(s => s.id === subject.id)
    if (index > -1) {
      subjects.value.splice(index, 1)
    }
    
    ElMessage.success('删除成功')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败: ' + (error.message || '未知错误'))
    }
  }
}

// 保存科目
const saveSubject = async () => {
  if (!subjectForm.value.name) {
    ElMessage.warning('请输入科目名称')
    return
  }
  
  // 如果没有填写代码，自动生成
  const code = subjectForm.value.code || subjectForm.value.name.toUpperCase()
  
  const submitData = {
    code,
    name: subjectForm.value.name,
    category: subjectForm.value.category,
    required_room_type: subjectForm.value.requiredRoomType || null,
    is_main: subjectForm.value.isMain,
    color: subjectForm.value.color,
    applicable_grades: subjectForm.value.applicableGrades || [],
    applicable_class_types: subjectForm.value.applicableClassTypes || []
  }
  
  try {
    if (editingSubject.value) {
      if (!useMockData.value) {
        await updateSubject(editingSubject.value.id, submitData)
      }
      
      const index = subjects.value.findIndex(s => s.id === editingSubject.value.id)
      if (index > -1) {
        subjects.value[index] = { 
          ...subjects.value[index], 
          ...submitData,
          isMain: submitData.is_main,
          icon: getIcon(submitData.name)
        }
      }
      ElMessage.success('修改成功')
    } else {
      if (!useMockData.value) {
        const res = await createSubject(submitData)
        subjects.value.push({ 
          ...res.data, 
          isMain: res.data.is_main,
          icon: getIcon(res.data.name)
        })
      } else {
        subjects.value.push({ 
          id: Date.now(), 
          ...submitData, 
          isMain: submitData.is_main,
          icon: getIcon(submitData.name)
        })
      }
      ElMessage.success('添加成功')
    }
    
    showAddDialog.value = false
    editingSubject.value = null
  } catch (error) {
    ElMessage.error('保存失败: ' + (error.message || '未知错误'))
  }
}
</script>

<style lang="scss" scoped>
.subject-management { padding: 24px; }
.toolbar { display: flex; justify-content: space-between; margin-bottom: 24px; }

.subjects-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }

.subject-card {
  display: flex; align-items: center; gap: 12px; padding: 16px 20px;
  background: #fff; border-radius: 12px; border: 1px solid var(--border-color);
  transition: all 0.2s ease; position: relative;
  &:hover { border-color: var(--subject-color); box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08); }
  
  .subject-icon {
    width: 48px; height: 48px; border-radius: 12px;
    background: color-mix(in srgb, var(--subject-color) 15%, transparent);
    display: flex; align-items: center; justify-content: center;
    .el-icon { font-size: 24px; color: var(--subject-color); }
  }
  
  .subject-info {
    flex: 1;
    .subject-name { font-size: 16px; font-weight: 600; color: var(--text-primary); margin-bottom: 4px; }
    .subject-meta { font-size: 12px; color: var(--text-secondary); display: flex; gap: 6px; }
    .subject-scope { 
      font-size: 11px; color: #8b5cf6; margin-top: 4px;
      .scope-text { 
        background: rgba(139, 92, 246, 0.1); 
        padding: 2px 6px; 
        border-radius: 4px; 
      }
    }
  }
  
  .subject-tags { display: flex; gap: 6px; position: absolute; top: 12px; right: 48px; }
  .more-btn { opacity: 0; transition: opacity 0.2s ease; }
  &:hover .more-btn { opacity: 1; }
}

.form-hint {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.grade-checkbox-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  
  :deep(.el-checkbox) {
    margin-right: 0;
  }
}
</style>
