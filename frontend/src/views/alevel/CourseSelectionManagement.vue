<template>
  <div class="selection-management">
    <!-- 工具栏 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <el-select v-model="filterStudentId" placeholder="选择学生" clearable style="width: 180px" @change="loadSelections">
          <el-option v-for="s in studentList" :key="s.id" :label="s.name + ' (' + s.studentNo + ')'" :value="s.id" />
        </el-select>
        <el-select v-model="filterStatus" placeholder="状态" clearable style="width: 130px" @change="loadSelections">
          <el-option label="草稿" value="DRAFT" />
          <el-option label="已提交" value="SUBMITTED" />
          <el-option label="已审批" value="APPROVED" />
          <el-option label="已拒绝" value="REJECTED" />
        </el-select>
        <el-select v-model="filterSemester" placeholder="学期" clearable style="width: 110px" @change="loadSelections">
          <el-option label="秋季" value="FALL" />
          <el-option label="春季" value="SPRING" />
        </el-select>
      </div>
      <div class="toolbar-right">
        <el-button type="primary" @click="showAddDialog = true">
          <el-icon><Plus /></el-icon>新建选课
        </el-button>
      </div>
    </div>
    
    <!-- 数据表格 -->
    <el-table :data="selections" stripe v-loading="loading" style="width: 100%">
      <el-table-column type="index" width="50" />
      <el-table-column prop="studentName" label="学生" width="140">
        <template #default="{ row }">
          <div class="student-cell">
            <span class="student-name">{{ row.studentName }}</span>
            <span class="student-no">{{ row.studentNo }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="academicYear" label="学年" width="120" />
      <el-table-column prop="semester" label="学期" width="90">
        <template #default="{ row }">
          <el-tag :type="row.semester === 'FALL' ? 'warning' : 'success'" size="small">
            {{ row.semester === 'FALL' ? '秋季' : '春季' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="选课科目" min-width="200">
        <template #default="{ row }">
          <div class="selection-tags">
            <el-tag v-for="(sel, idx) in row.selections" :key="idx" size="small" type="info" class="sel-tag">
              {{ getSubjectName(sel.alevel_subject_id) }}
            </el-tag>
            <span v-if="!row.selections || row.selections.length === 0" class="text-muted">未选课</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="totalWeeklyHours" label="总课时" width="90" align="center" />
      <el-table-column prop="status" label="状态" width="110">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)" size="small">
            {{ statusText(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link @click="editSelection(row)">编辑</el-button>
          <el-button type="success" link @click="approveSelection(row)" v-if="row.status === 'SUBMITTED'">审批</el-button>
          <el-popconfirm title="确定删除该选课记录吗？" @confirm="deleteSelection(row)">
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
        @change="loadSelections"
      />
    </div>
    
    <!-- 添加/编辑对话框 -->
    <el-dialog
      v-model="showAddDialog"
      :title="editingSelection ? '编辑选课' : '新建选课'"
      width="700px"
      destroy-on-close
    >
      <el-form :model="selectionForm" label-width="100px" :rules="formRules" ref="formRef">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="学生" prop="studentId">
              <el-select v-model="selectionForm.studentId" placeholder="选择学生" style="width: 100%" filterable>
                <el-option v-for="s in studentList" :key="s.id" :label="s.name + ' (' + s.studentNo + ')'" :value="s.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="学年" prop="academicYear">
              <el-input v-model="selectionForm.academicYear" placeholder="如 2025-2026" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="学期" prop="semester">
              <el-select v-model="selectionForm.semester" style="width: 100%">
                <el-option label="秋季" value="FALL" />
                <el-option label="春季" value="SPRING" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="状态">
              <el-select v-model="selectionForm.status" style="width: 100%">
                <el-option label="草稿" value="DRAFT" />
                <el-option label="已提交" value="SUBMITTED" />
                <el-option label="已审批" value="APPROVED" />
                <el-option label="已拒绝" value="REJECTED" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-divider content-position="left">选课科目</el-divider>
        
        <div class="subject-selection">
          <div v-for="(item, index) in selectionForm.selections" :key="index" class="sel-row">
            <el-select v-model="item.alevelSubjectId" placeholder="选择科目" style="width: 220px" filterable>
              <el-option v-for="sub in alevelSubjectList" :key="sub.id" :label="sub.name + ' (' + sub.exam_board + ' ' + sub.level + ')'" :value="sub.id" />
            </el-select>
            <el-input-number v-model="item.priority" :min="1" :max="10" placeholder="优先级" style="width: 120px" />
            <el-button type="danger" link @click="removeSelectionItem(index)">
              <el-icon><Delete /></el-icon>
            </el-button>
          </div>
          <el-button type="primary" link @click="addSelectionItem" class="add-sel-btn">
            <el-icon><Plus /></el-icon>添加科目
          </el-button>
        </div>
        
        <el-form-item label="备注" style="margin-top: 16px">
          <el-input v-model="selectionForm.note" type="textarea" :rows="2" placeholder="备注（可选）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="saveSelection">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Delete } from '@element-plus/icons-vue'
import { getCourseSelections, createCourseSelection, updateCourseSelection, deleteCourseSelection as deleteCourseSelectionApi } from '@/api/courseSelections'
import { getStudents } from '@/api/students'
import { getAlevelSubjects } from '@/api/alevelSubjects'

const loading = ref(false)
const selections = ref([])
const filterStudentId = ref('')
const filterStatus = ref('')
const filterSemester = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const totalCount = ref(0)
const useMockData = ref(false)

const showAddDialog = ref(false)
const editingSelection = ref(null)
const formRef = ref(null)
const studentList = ref([])
const alevelSubjectList = ref([])

const selectionForm = ref({
  studentId: null,
  academicYear: '2025-2026',
  semester: 'FALL',
  status: 'DRAFT',
  selections: [],
  note: ''
})

const formRules = {
  studentId: [{ required: true, message: '请选择学生', trigger: 'change', type: 'number' }],
  academicYear: [{ required: true, message: '请输入学年', trigger: 'blur' }],
  semester: [{ required: true, message: '请选择学期', trigger: 'change' }]
}

const mockSelections = [
  { id: 1, studentId: 1, studentName: '张三', studentNo: '20251001', academicYear: '2025-2026', semester: 'FALL', selections: [{ alevel_subject_id: 1, priority: 1 }, { alevel_subject_id: 2, priority: 2 }], totalWeeklyHours: 10, status: 'DRAFT' },
  { id: 2, studentId: 2, studentName: '李四', studentNo: '20251002', academicYear: '2025-2026', semester: 'FALL', selections: [{ alevel_subject_id: 1, priority: 1 }], totalWeeklyHours: 5, status: 'SUBMITTED' }
]

const statusType = (status) => {
  const map = { DRAFT: 'info', SUBMITTED: 'warning', APPROVED: 'success', REJECTED: 'danger' }
  return map[status] || 'info'
}

const statusText = (status) => {
  const map = { DRAFT: '草稿', SUBMITTED: '已提交', APPROVED: '已审批', REJECTED: '已拒绝' }
  return map[status] || status
}

const getSubjectName = (subjectId) => {
  const sub = alevelSubjectList.value.find(s => s.id === subjectId)
  return sub ? sub.name : '科目' + subjectId
}

const loadStudents = async () => {
  try {
    const res = await getStudents({ page: 1, page_size: 500 })
    studentList.value = (res.data?.items || []).map(s => ({
      id: s.id,
      name: s.name,
      studentNo: s.student_no
    }))
  } catch (e) {
    console.warn('加载学生失败:', e)
    studentList.value = [
      { id: 1, name: '张三', studentNo: '20251001' },
      { id: 2, name: '李四', studentNo: '20251002' }
    ]
  }
}

const loadAlevelSubjects = async () => {
  try {
    const res = await getAlevelSubjects({ page: 1, page_size: 500 })
    alevelSubjectList.value = res.data?.items || []
  } catch (e) {
    console.warn('加载科目失败:', e)
    alevelSubjectList.value = [
      { id: 1, name: '数学', exam_board: 'CAIE', level: 'AS' },
      { id: 2, name: '物理', exam_board: 'CAIE', level: 'AS' }
    ]
  }
}

const loadSelections = async () => {
  loading.value = true
  try {
    const res = await getCourseSelections({
      page: currentPage.value,
      page_size: pageSize.value,
      student_id: filterStudentId.value || undefined,
      status: filterStatus.value || undefined,
      semester: filterSemester.value || undefined
    })
    useMockData.value = false
    const items = res.data?.items || []
    selections.value = items.map(s => ({
      ...s,
      studentId: s.student_id,
      academicYear: s.academic_year,
      totalWeeklyHours: s.total_weekly_hours,
      studentName: getStudentName(s.student_id),
      studentNo: getStudentNo(s.student_id)
    }))
    totalCount.value = res.data?.total || 0
  } catch (error) {
    console.warn('后端 API 未启动，使用 Mock 数据')
    useMockData.value = true
    let filtered = [...mockSelections]
    if (filterStudentId.value) filtered = filtered.filter(s => s.studentId === filterStudentId.value)
    if (filterStatus.value) filtered = filtered.filter(s => s.status === filterStatus.value)
    if (filterSemester.value) filtered = filtered.filter(s => s.semester === filterSemester.value)
    selections.value = filtered
    totalCount.value = filtered.length
  } finally {
    loading.value = false
  }
}

const getStudentName = (studentId) => {
  const s = studentList.value.find(st => st.id === studentId)
  return s ? s.name : ''
}

const getStudentNo = (studentId) => {
  const s = studentList.value.find(st => st.id === studentId)
  return s ? s.studentNo : ''
}

const addSelectionItem = () => {
  selectionForm.value.selections.push({ alevelSubjectId: null, priority: 1 })
}

const removeSelectionItem = (index) => {
  selectionForm.value.selections.splice(index, 1)
}

const editSelection = (row) => {
  editingSelection.value = row
  selectionForm.value = {
    studentId: row.studentId,
    academicYear: row.academicYear,
    semester: row.semester,
    status: row.status,
    selections: (row.selections || []).map(s => ({
      alevelSubjectId: s.alevel_subject_id || s.alevelSubjectId,
      priority: s.priority || 1
    })),
    note: row.note || ''
  }
  showAddDialog.value = true
}

const approveSelection = async (row) => {
  try {
    if (!useMockData.value) {
      await updateCourseSelection(row.id, { status: 'APPROVED' })
    }
    row.status = 'APPROVED'
    ElMessage.success('审批通过')
  } catch (error) {
    ElMessage.error('审批失败')
  }
}

const saveSelection = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  
  const submitData = {
    student_id: selectionForm.value.studentId,
    academic_year: selectionForm.value.academicYear,
    semester: selectionForm.value.semester,
    status: selectionForm.value.status,
    selections: selectionForm.value.selections.map(s => ({
      alevel_subject_id: s.alevelSubjectId,
      priority: s.priority
    })),
    note: selectionForm.value.note || null
  }
  
  try {
    if (editingSelection.value) {
      if (!useMockData.value) await updateCourseSelection(editingSelection.value.id, submitData)
      const idx = selections.value.findIndex(s => s.id === editingSelection.value.id)
      if (idx !== -1) {
        selections.value[idx] = { ...selections.value[idx], ...selectionForm.value }
      }
      ElMessage.success('更新成功')
    } else {
      if (!useMockData.value) {
        const res = await createCourseSelection(submitData)
        selections.value.unshift({
          ...res.data,
          studentId: res.data.student_id,
          academicYear: res.data.academic_year,
          totalWeeklyHours: res.data.total_weekly_hours
        })
      } else {
        selections.value.unshift({
          id: Date.now(),
          ...selectionForm.value,
          studentName: getStudentName(selectionForm.value.studentId),
          studentNo: getStudentNo(selectionForm.value.studentId)
        })
      }
      ElMessage.success('创建成功')
    }
    showAddDialog.value = false
    editingSelection.value = null
    resetForm()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '操作失败')
  }
}

const deleteSelection = async (row) => {
  try {
    if (!useMockData.value) await deleteCourseSelectionApi(row.id)
    selections.value = selections.value.filter(s => s.id !== row.id)
    ElMessage.success('删除成功')
  } catch (error) {
    ElMessage.error('删除失败')
  }
}

const resetForm = () => {
  selectionForm.value = {
    studentId: null, academicYear: '2025-2026', semester: 'FALL',
    status: 'DRAFT', selections: [], note: ''
  }
}

onMounted(() => {
  loadStudents()
  loadAlevelSubjects()
  loadSelections()
})
</script>

<style lang="scss" scoped>
.selection-management { padding: 20px; }
.toolbar {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 16px; gap: 12px; flex-wrap: wrap;
}
.toolbar-left { display: flex; gap: 12px; align-items: center; }
.pagination-wrapper {
  display: flex; justify-content: flex-end;
  margin-top: 16px; padding-top: 16px; border-top: 1px solid var(--border-color);
}
.student-cell {
  display: flex; flex-direction: column;
  .student-name { font-weight: 500; }
  .student-no { font-size: 12px; color: var(--text-muted); }
}
.selection-tags {
  display: flex; flex-wrap: wrap; gap: 4px;
  .sel-tag { margin-right: 0; }
}
.subject-selection {
  padding: 0 12px;
  .sel-row {
    display: flex; align-items: center; gap: 8px;
    margin-bottom: 8px;
  }
  .add-sel-btn { margin-top: 4px; }
}
.text-muted { color: var(--text-muted); }
</style>
