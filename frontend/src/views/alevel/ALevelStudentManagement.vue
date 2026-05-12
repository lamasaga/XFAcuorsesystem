<template>
  <div class="student-management">
    <!-- 工具栏 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <el-input
          v-model="searchQuery"
          placeholder="搜索学生姓名或学号"
          clearable
          style="width: 240px"
          @keyup.enter="loadStudents"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-select v-model="filterGrade" placeholder="年级" clearable style="width: 120px" @change="loadStudents">
          <el-option label="G10" value="G10" />
          <el-option label="G11" value="G11" />
          <el-option label="G12" value="G12" />
        </el-select>
        <el-select v-model="filterStatus" placeholder="状态" clearable style="width: 120px" @change="loadStudents">
          <el-option label="在读" value="ACTIVE" />
          <el-option label="休学" value="INACTIVE" />
          <el-option label="毕业" value="GRADUATED" />
        </el-select>
      </div>
      <div class="toolbar-right">
        <el-button @click="showImportDialog = true">
          <el-icon><Upload /></el-icon>导入
        </el-button>
        <el-button type="warning" @click="openPromoteDialog">
          <el-icon><TopRight /></el-icon>一键升年级
        </el-button>
        <el-button type="primary" @click="showAddDialog = true">
          <el-icon><Plus /></el-icon>添加学生
        </el-button>
      </div>
    </div>
    
    <!-- 数据表格 -->
    <el-table :data="students" stripe v-loading="loading" style="width: 100%">
      <el-table-column type="index" width="50" />
      <el-table-column prop="name" label="姓名" width="120" />
      <el-table-column prop="studentNo" label="学号" width="140" />
      <el-table-column prop="grade" label="年级" width="100">
        <template #default="{ row }">
          <el-tag :type="row.grade === 'G10' ? 'primary' : 'success'" size="small">
            {{ row.grade }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="classId" label="行政班" width="120">
        <template #default="{ row }">
          <span v-if="row.classId">{{ getClassName(row.classId) }}</span>
          <span v-else class="text-muted">未分配</span>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)" size="small">
            {{ statusText(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="createdAt" label="录入时间" width="160">
        <template #default="{ row }">
          {{ formatDate(row.createdAt) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link @click="editStudent(row)">编辑</el-button>
          <el-popconfirm title="确定删除该学生吗？" @confirm="deleteStudent(row)">
            <template #reference>
              <el-button type="danger" link>删除</el-button>
            </template>
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
        @change="loadStudents"
      />
    </div>
    
    <!-- 导入对话框 -->
    <ExcelImportDialog
      v-model="showImportDialog"
      title="导入学生数据"
      :template-url="getStudentImportTemplateUrl('xlsx')"
      :import-api="importStudentsFile"
      @success="loadStudents"
    />

    <!-- 一键升年级对话框 -->
    <el-dialog v-model="showPromoteDialog" title="一键升年级" width="480px">
      <div class="promote-content">
        <el-alert type="warning" :closable="false" show-icon>
          <template #title>
            <span>此操作将把选定年级的在读学生升级到下一年级。G12 学生将标记为毕业。</span>
          </template>
        </el-alert>
        <div class="promote-section">
          <div class="promote-label">选择要升级的年级：</div>
          <el-checkbox-group v-model="promoteGrades" class="promote-grades">
            <el-checkbox v-for="g in promoteGradeOptions" :key="g.key" :value="g.key" :label="g.name" />
          </el-checkbox-group>
          <div class="promote-hint">留空则默认升级所有非毕业在读年级</div>
        </div>
        <div class="promote-preview" v-if="promotePreview.length > 0">
          <div class="promote-label">影响学生预览：</div>
          <el-table :data="promotePreview" size="small" max-height="200">
            <el-table-column prop="grade" label="当前年级" width="100" />
            <el-table-column prop="count" label="人数" width="80" />
            <el-table-column prop="newGrade" label="升级后" width="100" />
          </el-table>
        </div>
        <div class="promote-empty" v-else>
          <el-empty description="未选择年级或该年级暂无在读学生" :image-size="80" />
        </div>
      </div>
      <template #footer>
        <el-button @click="showPromoteDialog = false">取消</el-button>
        <el-button type="warning" @click="executePromote" :disabled="promotePreview.length === 0">
          确认升级
        </el-button>
      </template>
    </el-dialog>

    <!-- 添加/编辑对话框 -->
    <el-dialog
      v-model="showAddDialog"
      :title="editingStudent ? '编辑学生' : '添加学生'"
      width="550px"
      destroy-on-close
    >
      <el-form :model="studentForm" label-width="100px" :rules="formRules" ref="formRef">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="姓名" prop="name">
              <el-input v-model="studentForm.name" placeholder="请输入学生姓名" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="学号" prop="studentNo">
              <el-input v-model="studentForm.studentNo" placeholder="请输入学号" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="年级" prop="grade">
              <el-select v-model="studentForm.grade" placeholder="选择年级" style="width: 100%">
                <el-option label="G10" value="G10" />
                <el-option label="G11" value="G11" />
                <el-option label="G12" value="G12" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="行政班">
              <el-select v-model="studentForm.classId" placeholder="选择行政班" clearable style="width: 100%">
                <el-option 
                  v-for="cls in classList" 
                  :key="cls.id" 
                  :label="cls.name" 
                  :value="cls.id" 
                />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="状态">
          <el-radio-group v-model="studentForm.status">
            <el-radio label="ACTIVE">在读</el-radio>
            <el-radio label="INACTIVE">休学</el-radio>
            <el-radio label="GRADUATED">毕业</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="saveStudent">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Plus, Upload, TopRight } from '@element-plus/icons-vue'
import { getStudents, createStudent, updateStudent, deleteStudent as deleteStudentApi, getStudentImportTemplateUrl, importStudentsFile, promoteStudents } from '@/api/students'
import { getClasses } from '@/api/classes'
import ExcelImportDialog from '@/components/ExcelImportDialog.vue'

const loading = ref(false)
const students = ref([])
const searchQuery = ref('')
const filterGrade = ref('')
const filterStatus = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const totalCount = ref(0)
const useMockData = ref(false)

const showAddDialog = ref(false)
const showImportDialog = ref(false)
const showPromoteDialog = ref(false)
const editingStudent = ref(null)
const formRef = ref(null)
const classList = ref([])

// 一键升年级
const promoteGrades = ref([])
const promoteGradeOptions = [
  { key: 'G10', name: 'G10 (十年级)' },
  { key: 'G11', name: 'G11 (十一年级)' },
  { key: 'G12', name: 'G12 (十二年级/毕业)' },
]
const STUDENT_GRADE_NEXT = { G10: 'G11', G11: 'G12' }

const promotePreview = computed(() => {
  const grades = promoteGrades.value.length > 0 ? promoteGrades.value : ['G10']
  const preview = []
  for (const grade of grades) {
    const count = students.value.filter(s => s.grade === grade && s.status === 'ACTIVE').length
    if (count > 0) {
      preview.push({
        grade,
        count,
        newGrade: grade === 'G12' ? 'GRADUATED' : (STUDENT_GRADE_NEXT[grade] || '-')
      })
    }
  }
  return preview
})

const openPromoteDialog = () => {
  promoteGrades.value = []
  showPromoteDialog.value = true
}

const executePromote = async () => {
  try {
    const totalCount = promotePreview.value.reduce((sum, p) => sum + p.count, 0)
    await ElMessageBox.confirm(
      `确定要升级 ${totalCount} 名学生的年级吗？此操作不可撤销。`,
      '确认升级',
      { confirmButtonText: '确定升级', cancelButtonText: '取消', type: 'warning' }
    )
    const payload = promoteGrades.value.length > 0 ? { grades: promoteGrades.value } : {}
    const res = await promoteStudents(payload)
    ElMessage.success(res.message || '升年级成功')
    showPromoteDialog.value = false
    await loadStudents()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(e.response?.data?.detail || e.message || '操作失败')
    }
  }
}

const studentForm = ref({
  name: '',
  studentNo: '',
  grade: 'G10',
  classId: null,
  status: 'ACTIVE'
})

const formRules = {
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  studentNo: [{ required: true, message: '请输入学号', trigger: 'blur' }],
  grade: [{ required: true, message: '请选择年级', trigger: 'change' }]
}

const mockStudents = [
  { id: 1, name: '张三', studentNo: '20251001', grade: 'G10', classId: null, status: 'ACTIVE', createdAt: '2025-01-15T08:00:00' },
  { id: 2, name: '李四', studentNo: '20251002', grade: 'G10', classId: null, status: 'ACTIVE', createdAt: '2025-01-15T08:00:00' },
  { id: 3, name: '王五', studentNo: '20241101', grade: 'G11', classId: null, status: 'ACTIVE', createdAt: '2024-09-01T08:00:00' }
]

const statusType = (status) => {
  const map = { ACTIVE: 'success', INACTIVE: 'warning', GRADUATED: 'info' }
  return map[status] || 'info'
}

const statusText = (status) => {
  const map = { ACTIVE: '在读', INACTIVE: '休学', GRADUATED: '毕业' }
  return map[status] || status
}

const getClassName = (classId) => {
  const cls = classList.value.find(c => c.id === classId)
  return cls ? cls.name : classId
}

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  return d.toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

const loadClasses = async () => {
  try {
    const res = await getClasses({ page: 1, page_size: 200 })
    const items = res.data?.items || []
    classList.value = items.filter(c => c.grade === 'G10' || c.grade === 'G11' || c.grade === 'G12')
  } catch (e) {
    console.warn('加载班级失败:', e)
  }
}

const loadStudents = async () => {
  loading.value = true
  try {
    const res = await getStudents({
      page: currentPage.value,
      page_size: pageSize.value,
      grade: filterGrade.value || undefined,
      status: filterStatus.value || undefined,
      search: searchQuery.value || undefined
    })
    useMockData.value = false
    const items = res.data?.items || []
    students.value = items.map(s => ({
      ...s,
      studentNo: s.student_no,
      classId: s.class_id,
      createdAt: s.created_at,
      updatedAt: s.updated_at
    }))
    totalCount.value = res.data?.total || 0
  } catch (error) {
    console.warn('后端 API 未启动，使用 Mock 数据')
    useMockData.value = true
    let filtered = [...mockStudents]
    if (filterGrade.value) filtered = filtered.filter(s => s.grade === filterGrade.value)
    if (filterStatus.value) filtered = filtered.filter(s => s.status === filterStatus.value)
    if (searchQuery.value) {
      const q = searchQuery.value.toLowerCase()
      filtered = filtered.filter(s => s.name.toLowerCase().includes(q) || s.studentNo.includes(q))
    }
    students.value = filtered
    totalCount.value = filtered.length
  } finally {
    loading.value = false
  }
}

const editStudent = (row) => {
  editingStudent.value = row
  studentForm.value = {
    name: row.name,
    studentNo: row.studentNo,
    grade: row.grade,
    classId: row.classId || null,
    status: row.status
  }
  showAddDialog.value = true
}

const saveStudent = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  
  const submitData = {
    name: studentForm.value.name,
    student_no: studentForm.value.studentNo,
    grade: studentForm.value.grade,
    class_id: studentForm.value.classId,
    status: studentForm.value.status
  }
  
  try {
    if (editingStudent.value) {
      if (!useMockData.value) {
        await updateStudent(editingStudent.value.id, submitData)
      }
      const idx = students.value.findIndex(s => s.id === editingStudent.value.id)
      if (idx !== -1) {
        students.value[idx] = { ...students.value[idx], ...studentForm.value }
      }
      ElMessage.success('更新成功')
    } else {
      if (!useMockData.value) {
        const res = await createStudent(submitData)
        const newStudent = {
          ...res.data,
          studentNo: res.data.student_no,
          classId: res.data.class_id,
          createdAt: res.data.created_at
        }
        students.value.unshift(newStudent)
      } else {
        students.value.unshift({
          id: Date.now(),
          ...studentForm.value,
          createdAt: new Date().toISOString()
        })
      }
      ElMessage.success('创建成功')
    }
    showAddDialog.value = false
    editingStudent.value = null
    resetForm()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '操作失败')
  }
}

const deleteStudent = async (row) => {
  try {
    if (!useMockData.value) {
      await deleteStudentApi(row.id)
    }
    students.value = students.value.filter(s => s.id !== row.id)
    ElMessage.success('删除成功')
  } catch (error) {
    ElMessage.error('删除失败')
  }
}

const resetForm = () => {
  studentForm.value = {
    name: '',
    studentNo: '',
    grade: 'G10',
    classId: null,
    status: 'ACTIVE'
  }
}

onMounted(() => {
  loadClasses()
  loadStudents()
})
</script>

<style lang="scss" scoped>
.student-management {
  padding: 20px;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  gap: 12px;
  flex-wrap: wrap;
}

.toolbar-left {
  display: flex;
  gap: 12px;
  align-items: center;
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--border-color);
}

.text-muted {
  color: var(--text-muted);
}

.promote-content {
  .promote-section {
    margin-top: 16px;
    .promote-label { font-size: 14px; font-weight: 600; color: var(--text-primary); margin-bottom: 10px; }
    .promote-grades { display: flex; flex-wrap: wrap; gap: 8px; }
    .promote-hint { font-size: 12px; color: var(--text-muted); margin-top: 8px; }
  }
  .promote-preview { margin-top: 16px; }
  .promote-empty { margin-top: 16px; }
}
</style>
