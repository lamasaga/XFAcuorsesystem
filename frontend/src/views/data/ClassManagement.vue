<template>
  <div class="class-management">
    <div class="toolbar">
      <div class="toolbar-left">
        <el-input v-model="searchQuery" placeholder="搜索班级" prefix-icon="Search" clearable class="search-input" />
        <el-select v-model="filterType" placeholder="班级类型" clearable style="width: 120px">
          <el-option label="国际班 (I)" value="I" />
          <el-option label="综素班 (N)" value="N" />
        </el-select>
        <el-select v-model="filterDepartment" placeholder="学部" clearable style="width: 120px">
          <el-option label="小学部" value="PRIMARY" />
          <el-option label="中学部" value="SECONDARY" />
        </el-select>
      </div>
      <div class="toolbar-right">
        <el-button @click="showImportDialog = true"><el-icon><Upload /></el-icon>导入</el-button>
        <el-button type="warning" @click="openPromoteDialog"><el-icon><TopRight /></el-icon>一键升班</el-button>
        <el-button type="primary" @click="openAddDialog"><el-icon><Plus /></el-icon>添加班级</el-button>
      </div>
    </div>
    
    <!-- 学部分组展示 -->
    <div class="departments-container">
      <!-- 小学部 -->
      <div class="department-section">
        <div class="department-header">
          <h3>
            <el-icon><School /></el-icon>
            小学部 (PRIMARY)
          </h3>
          <span class="class-count">{{ primaryClasses.length }} 个班级</span>
        </div>
        
        <!-- 按年级分组 -->
        <div v-for="grade in primaryGrades" :key="grade.key" class="grade-group">
          <div class="grade-title">
            <span class="grade-name">{{ grade.name }}</span>
            <span class="grade-count">{{ getClassesByGrade(grade.key, 'PRIMARY').length }} 个班</span>
          </div>
          <div class="classes-grid">
            <div 
              v-for="cls in getClassesByGrade(grade.key, 'PRIMARY')" 
              :key="cls.id"
              class="class-card"
              :class="{ 'type-i': cls.type === 'I', 'type-n': cls.type === 'N' }"
            >
              <div class="class-type-badge">{{ cls.type }}</div>
              <div class="class-avatar">
                <span>{{ cls.classNo }}</span>
              </div>
              <div class="class-info">
                <div class="class-name">{{ cls.name }}</div>
                <div class="class-homeroom">
                  <div class="homeroom-item" v-if="cls.homeroomCN">
                    <el-tag size="small" type="danger">中</el-tag>
                    <span>{{ cls.homeroomCN }}</span>
                  </div>
                  <div class="homeroom-item" v-if="cls.homeroomEN">
                    <el-tag size="small" type="warning">外</el-tag>
                    <span>{{ cls.homeroomEN }}</span>
                  </div>
                </div>
              </div>
              <el-dropdown trigger="click" @click.stop>
                <el-button class="more-btn" link><el-icon><More /></el-icon></el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item @click="editClass(cls)"><el-icon><Edit /></el-icon>编辑</el-dropdown-item>
                    <el-dropdown-item @click="viewSchedule(cls)"><el-icon><Calendar /></el-icon>查看课表</el-dropdown-item>
                    <el-dropdown-item divided @click="deleteClass(cls)"><el-icon><Delete /></el-icon>删除</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 中学部 -->
      <div class="department-section">
        <div class="department-header">
          <h3>
            <el-icon><OfficeBuilding /></el-icon>
            中学部 (SECONDARY)
          </h3>
          <span class="class-count">{{ secondaryClasses.length }} 个班级</span>
        </div>
        
        <div v-for="grade in secondaryGrades" :key="grade.key" class="grade-group">
          <div class="grade-title">
            <span class="grade-name">{{ grade.name }}</span>
            <span class="grade-count">{{ getClassesByGrade(grade.key, 'SECONDARY').length }} 个班</span>
          </div>
          <div class="classes-grid">
            <div 
              v-for="cls in getClassesByGrade(grade.key, 'SECONDARY')" 
              :key="cls.id"
              class="class-card"
              :class="{ 'type-i': cls.type === 'I', 'type-n': cls.type === 'N' }"
            >
              <div class="class-type-badge">{{ cls.type }}</div>
              <div class="class-avatar">
                <span>{{ cls.classNo }}</span>
              </div>
              <div class="class-info">
                <div class="class-name">{{ cls.name }}</div>
                <div class="class-homeroom">
                  <div class="homeroom-item" v-if="cls.homeroomCN">
                    <el-tag size="small" type="danger">中</el-tag>
                    <span>{{ cls.homeroomCN }}</span>
                  </div>
                  <div class="homeroom-item" v-if="cls.homeroomEN">
                    <el-tag size="small" type="warning">外</el-tag>
                    <span>{{ cls.homeroomEN }}</span>
                  </div>
                </div>
              </div>
              <el-dropdown trigger="click" @click.stop>
                <el-button class="more-btn" link><el-icon><More /></el-icon></el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item @click="editClass(cls)"><el-icon><Edit /></el-icon>编辑</el-dropdown-item>
                    <el-dropdown-item @click="viewSchedule(cls)"><el-icon><Calendar /></el-icon>查看课表</el-dropdown-item>
                    <el-dropdown-item divided @click="deleteClass(cls)"><el-icon><Delete /></el-icon>删除</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 统计信息 -->
    <div class="class-summary card">
      <div class="summary-item">
        <span class="label">国际班 (I类):</span>
        <span class="value">{{ classes.filter(c => c.type === 'I').length }} 个</span>
      </div>
      <div class="summary-item">
        <span class="label">综素班 (N类):</span>
        <span class="value">{{ classes.filter(c => c.type === 'N').length }} 个</span>
      </div>
      <div class="summary-item">
        <span class="label">小学部:</span>
        <span class="value">{{ primaryClasses.length }} 个</span>
      </div>
      <div class="summary-item">
        <span class="label">中学部:</span>
        <span class="value">{{ secondaryClasses.length }} 个</span>
      </div>
    </div>
    
    <!-- 添加/编辑对话框 -->
    <el-dialog v-model="showAddDialog" :title="editingClass ? '编辑班级' : '添加班级'" width="550px">
      <el-form :model="classForm" label-width="100px">
        <el-form-item label="班级类型">
          <el-radio-group v-model="classForm.type">
            <el-radio value="I">国际班 (I类)</el-radio>
            <el-radio value="N">综素班 (N类)</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="年级">
          <el-select v-model="classForm.grade" placeholder="选择年级" style="width: 100%">
            <el-option-group label="小学部">
              <el-option label="PK (学前班)" value="PK" />
              <el-option label="KG (幼儿园)" value="KG" />
              <el-option v-for="g in 5" :key="g" :label="`G${g} (${g}年级)`" :value="`G${g}`" />
            </el-option-group>
            <el-option-group label="中学部">
              <el-option v-for="g in 7" :key="g+5" :label="`G${g+5} (${g+5}年级)`" :value="`G${g+5}`" />
            </el-option-group>
          </el-select>
        </el-form-item>
        <el-form-item label="班级序号">
          <el-input-number v-model="classForm.classNo" :min="1" :max="5" />
        </el-form-item>
        <el-form-item label="中教班主任">
          <el-select v-model="classForm.homeroomCnId" placeholder="选择中教班主任" clearable filterable style="width: 100%">
            <el-option label="（空置）" value="" class="empty-option" />
            <el-option v-for="t in cnTeachers" :key="t.id" :label="t.name" :value="t.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="外教班主任">
          <el-select v-model="classForm.homeroomEnId" placeholder="选择外教班主任" clearable filterable style="width: 100%">
            <el-option label="（空置）" value="" class="empty-option" />
            <el-option v-for="t in enTeachers" :key="t.id" :label="t.name" :value="t.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="saveClass">保存</el-button>
      </template>
    </el-dialog>
    
    <!-- 导入对话框 -->
    <ExcelImportDialog
      v-model="showImportDialog"
      title="导入班级数据"
      :template-url="getClassImportTemplateUrl('xlsx')"
      :import-api="importClassesFile"
      @success="loadClasses"
    />

    <!-- 一键升班对话框 -->
    <el-dialog v-model="showPromoteDialog" title="一键升班" width="520px">
      <div class="promote-content">
        <el-alert
          type="warning"
          :closable="false"
          show-icon
        >
          <template #title>
            <span>此操作将把选定年级的所有班级升级到下一年级，同时更新班级内所有学生的年级。</span>
          </template>
        </el-alert>
        
        <div class="promote-section">
          <div class="promote-label">选择要升级的年级：</div>
          <el-checkbox-group v-model="promoteGrades" class="promote-grades">
            <el-checkbox v-for="g in allGrades" :key="g.key" :value="g.key" :label="g.name" />
          </el-checkbox-group>
          <div class="promote-hint">留空则默认升级所有非毕业年级（PK ~ G11）</div>
        </div>

        <div class="promote-preview" v-if="promotePreview.length > 0">
          <div class="promote-label">将要升级的班级预览：</div>
          <el-table :data="promotePreview" size="small" max-height="240">
            <el-table-column prop="oldName" label="当前名称" width="120" />
            <el-table-column prop="newName" label="升级后" width="120" />
            <el-table-column prop="studentCount" label="学生数" width="80" />
          </el-table>
        </div>
        <div class="promote-empty" v-else>
          <el-empty description="未选择年级或该年级暂无班级" :image-size="80" />
        </div>
      </div>
      <template #footer>
        <el-button @click="showPromoteDialog = false">取消</el-button>
        <el-button type="warning" @click="executePromote" :disabled="promotePreview.length === 0">
          确认升班
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
/**
 * 班级管理页面
 * 
 * 功能：
 * - 从后端 API 获取班级数据
 * - 支持按学部、类型筛选
 * - 支持添加、编辑、删除班级
 */
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Upload, Plus, More, Edit, Calendar, Delete, School, OfficeBuilding, TopRight } from '@element-plus/icons-vue'
// 导入 API
import { getClasses, createClass, updateClass, deleteClass as deleteClassApi, getClassImportTemplateUrl, importClassesFile, promoteClasses } from '@/api/classes'
import { getTeachers } from '@/api/teachers'
import { getScheduleList } from '@/api/schedules'
import ExcelImportDialog from '@/components/ExcelImportDialog.vue'

const router = useRouter()

// 当前激活的课表
const activeScheduleId = ref(null)

const searchQuery = ref('')
const filterType = ref('')
const filterDepartment = ref('')
const showAddDialog = ref(false)
const showImportDialog = ref(false)
const showPromoteDialog = ref(false)
const editingClass = ref(null)
const loading = ref(false)
const useMockData = ref(false)

// 一键升班
const promoteGrades = ref([])
const allGrades = [
  { key: 'PK', name: 'PK (学前班)' },
  { key: 'KG', name: 'KG (幼儿园)' },
  { key: 'G1', name: 'G1 (一年级)' },
  { key: 'G2', name: 'G2 (二年级)' },
  { key: 'G3', name: 'G3 (三年级)' },
  { key: 'G4', name: 'G4 (四年级)' },
  { key: 'G5', name: 'G5 (五年级)' },
  { key: 'G6', name: 'G6 (六年级)' },
  { key: 'G7', name: 'G7 (七年级)' },
  { key: 'G8', name: 'G8 (八年级)' },
  { key: 'G9', name: 'G9 (九年级)' },
  { key: 'G10', name: 'G10 (十年级)' },
  { key: 'G11', name: 'G11 (十一年级)' },
  { key: 'G12', name: 'G12 (十二年级/毕业)' },
]

const GRADE_NEXT = {
  PK: 'KG', KG: 'G1', G1: 'G2', G2: 'G3', G3: 'G4', G4: 'G5',
  G5: 'G6', G6: 'G7', G7: 'G8', G8: 'G9', G9: 'G10', G10: 'G11', G11: 'G12'
}

const promotePreview = computed(() => {
  const grades = promoteGrades.value.length > 0 ? promoteGrades.value : Object.keys(GRADE_NEXT)
  const preview = []
  for (const grade of grades) {
    const classesInGrade = classes.value.filter(c => c.grade === grade)
    for (const cls of classesInGrade) {
      const newGrade = GRADE_NEXT[grade]
      if (!newGrade) continue
      // 模拟名称更新：将年级部分替换
      const newName = cls.name.replace(new RegExp(grade, 'i'), newGrade)
      preview.push({
        classId: cls.id,
        oldName: cls.name,
        newName: newName,
        newGrade: newGrade,
        studentCount: '-' // 前端不知道学生数
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
    await ElMessageBox.confirm(
      `确定要升级 ${promotePreview.value.length} 个班级吗？此操作不可撤销。`,
      '确认升班',
      { confirmButtonText: '确定升班', cancelButtonText: '取消', type: 'warning' }
    )
    
    const payload = promoteGrades.value.length > 0 ? { grades: promoteGrades.value } : {}
    const res = await promoteClasses(payload)
    
    ElMessage.success(res.message || '升班成功')
    showPromoteDialog.value = false
    await loadClasses()
  } catch (e) {
    if (e !== 'cancel') {
      const detail = e.response?.data?.detail || e.message || '未知错误'
      ElMessage.error('升班失败: ' + detail)
    }
  }
}

// 年级配置
const primaryGrades = [
  { key: 'PK', name: 'PK (学前班)' },
  { key: 'KG', name: 'KG (幼儿园)' },
  { key: 'G1', name: 'G1 (一年级)' },
  { key: 'G2', name: 'G2 (二年级)' },
  { key: 'G3', name: 'G3 (三年级)' },
  { key: 'G4', name: 'G4 (四年级)' },
  { key: 'G5', name: 'G5 (五年级)' },
]

const secondaryGrades = [
  { key: 'G6', name: 'G6 (六年级)' },
  { key: 'G7', name: 'G7 (七年级)' },
  { key: 'G8', name: 'G8 (八年级)' },
  { key: 'G9', name: 'G9 (九年级)' },
  { key: 'G10', name: 'G10 (十年级)' },
  { key: 'G11', name: 'G11 (十一年级)' },
  { key: 'G12', name: 'G12 (十二年级/毕业)' },
]

// 班级数据
const classes = ref([])

// Mock 数据 - 当后端未启动时使用
const mockClasses = [
  // 小学部 - I类国际班
  { id: 1, name: 'IPK-1', type: 'I', grade: 'PK', class_no: 1, department: 'PRIMARY', homeroom_cn_id: null, homeroom_en_id: null },
  { id: 2, name: 'IKG-1', type: 'I', grade: 'KG', class_no: 1, department: 'PRIMARY', homeroom_cn_id: null, homeroom_en_id: null },
  { id: 3, name: 'IG1-1', type: 'I', grade: 'G1', class_no: 1, department: 'PRIMARY', homeroom_cn_id: null, homeroom_en_id: null },
  { id: 4, name: 'IG1-2', type: 'I', grade: 'G1', class_no: 2, department: 'PRIMARY', homeroom_cn_id: null, homeroom_en_id: null },
  { id: 5, name: 'IG2-1', type: 'I', grade: 'G2', class_no: 1, department: 'PRIMARY', homeroom_cn_id: null, homeroom_en_id: null },
  { id: 6, name: 'IG2-2', type: 'I', grade: 'G2', class_no: 2, department: 'PRIMARY', homeroom_cn_id: null, homeroom_en_id: null },
  { id: 7, name: 'IG3-1', type: 'I', grade: 'G3', class_no: 1, department: 'PRIMARY', homeroom_cn_id: null, homeroom_en_id: null },
  { id: 8, name: 'IG3-2', type: 'I', grade: 'G3', class_no: 2, department: 'PRIMARY', homeroom_cn_id: null, homeroom_en_id: null },
  // 中学部 - I类国际班
  { id: 20, name: 'IG6-1', type: 'I', grade: 'G6', class_no: 1, department: 'SECONDARY', homeroom_cn_id: null, homeroom_en_id: null },
  { id: 21, name: 'IG6-2', type: 'I', grade: 'G6', class_no: 2, department: 'SECONDARY', homeroom_cn_id: null, homeroom_en_id: null },
  { id: 22, name: 'IG7-1', type: 'I', grade: 'G7', class_no: 1, department: 'SECONDARY', homeroom_cn_id: null, homeroom_en_id: null },
  // N类综素班
  { id: 30, name: 'NG1-1', type: 'N', grade: 'G1', class_no: 1, department: 'PRIMARY', homeroom_cn_id: null, homeroom_en_id: null },
  { id: 31, name: 'NG6-1', type: 'N', grade: 'G6', class_no: 1, department: 'SECONDARY', homeroom_cn_id: null, homeroom_en_id: null },
]

// 教师数据
const cnTeachers = ref([])
const enTeachers = ref([])
// 教师ID到名字的映射
const teacherIdToName = ref({})

const classForm = ref({ 
  type: 'I', 
  grade: '', 
  classNo: 1, 
  homeroomCnId: '',  // 存储教师ID，空字符串表示空置
  homeroomEnId: '' 
})

/**
 * 从 API 加载班级数据
 */
const loadClasses = async () => {
  loading.value = true
  try {
    const res = await getClasses({
      page: 1,
      page_size: 200,  // 获取所有班级
      type: filterType.value || undefined,
      department: filterDepartment.value || undefined,
      search: searchQuery.value || undefined
    })
    
    useMockData.value = false
    // 转换字段名，并根据班主任ID查找教师姓名
    classes.value = res.data.items.map(c => ({
      ...c,
      classNo: c.class_no,
      homeroomCN: c.homeroom_cn_id ? teacherIdToName.value[c.homeroom_cn_id] : null,
      homeroomEN: c.homeroom_en_id ? teacherIdToName.value[c.homeroom_en_id] : null
    }))
  } catch (error) {
    console.warn('后端 API 未启动，使用 Mock 数据', error.message)
    useMockData.value = true
    
    let filtered = [...mockClasses]
    if (filterType.value) {
      filtered = filtered.filter(c => c.type === filterType.value)
    }
    if (filterDepartment.value) {
      filtered = filtered.filter(c => c.department === filterDepartment.value)
    }
    if (searchQuery.value) {
      const query = searchQuery.value.toLowerCase()
      filtered = filtered.filter(c => c.name.toLowerCase().includes(query))
    }
    
    classes.value = filtered.map(c => ({
      ...c,
      classNo: c.class_no,
      homeroomCN: c.homeroom_cn_id ? teacherIdToName.value[c.homeroom_cn_id] : null,
      homeroomEN: c.homeroom_en_id ? teacherIdToName.value[c.homeroom_en_id] : null
    }))
  } finally {
    loading.value = false
  }
}

/**
 * 加载教师数据（用于下拉选择）
 */
const loadTeachers = async () => {
  try {
    const [cnRes, enRes] = await Promise.all([
      getTeachers({ type: 'CN', page_size: 200 }),
      getTeachers({ type: 'EN', page_size: 200 })
    ])
    cnTeachers.value = cnRes.data.items
    enTeachers.value = enRes.data.items
    
    // 构建ID到名字的映射
    const idMap = {}
    cnRes.data.items.forEach(t => { idMap[t.id] = t.name })
    enRes.data.items.forEach(t => { idMap[t.id] = t.name })
    teacherIdToName.value = idMap
  } catch (error) {
    // 使用 Mock 教师数据
    cnTeachers.value = [
      { id: 1, name: '郭金莉' }, { id: 2, name: '黄丽娜' }, { id: 3, name: '温惠' },
      { id: 4, name: '赵立娜' }, { id: 5, name: '李春香' }, { id: 6, name: '马昕光' }
    ]
    enTeachers.value = [
      { id: 10, name: 'Bing' }, { id: 11, name: 'Josh B' }, { id: 12, name: 'Andrew' },
      { id: 13, name: 'Stan' }, { id: 14, name: 'Cass' }
    ]
    
    // 构建ID到名字的映射
    const idMap = {}
    cnTeachers.value.forEach(t => { idMap[t.id] = t.name })
    enTeachers.value.forEach(t => { idMap[t.id] = t.name })
    teacherIdToName.value = idMap
  }
}

// 加载课表列表
const loadScheduleList = async () => {
  try {
    const res = await getScheduleList()
    const schedules = res.data.items || []
    // 查找激活的课表
    const active = schedules.find(s => s.is_active)
    if (active) {
      activeScheduleId.value = active.id
    } else if (schedules.length > 0) {
      activeScheduleId.value = schedules[0].id
    }
  } catch (error) {
    console.warn('加载课表列表失败:', error)
  }
}

// 页面加载时获取数据（先加载教师，再加载班级，因为班级需要教师ID映射）
onMounted(async () => {
  await loadTeachers()
  await loadClasses()
  loadScheduleList()
})

// 监听筛选条件变化
watch([filterType, filterDepartment], () => {
  loadClasses()
})

// 计算属性
const primaryClasses = computed(() => classes.value.filter(c => c.department === 'PRIMARY'))
const secondaryClasses = computed(() => classes.value.filter(c => c.department === 'SECONDARY'))

const getClassesByGrade = (grade, department) => {
  return classes.value.filter(c => c.grade === grade && c.department === department)
}

// 操作函数
const openAddDialog = () => {
  editingClass.value = null
  classForm.value = { 
    type: 'I', 
    grade: '', 
    classNo: 1, 
    homeroomCnId: '',
    homeroomEnId: '' 
  }
  showAddDialog.value = true
}

const editClass = (cls) => { 
  editingClass.value = cls
  classForm.value = { 
    type: cls.type,
    grade: cls.grade,
    classNo: cls.classNo || cls.class_no,
    // 将 null 转换为空字符串，与"空置"选项的 value 匹配
    homeroomCnId: cls.homeroom_cn_id ?? '',
    homeroomEnId: cls.homeroom_en_id ?? ''
  }
  showAddDialog.value = true 
}

const viewSchedule = (cls) => {
  if (!activeScheduleId.value) {
    ElMessage.warning('暂无可用的课表，请先生成排课')
    return
  }
  // 跳转到课表管理页面，并传递班级 ID
  router.push({
    path: '/timetable',
    query: {
      schedule_id: activeScheduleId.value,
      class_id: cls.id
    }
  })
}

const deleteClass = async (cls) => {
  try {
    await ElMessageBox.confirm(`确定要删除班级 ${cls.name} 吗？`, '确认删除', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    // 始终尝试调用后端 API 删除
    try {
      await deleteClassApi(cls.id)
    } catch (apiError) {
      // 如果后端删除失败，显示错误但不阻止本地删除（可能是 Mock 模式）
      console.warn('后端删除失败:', apiError.message)
      if (!useMockData.value) {
        // 如果不是 Mock 模式，则抛出错误
        throw apiError
      }
    }
    
    const index = classes.value.findIndex(c => c.id === cls.id)
    if (index > -1) {
      classes.value.splice(index, 1)
    }
    
    ElMessage.success('删除成功')
  } catch (error) {
    if (error !== 'cancel') {
      const detail = error.response?.data?.detail || error.message || '未知错误'
      ElMessage.error('删除失败: ' + detail)
    }
  }
}

const saveClass = async () => {
  // 生成班级名称
  const name = `${classForm.value.type}${classForm.value.grade}-${classForm.value.classNo}`
  const department = ['PK', 'KG', 'G1', 'G2', 'G3', 'G4', 'G5'].includes(classForm.value.grade) ? 'PRIMARY' : 'SECONDARY'
  
  const submitData = {
    name,
    type: classForm.value.type,
    grade: classForm.value.grade,
    class_no: classForm.value.classNo,
    department,
    homeroom_cn_id: classForm.value.homeroomCnId || null,
    homeroom_en_id: classForm.value.homeroomEnId || null
  }
  
  try {
    if (editingClass.value) {
      if (!useMockData.value) {
        await updateClass(editingClass.value.id, submitData)
      }
      
      const index = classes.value.findIndex(c => c.id === editingClass.value.id)
      if (index > -1) {
        classes.value[index] = { 
          ...classes.value[index], 
          ...submitData, 
          classNo: submitData.class_no,
          // 根据ID更新显示的教师姓名
          homeroomCN: submitData.homeroom_cn_id ? teacherIdToName.value[submitData.homeroom_cn_id] : null,
          homeroomEN: submitData.homeroom_en_id ? teacherIdToName.value[submitData.homeroom_en_id] : null
        }
      }
      ElMessage.success('修改成功')
    } else {
      const newClass = {
        id: Date.now(),
        ...submitData, 
        classNo: submitData.class_no,
        homeroomCN: submitData.homeroom_cn_id ? teacherIdToName.value[submitData.homeroom_cn_id] : null,
        homeroomEN: submitData.homeroom_en_id ? teacherIdToName.value[submitData.homeroom_en_id] : null
      }
      
      if (!useMockData.value) {
        const res = await createClass(submitData)
        newClass.id = res.data.id
      }
      
      classes.value.push(newClass)
      ElMessage.success('添加成功')
    }
    
    showAddDialog.value = false
    editingClass.value = null
  } catch (error) {
    // 优先使用后端返回的错误详情
    const detail = error.response?.data?.detail || error.response?.data?.message || error.message || '未知错误'
    ElMessage.error('保存失败: ' + detail)
  }
}
</script>

<style lang="scss" scoped>
.class-management { padding: 24px; }

.toolbar {
  display: flex;
  justify-content: space-between;
  margin-bottom: 24px;
  .toolbar-left { display: flex; gap: 12px; .search-input { width: 200px; } }
  .toolbar-right { display: flex; gap: 8px; }
}

.departments-container { display: flex; flex-direction: column; gap: 32px; }

.department-section {
  .department-header {
    display: flex; align-items: center; gap: 12px; margin-bottom: 16px;
    padding-bottom: 12px; border-bottom: 2px solid var(--primary-color);
    h3 { 
      font-size: 16px; font-weight: 600; color: var(--text-primary); margin: 0;
      display: flex; align-items: center; gap: 8px;
    }
    .class-count { 
      font-size: 13px; color: var(--text-secondary); 
      background: var(--bg-color); padding: 2px 10px; border-radius: 12px; 
    }
  }
}

.grade-group {
  margin-bottom: 20px;
  
  .grade-title {
    display: flex; align-items: center; gap: 8px; margin-bottom: 12px;
    .grade-name { font-size: 14px; font-weight: 600; color: var(--text-secondary); }
    .grade-count { font-size: 12px; color: var(--text-muted); }
  }
}

.classes-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; }

.class-card {
  display: flex; align-items: center; gap: 12px; padding: 14px;
  background: #fff; border-radius: 10px; border: 1px solid var(--border-color);
  cursor: pointer; transition: all 0.2s ease; position: relative;
  
  &:hover { 
    border-color: var(--primary-color); 
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08); 
    .more-btn { opacity: 1; }
  }
  
  &.type-i {
    border-left: 3px solid #2563eb;
    .class-avatar { background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%); }
  }
  
  &.type-n {
    border-left: 3px solid #16a34a;
    .class-avatar { background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%); }
  }
  
  .class-type-badge {
    position: absolute; top: 8px; right: 8px;
    font-size: 10px; font-weight: 700; color: var(--text-muted);
  }
  
  .class-avatar {
    width: 40px; height: 40px; border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    color: #fff; font-size: 16px; font-weight: 700; flex-shrink: 0;
  }
  
  .class-info {
    flex: 1; min-width: 0;
    .class-name { font-size: 14px; font-weight: 600; color: var(--text-primary); margin-bottom: 4px; }
    .class-homeroom {
      display: flex; flex-direction: column; gap: 2px;
      .homeroom-item {
        display: flex; align-items: center; gap: 4px; font-size: 11px; color: var(--text-secondary);
      }
    }
  }
  
  .more-btn { opacity: 0; transition: opacity 0.2s ease; }
}

// 空置选项样式
:deep(.empty-option) {
  color: #909399;
  font-style: italic;
}

.class-summary {
  margin-top: 24px; padding: 16px 24px;
  display: flex; gap: 32px;
  
  .summary-item {
    display: flex; align-items: center; gap: 8px;
    .label { color: var(--text-secondary); font-size: 13px; }
    .value { font-weight: 600; color: var(--primary-color); }
  }
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
