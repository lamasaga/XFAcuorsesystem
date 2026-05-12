<template>
  <div class="subject-management">
    <!-- 工具栏 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <el-input
          v-model="searchQuery"
          placeholder="搜索科目名称"
          clearable
          style="width: 220px"
          @keyup.enter="loadSubjects"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-select v-model="filterExamBoard" placeholder="考试局" clearable style="width: 130px" @change="loadSubjects">
          <el-option label="CAIE" value="CAIE" />
          <el-option label="Edexcel" value="Edexcel" />
          <el-option label="AQA" value="AQA" />
        </el-select>
        <el-select v-model="filterLevel" placeholder="级别" clearable style="width: 110px" @change="loadSubjects">
          <el-option label="AS" value="AS" />
          <el-option label="A2" value="A2" />
        </el-select>
      </div>
      <div class="toolbar-right">
        <el-button @click="showImportDialog = true">
          <el-icon><Upload /></el-icon>导入
        </el-button>
        <el-button type="primary" @click="showAddDialog = true">
          <el-icon><Plus /></el-icon>添加科目
        </el-button>
      </div>
    </div>
    
    <!-- 数据表格 -->
    <el-table :data="subjects" stripe v-loading="loading" style="width: 100%">
      <el-table-column type="index" width="50" />
      <el-table-column prop="name" label="科目名称" min-width="160" />
      <el-table-column prop="examBoard" label="考试局" width="110">
        <template #default="{ row }">
          <el-tag size="small">{{ row.examBoard }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="level" label="级别" width="90">
        <template #default="{ row }">
          <el-tag :type="row.level === 'AS' ? 'primary' : 'success'" size="small">{{ row.level }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="moduleCode" label="模块代码" width="120">
        <template #default="{ row }">
          <span class="code-text">{{ row.moduleCode || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="weeklyHours" label="周课时" width="90" align="center" />
      <el-table-column prop="maxStudents" label="容量" width="90" align="center" />
      <el-table-column prop="isActive" label="状态" width="90" align="center">
        <template #default="{ row }">
          <el-tag :type="row.isActive ? 'success' : 'info'" size="small">
            {{ row.isActive ? '启用' : '停用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link @click="editSubject(row)">编辑</el-button>
          <el-popconfirm title="确定删除该科目吗？" @confirm="deleteSubject(row)">
            <template #reference><el-button type="danger" link>删除</el-button></template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>
    
    <!-- 分页 -->
    <div class="pagination-wrapper">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :total="totalCount"
        layout="total, sizes, prev, pager, next"
        @change="loadSubjects"
      />
    </div>
    
    <!-- 导入对话框 -->
    <ExcelImportDialog
      v-model="showImportDialog"
      title="导入 A-Level 科目数据"
      :template-url="getAlevelSubjectImportTemplateUrl('xlsx')"
      :import-api="importAlevelSubjectsFile"
      @success="loadSubjects"
    />

    <!-- 添加/编辑对话框 -->
    <el-dialog
      v-model="showAddDialog"
      :title="editingSubject ? '编辑科目' : '添加科目'"
      width="600px"
      destroy-on-close
    >
      <el-form :model="subjectForm" label-width="100px" :rules="formRules" ref="formRef">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="科目名称" prop="name">
              <el-input v-model="subjectForm.name" placeholder="如：数学、物理" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="模块代码">
              <el-input v-model="subjectForm.moduleCode" placeholder="如 9702/12" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="考试局" prop="examBoard">
              <el-select v-model="subjectForm.examBoard" style="width: 100%">
                <el-option label="CAIE" value="CAIE" />
                <el-option label="Edexcel" value="Edexcel" />
                <el-option label="AQA" value="AQA" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="级别" prop="level">
              <el-select v-model="subjectForm.level" style="width: 100%">
                <el-option label="AS" value="AS" />
                <el-option label="A2" value="A2" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="周课时" prop="weeklyHours">
              <el-input-number v-model="subjectForm.weeklyHours" :min="1" :max="20" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="最大容量" prop="maxStudents">
              <el-input-number v-model="subjectForm.maxStudents" :min="1" :max="100" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="关联科目">
          <el-select v-model="subjectForm.subjectId" placeholder="选择基础科目（可选）" clearable style="width: 100%">
            <el-option v-for="s in baseSubjects" :key="s.id" :label="s.name" :value="s.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="科目描述">
          <el-input v-model="subjectForm.description" type="textarea" :rows="3" placeholder="科目描述（可选）" />
        </el-form-item>
        <el-form-item label="启用状态">
          <el-switch v-model="subjectForm.isActive" active-text="启用" inactive-text="停用" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="saveSubject">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Plus, Upload } from '@element-plus/icons-vue'
import { getAlevelSubjects, createAlevelSubject, updateAlevelSubject, deleteAlevelSubject as deleteAlevelSubjectApi, getAlevelSubjectImportTemplateUrl, importAlevelSubjectsFile } from '@/api/alevelSubjects'
import { getSubjects } from '@/api/subjects'
import ExcelImportDialog from '@/components/ExcelImportDialog.vue'

const loading = ref(false)
const subjects = ref([])
const searchQuery = ref('')
const filterExamBoard = ref('')
const filterLevel = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const totalCount = ref(0)
const useMockData = ref(false)

const showAddDialog = ref(false)
const showImportDialog = ref(false)
const editingSubject = ref(null)
const formRef = ref(null)
const baseSubjects = ref([])

const subjectForm = ref({
  name: '',
  moduleCode: '',
  examBoard: 'CAIE',
  level: 'AS',
  weeklyHours: 4,
  maxStudents: 20,
  subjectId: null,
  description: '',
  isActive: true
})

const formRules = {
  name: [{ required: true, message: '请输入科目名称', trigger: 'blur' }],
  examBoard: [{ required: true, message: '请选择考试局', trigger: 'change' }],
  level: [{ required: true, message: '请选择级别', trigger: 'change' }]
}

const mockSubjects = [
  { id: 1, name: '数学', examBoard: 'CAIE', level: 'AS', moduleCode: '9709/12', weeklyHours: 5, maxStudents: 20, isActive: true },
  { id: 2, name: '物理', examBoard: 'CAIE', level: 'AS', moduleCode: '9702/12', weeklyHours: 5, maxStudents: 18, isActive: true },
  { id: 3, name: '化学', examBoard: 'Edexcel', level: 'A2', moduleCode: 'WCH15', weeklyHours: 5, maxStudents: 16, isActive: true },
  { id: 4, name: '经济', examBoard: 'CAIE', level: 'AS', moduleCode: '9708/12', weeklyHours: 4, maxStudents: 22, isActive: false }
]

const loadBaseSubjects = async () => {
  try {
    const res = await getSubjects({ page: 1, page_size: 200 })
    baseSubjects.value = res.data?.items || []
  } catch (e) {
    console.warn('加载基础科目失败:', e)
  }
}

const loadSubjects = async () => {
  loading.value = true
  try {
    const res = await getAlevelSubjects({
      page: currentPage.value,
      page_size: pageSize.value,
      exam_board: filterExamBoard.value || undefined,
      level: filterLevel.value || undefined,
      search: searchQuery.value || undefined
    })
    useMockData.value = false
    const items = res.data?.items || []
    subjects.value = items.map(s => ({
      ...s,
      examBoard: s.exam_board,
      moduleCode: s.module_code,
      weeklyHours: s.weekly_hours,
      maxStudents: s.max_students,
      subjectId: s.subject_id,
      isActive: s.is_active
    }))
    totalCount.value = res.data?.total || 0
  } catch (error) {
    console.warn('后端 API 未启动，使用 Mock 数据')
    useMockData.value = true
    let filtered = [...mockSubjects]
    if (filterExamBoard.value) filtered = filtered.filter(s => s.examBoard === filterExamBoard.value)
    if (filterLevel.value) filtered = filtered.filter(s => s.level === filterLevel.value)
    if (searchQuery.value) {
      const q = searchQuery.value.toLowerCase()
      filtered = filtered.filter(s => s.name.toLowerCase().includes(q))
    }
    subjects.value = filtered
    totalCount.value = filtered.length
  } finally {
    loading.value = false
  }
}

const editSubject = (row) => {
  editingSubject.value = row
  subjectForm.value = {
    name: row.name,
    moduleCode: row.moduleCode || '',
    examBoard: row.examBoard,
    level: row.level,
    weeklyHours: row.weeklyHours,
    maxStudents: row.maxStudents,
    subjectId: row.subjectId || null,
    description: row.description || '',
    isActive: row.isActive
  }
  showAddDialog.value = true
}

const saveSubject = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  
  const submitData = {
    name: subjectForm.value.name,
    module_code: subjectForm.value.moduleCode || null,
    exam_board: subjectForm.value.examBoard,
    level: subjectForm.value.level,
    weekly_hours: subjectForm.value.weeklyHours,
    max_students: subjectForm.value.maxStudents,
    subject_id: subjectForm.value.subjectId || null,
    description: subjectForm.value.description || null,
    is_active: subjectForm.value.isActive
  }
  
  try {
    if (editingSubject.value) {
      if (!useMockData.value) await updateAlevelSubject(editingSubject.value.id, submitData)
      const idx = subjects.value.findIndex(s => s.id === editingSubject.value.id)
      if (idx !== -1) subjects.value[idx] = { ...subjects.value[idx], ...subjectForm.value }
      ElMessage.success('更新成功')
    } else {
      if (!useMockData.value) {
        const res = await createAlevelSubject(submitData)
        subjects.value.unshift({
          ...res.data,
          examBoard: res.data.exam_board,
          moduleCode: res.data.module_code,
          weeklyHours: res.data.weekly_hours,
          maxStudents: res.data.max_students,
          isActive: res.data.is_active
        })
      } else {
        subjects.value.unshift({ id: Date.now(), ...subjectForm.value })
      }
      ElMessage.success('创建成功')
    }
    showAddDialog.value = false
    editingSubject.value = null
    resetForm()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '操作失败')
  }
}

const deleteSubject = async (row) => {
  try {
    if (!useMockData.value) await deleteAlevelSubjectApi(row.id)
    subjects.value = subjects.value.filter(s => s.id !== row.id)
    ElMessage.success('删除成功')
  } catch (error) {
    ElMessage.error('删除失败')
  }
}

const resetForm = () => {
  subjectForm.value = {
    name: '', moduleCode: '', examBoard: 'CAIE', level: 'AS',
    weeklyHours: 4, maxStudents: 20, subjectId: null, description: '', isActive: true
  }
}

onMounted(() => {
  loadBaseSubjects()
  loadSubjects()
})
</script>

<style lang="scss" scoped>
.subject-management { padding: 20px; }
.toolbar {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 16px; gap: 12px; flex-wrap: wrap;
}
.toolbar-left { display: flex; gap: 12px; align-items: center; }
.pagination-wrapper {
  display: flex; justify-content: flex-end;
  margin-top: 16px; padding-top: 16px; border-top: 1px solid var(--border-color);
}
.code-text { font-family: monospace; color: var(--text-secondary); font-size: 13px; }
</style>
