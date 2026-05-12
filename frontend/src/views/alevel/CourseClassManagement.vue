<template>
  <div class="class-management">
    <!-- 工具栏 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <el-input
          v-model="searchQuery"
          placeholder="搜索课程班名称"
          clearable
          style="width: 220px"
          @keyup.enter="loadClasses"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-select v-model="filterSubjectId" placeholder="科目" clearable style="width: 150px" @change="loadClasses">
          <el-option v-for="s in alevelSubjectList" :key="s.id" :label="s.name" :value="s.id" />
        </el-select>
        <el-select v-model="filterStatus" placeholder="状态" clearable style="width: 120px" @change="loadClasses">
          <el-option label="活跃" value="ACTIVE" />
          <el-option label="待开课" value="PENDING" />
          <el-option label="已关闭" value="CLOSED" />
        </el-select>
      </div>
      <div class="toolbar-right">
        <el-button type="primary" @click="showAddDialog = true">
          <el-icon><Plus /></el-icon>创建课程班
        </el-button>
      </div>
    </div>
    
    <!-- 数据表格 -->
    <el-table :data="classes" stripe v-loading="loading" style="width: 100%">
      <el-table-column type="index" width="50" />
      <el-table-column prop="name" label="课程班名称" min-width="180" />
      <el-table-column prop="code" label="代码" width="120">
        <template #default="{ row }">
          <span class="code-text">{{ row.code || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="subjectName" label="科目" width="140" />
      <el-table-column prop="teacherName" label="授课教师" width="120">
        <template #default="{ row }">
          <span v-if="row.teacherName">{{ row.teacherName }}</span>
          <span v-else class="text-muted">未分配</span>
        </template>
      </el-table-column>
      <el-table-column prop="enrollment" label="人数/容量" width="110" align="center">
        <template #default="{ row }">
          <el-progress
            :percentage="Math.round((row.currentEnrollment / row.maxCapacity) * 100)"
            :status="row.currentEnrollment >= row.maxCapacity ? 'exception' : ''"
            :stroke-width="14"
            :show-text="true"
            style="width: 80px"
          >
            <template #default="{ percentage }">
              <span class="enrollment-text">{{ row.currentEnrollment }}/{{ row.maxCapacity }}</span>
            </template>
          </el-progress>
        </template>
      </el-table-column>
      <el-table-column prop="semester" label="学期" width="90">
        <template #default="{ row }">
          <el-tag :type="row.semester === 'FALL' ? 'warning' : 'success'" size="small">
            {{ row.semester === 'FALL' ? '秋季' : '春季' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="classStatusType(row.status)" size="small">
            {{ classStatusText(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="220" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link @click="editClass(row)">编辑</el-button>
          <el-button type="success" link @click="manageMembers(row)">成员</el-button>
          <el-popconfirm title="确定删除该课程班吗？" @confirm="deleteClass(row)">
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
        @change="loadClasses"
      />
    </div>
    
    <!-- 添加/编辑对话框 -->
    <el-dialog
      v-model="showAddDialog"
      :title="editingClass ? '编辑课程班' : '创建课程班'"
      width="600px"
      destroy-on-close
    >
      <el-form :model="classForm" label-width="100px" :rules="formRules" ref="formRef">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="课程班名称" prop="name">
              <el-input v-model="classForm.name" placeholder="如：数学 AS-1班" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="代码">
              <el-input v-model="classForm.code" placeholder="课程班代码（可选）" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="科目" prop="alevelSubjectId">
              <el-select v-model="classForm.alevelSubjectId" placeholder="选择科目" style="width: 100%" filterable>
                <el-option v-for="s in alevelSubjectList" :key="s.id" :label="s.name + ' (' + s.exam_board + ' ' + s.level + ')'" :value="s.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="授课教师">
              <el-select v-model="classForm.teacherId" placeholder="选择教师（可选）" clearable style="width: 100%" filterable>
                <el-option v-for="t in teacherList" :key="t.id" :label="t.name" :value="t.id" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="最大容量">
              <el-input-number v-model="classForm.maxCapacity" :min="1" :max="100" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="学期">
              <el-select v-model="classForm.semester" style="width: 100%">
                <el-option label="秋季" value="FALL" />
                <el-option label="春季" value="SPRING" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="学年">
              <el-input v-model="classForm.academicYear" placeholder="如 2025-2026" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="状态">
              <el-select v-model="classForm.status" style="width: 100%">
                <el-option label="活跃" value="ACTIVE" />
                <el-option label="待开课" value="PENDING" />
                <el-option label="已关闭" value="CLOSED" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="saveClass">保存</el-button>
      </template>
    </el-dialog>
    
    <!-- 成员管理对话框 -->
    <el-dialog
      v-model="showMemberDialog"
      title="课程班成员管理"
      width="600px"
      destroy-on-close
    >
      <div class="member-toolbar">
        <el-select v-model="newMemberId" placeholder="选择学生加入" style="width: 260px" filterable>
          <el-option v-for="s in availableStudents" :key="s.id" :label="s.name + ' (' + s.studentNo + ')'" :value="s.id" />
        </el-select>
        <el-button type="primary" @click="addMember" :disabled="!newMemberId">
          <el-icon><Plus /></el-icon>加入
        </el-button>
      </div>
      <el-table :data="members" stripe size="small" style="width: 100%">
        <el-table-column prop="studentName" label="学生姓名" />
        <el-table-column prop="studentNo" label="学号" />
        <el-table-column prop="enrolledAt" label="加入时间">
          <template #default="{ row }">
            {{ formatDate(row.enrolledAt) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-popconfirm title="确定移除该学生吗？" @confirm="removeMember(row)">
              <template #reference><el-button type="danger" link size="small">移除</el-button></template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Plus } from '@element-plus/icons-vue'
import { getCourseClasses, createCourseClass, updateCourseClass, deleteCourseClass as deleteCourseClassApi, getCourseClassMembers, addCourseClassMember, removeCourseClassMember } from '@/api/courseClasses'
import { getAlevelSubjects } from '@/api/alevelSubjects'
import { getTeachers } from '@/api/teachers'
import { getStudents } from '@/api/students'

const loading = ref(false)
const classes = ref([])
const searchQuery = ref('')
const filterSubjectId = ref('')
const filterStatus = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const totalCount = ref(0)
const useMockData = ref(false)

const showAddDialog = ref(false)
const showMemberDialog = ref(false)
const editingClass = ref(null)
const currentClass = ref(null)
const formRef = ref(null)
const alevelSubjectList = ref([])
const teacherList = ref([])
const studentList = ref([])
const members = ref([])
const newMemberId = ref(null)

const classForm = ref({
  name: '',
  code: '',
  alevelSubjectId: null,
  teacherId: null,
  maxCapacity: 20,
  semester: 'FALL',
  academicYear: '2025-2026',
  status: 'ACTIVE'
})

const formRules = {
  name: [{ required: true, message: '请输入课程班名称', trigger: 'blur' }],
  alevelSubjectId: [{ required: true, message: '请选择科目', trigger: 'change', type: 'number' }]
}

const mockClasses = [
  { id: 1, name: '数学 AS-1班', code: 'MATH-AS-01', alevelSubjectId: 1, subjectName: '数学', teacherId: 1, teacherName: '王老师', maxCapacity: 20, currentEnrollment: 15, semester: 'FALL', academicYear: '2025-2026', status: 'ACTIVE' },
  { id: 2, name: '物理 AS-1班', code: 'PHY-AS-01', alevelSubjectId: 2, subjectName: '物理', teacherId: null, teacherName: null, maxCapacity: 18, currentEnrollment: 12, semester: 'FALL', academicYear: '2025-2026', status: 'PENDING' }
]

const classStatusType = (status) => {
  const map = { ACTIVE: 'success', PENDING: 'warning', CLOSED: 'info' }
  return map[status] || 'info'
}

const classStatusText = (status) => {
  const map = { ACTIVE: '活跃', PENDING: '待开课', CLOSED: '已关闭' }
  return map[status] || status
}

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  return d.toLocaleDateString('zh-CN')
}

const availableStudents = computed(() => {
  const memberIds = members.value.map(m => m.studentId)
  return studentList.value.filter(s => !memberIds.includes(s.id))
})

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

const loadTeachers = async () => {
  try {
    const res = await getTeachers({ page: 1, page_size: 500 })
    teacherList.value = (res.data?.items || []).map(t => ({ id: t.id, name: t.name }))
  } catch (e) {
    console.warn('加载教师失败:', e)
    teacherList.value = []
  }
}

const loadStudents = async () => {
  try {
    const res = await getStudents({ page: 1, page_size: 500 })
    studentList.value = (res.data?.items || []).map(s => ({ id: s.id, name: s.name, studentNo: s.student_no }))
  } catch (e) {
    console.warn('加载学生失败:', e)
    studentList.value = [
      { id: 1, name: '张三', studentNo: '20251001' },
      { id: 2, name: '李四', studentNo: '20251002' }
    ]
  }
}

const getSubjectName = (subjectId) => {
  const sub = alevelSubjectList.value.find(s => s.id === subjectId)
  return sub ? sub.name : ''
}

const getTeacherName = (teacherId) => {
  const t = teacherList.value.find(te => te.id === teacherId)
  return t ? t.name : ''
}

const loadClasses = async () => {
  loading.value = true
  try {
    const res = await getCourseClasses({
      page: currentPage.value,
      page_size: pageSize.value,
      alevel_subject_id: filterSubjectId.value || undefined,
      status: filterStatus.value || undefined,
      search: searchQuery.value || undefined
    })
    useMockData.value = false
    const items = res.data?.items || []
    classes.value = items.map(c => ({
      ...c,
      alevelSubjectId: c.alevel_subject_id,
      teacherId: c.teacher_id,
      maxCapacity: c.max_capacity,
      currentEnrollment: c.current_enrollment,
      academicYear: c.academic_year,
      subjectName: getSubjectName(c.alevel_subject_id),
      teacherName: getTeacherName(c.teacher_id)
    }))
    totalCount.value = res.data?.total || 0
  } catch (error) {
    console.warn('后端 API 未启动，使用 Mock 数据')
    useMockData.value = true
    let filtered = [...mockClasses]
    if (filterSubjectId.value) filtered = filtered.filter(c => c.alevelSubjectId === filterSubjectId.value)
    if (filterStatus.value) filtered = filtered.filter(c => c.status === filterStatus.value)
    if (searchQuery.value) {
      const q = searchQuery.value.toLowerCase()
      filtered = filtered.filter(c => c.name.toLowerCase().includes(q))
    }
    classes.value = filtered
    totalCount.value = filtered.length
  } finally {
    loading.value = false
  }
}

const editClass = (row) => {
  editingClass.value = row
  classForm.value = {
    name: row.name,
    code: row.code || '',
    alevelSubjectId: row.alevelSubjectId,
    teacherId: row.teacherId || null,
    maxCapacity: row.maxCapacity,
    semester: row.semester,
    academicYear: row.academicYear,
    status: row.status
  }
  showAddDialog.value = true
}

const saveClass = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  
  const submitData = {
    name: classForm.value.name,
    code: classForm.value.code || null,
    alevel_subject_id: classForm.value.alevelSubjectId,
    teacher_id: classForm.value.teacherId || null,
    max_capacity: classForm.value.maxCapacity,
    semester: classForm.value.semester,
    academic_year: classForm.value.academicYear,
    status: classForm.value.status
  }
  
  try {
    if (editingClass.value) {
      if (!useMockData.value) await updateCourseClass(editingClass.value.id, submitData)
      const idx = classes.value.findIndex(c => c.id === editingClass.value.id)
      if (idx !== -1) classes.value[idx] = { ...classes.value[idx], ...classForm.value }
      ElMessage.success('更新成功')
    } else {
      if (!useMockData.value) {
        const res = await createCourseClass(submitData)
        classes.value.unshift({
          ...res.data,
          alevelSubjectId: res.data.alevel_subject_id,
          teacherId: res.data.teacher_id,
          maxCapacity: res.data.max_capacity,
          currentEnrollment: res.data.current_enrollment,
          academicYear: res.data.academic_year,
          subjectName: getSubjectName(res.data.alevel_subject_id),
          teacherName: getTeacherName(res.data.teacher_id)
        })
      } else {
        classes.value.unshift({
          id: Date.now(),
          ...classForm.value,
          currentEnrollment: 0,
          subjectName: getSubjectName(classForm.value.alevelSubjectId),
          teacherName: getTeacherName(classForm.value.teacherId)
        })
      }
      ElMessage.success('创建成功')
    }
    showAddDialog.value = false
    editingClass.value = null
    resetForm()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '操作失败')
  }
}

const deleteClass = async (row) => {
  try {
    if (!useMockData.value) await deleteCourseClassApi(row.id)
    classes.value = classes.value.filter(c => c.id !== row.id)
    ElMessage.success('删除成功')
  } catch (error) {
    ElMessage.error('删除失败')
  }
}

const manageMembers = async (row) => {
  currentClass.value = row
  showMemberDialog.value = true
  await loadMembers(row.id)
}

const loadMembers = async (classId) => {
  try {
    const res = await getCourseClassMembers(classId)
    const items = res.data?.items || []
    members.value = items.map(m => ({
      ...m,
      studentId: m.student_id,
      courseClassId: m.course_class_id,
      enrolledAt: m.enrolled_at,
      studentName: getStudentName(m.student_id),
      studentNo: getStudentNo(m.student_id)
    }))
  } catch (e) {
    console.warn('加载成员失败:', e)
    members.value = []
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

const addMember = async () => {
  if (!newMemberId.value || !currentClass.value) return
  try {
    await addCourseClassMember(currentClass.value.id, {
      student_id: newMemberId.value,
      status: 'ENROLLED'
    })
    ElMessage.success('添加成功')
    newMemberId.value = null
    await loadMembers(currentClass.value.id)
    await loadClasses()
  } catch (error) {
    ElMessage.error('添加失败')
  }
}

const removeMember = async (row) => {
  try {
    await removeCourseClassMember(row.id)
    ElMessage.success('移除成功')
    await loadMembers(currentClass.value.id)
    await loadClasses()
  } catch (error) {
    ElMessage.error('移除失败')
  }
}

const resetForm = () => {
  classForm.value = {
    name: '', code: '', alevelSubjectId: null, teacherId: null,
    maxCapacity: 20, semester: 'FALL', academicYear: '2025-2026', status: 'ACTIVE'
  }
}

onMounted(() => {
  loadAlevelSubjects()
  loadTeachers()
  loadStudents()
  loadClasses()
})
</script>

<style lang="scss" scoped>
.class-management { padding: 20px; }
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
.text-muted { color: var(--text-muted); }
.enrollment-text { font-size: 12px; color: var(--text-secondary); }
.member-toolbar {
  display: flex; gap: 12px; margin-bottom: 16px; align-items: center;
}
</style>
