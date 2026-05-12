<template>
  <div class="layer-config">
    <div class="toolbar">
      <div class="toolbar-left">
        <h3>分层/合班课程配置</h3>
        <span class="hint">配置分层教学或合班上课，这些课程会在同一时间排课</span>
      </div>
      <div class="toolbar-right">
        <el-button type="primary" @click="openAddDialog('LAYER')">
          <el-icon><Plus /></el-icon>添加分层课程
        </el-button>
        <el-button type="success" @click="openAddDialog('COMBINE')">
          <el-icon><Plus /></el-icon>添加合班上课
        </el-button>
      </div>
    </div>

    <!-- 课程列表 -->
    <div class="layer-groups" v-loading="loading">
      <div v-if="layerGroups.length === 0 && !loading" class="empty-state">
        <el-empty description="暂无配置，请点击右上角添加" />
      </div>

      <div v-for="group in layerGroups" :key="group.id" 
        class="layer-group-card" 
        :class="{ 
          'cross-grade': group.is_cross_grade, 
          'highlight': group.is_cross_grade,
          'combine-card': group.group_type === 'COMBINE'
        }">
        <div class="group-header">
          <div class="group-title">
            <el-tag effect="dark" :type="group.group_type === 'COMBINE' ? 'success' : 'primary'">
              {{ group.subjectName }}
            </el-tag>
            <span class="title-text">
              {{ group.subjectName }}{{ group.group_type === 'COMBINE' ? '合班' : '分层' }}
            </span>
            <el-tag size="small" :type="getGroupTypeTag(group)">
              {{ getGroupTypeLabel(group) }}
            </el-tag>
          </div>
          <div class="group-actions">
            <el-button type="primary" link @click="editLayerGroup(group)">
              <el-icon><Edit /></el-icon>编辑
            </el-button>
            <el-button type="danger" link @click="deleteLayerGroup(group)">
              <el-icon><Delete /></el-icon>删除
            </el-button>
          </div>
        </div>
        <div class="group-content">
          <!-- 分层模式：显示年级和涉及班级 -->
          <div v-if="group.group_type !== 'COMBINE'" class="info-row">
            <span class="label">适用年级:</span>
            <span class="value">
              <el-tag v-for="g in group.grades" :key="g" size="small" class="grade-tag">{{ g }}</el-tag>
              <span v-if="group.is_cross_grade" class="cross-hint">（跨年级混合）</span>
            </span>
          </div>
          <div v-if="group.group_type !== 'COMBINE' && group.class_ids && group.class_ids.length > 0" class="info-row">
            <span class="label">涉及班级:</span>
            <span class="value">
              <el-tag v-for="cid in group.class_ids" :key="cid" size="small" class="grade-tag" type="warning">
                {{ getClassName(cid) }}
              </el-tag>
            </span>
          </div>
          <!-- 合班模式：显示班级 -->
          <div v-else class="info-row">
            <span class="label">合班班级:</span>
            <span class="value">
              <el-tag v-for="cid in group.class_ids" :key="cid" size="small" class="grade-tag" type="success">
                {{ getClassName(cid) }}
              </el-tag>
            </span>
          </div>
          <!-- 分层数量（仅分层模式） -->
          <div v-if="group.group_type !== 'COMBINE'" class="info-row">
            <span class="label">分层数量:</span>
            <span class="value">每年级 <strong>{{ group.layer_count }}</strong> 层</span>
          </div>
          <div class="info-row">
            <span class="label">周课时:</span>
            <span class="value">
              <strong>{{ group.weekly_hours }}</strong> 节/周 
              <span v-if="group.needs_continuous">（含连堂）</span>
            </span>
          </div>
          <div class="info-row">
            <span class="label">任课教师:</span>
            <span class="value teacher-list">
              <template v-if="group.teacher_ids && group.teacher_ids.length > 0">
                <template v-if="group.group_type === 'COMBINE'">
                  <el-tag size="small" type="success">{{ getTeacherName(group.teacher_ids[0]) }}</el-tag>
                </template>
                <template v-else>
                  <el-tag 
                    v-for="(tid, idx) in group.teacher_ids" 
                    :key="idx" 
                    size="small" 
                    :type="tid ? 'success' : 'info'"
                    class="teacher-tag"
                  >
                    第{{ idx + 1 }}层: {{ getTeacherName(tid) }}
                  </el-tag>
                </template>
              </template>
              <span v-else class="no-teacher">未配置教师</span>
            </span>
          </div>
          <el-alert v-if="group.is_cross_grade && group.group_type !== 'COMBINE'" 
            type="warning" :closable="false" show-icon class="cross-alert">
            跨年级分层约束最强：所有{{ group.layer_count }}层必须安排在完全相同的时间槽
          </el-alert>
          <el-alert v-if="group.group_type === 'COMBINE'" 
            type="info" :closable="false" show-icon class="cross-alert">
            合班上课：{{ group.class_ids?.length || 0 }}个班级将在同一时间、同一教师上课
          </el-alert>
        </div>
      </div>
    </div>

    <!-- 添加/编辑对话框 -->
    <el-dialog v-model="showAddDialog" 
      :title="dialogTitle" 
      width="650px" 
      @close="resetForm">
      <el-form :model="layerForm" label-width="100px">
        <!-- 课程类型（只读显示） -->
        <el-form-item label="课程类型">
          <el-tag :type="layerForm.group_type === 'COMBINE' ? 'success' : 'primary'" size="large">
            {{ layerForm.group_type === 'COMBINE' ? '合班上课' : '分层课程' }}
          </el-tag>
          <span class="form-hint">
            {{ layerForm.group_type === 'COMBINE' 
              ? '指定班级合并上课，同一老师教多个班' 
              : '年级内学生按能力分层，多个老师同时教' }}
          </span>
        </el-form-item>

        <el-form-item label="科目">
          <el-select v-model="layerForm.subject_id" placeholder="选择科目" @change="handleSubjectChange">
            <el-option v-for="s in subjects" :key="s.id" :label="s.name" :value="s.id" />
          </el-select>
        </el-form-item>

        <!-- 分层模式：年级选择 -->
        <template v-if="layerForm.group_type !== 'COMBINE'">
          <el-form-item label="分层类型">
            <el-radio-group v-model="layerForm.is_cross_grade">
              <el-radio :value="false">同年级分层</el-radio>
              <el-radio :value="true">跨年级分层</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="适用年级">
            <el-checkbox-group v-model="layerForm.grades" @change="onLayerGradesChange">
              <el-checkbox v-for="g in gradeOptions" :key="g" :value="g">{{ g }}</el-checkbox>
            </el-checkbox-group>
          </el-form-item>
          <el-form-item label="适用班型">
            <el-radio-group v-model="layerForm.class_type" @change="onLayerClassTypeChange">
              <el-radio value="I">国际班</el-radio>
              <el-radio value="N">综素班</el-radio>
              <el-radio value="ALL">全部</el-radio>
            </el-radio-group>
            <span class="form-hint">选择此分层组适用的班级类型</span>
          </el-form-item>
          <el-form-item v-if="layerForm.grades.length > 0" label="涉及班级">
            <div class="affected-classes">
              <el-tag v-for="c in affectedLayerClasses" :key="c.id" size="small" class="grade-tag">
                {{ c.name }}
              </el-tag>
              <span v-if="affectedLayerClasses.length === 0" class="form-hint">无匹配班级</span>
            </div>
          </el-form-item>
          <el-form-item label="分层数量">
            <el-input-number v-model="layerForm.layer_count" :min="2" :max="10" />
            <span class="form-hint">层（修改数量后请重新配置教师）</span>
          </el-form-item>
        </template>

        <!-- 合班模式：班级选择 -->
        <template v-else>
          <el-form-item label="选择年级">
            <el-select v-model="selectedGradeForCombine" placeholder="先选择年级" @change="onCombineGradeChange">
              <el-option v-for="g in gradeOptions" :key="g" :label="g" :value="g" />
            </el-select>
            <span class="form-hint">选择年级后可选择要合班的班级</span>
          </el-form-item>
          <el-form-item label="合班班级">
            <el-checkbox-group v-model="layerForm.class_ids" :disabled="!selectedGradeForCombine">
              <el-checkbox 
                v-for="c in filteredClassesForCombine" 
                :key="c.id" 
                :value="c.id"
              >
                {{ c.name }}
              </el-checkbox>
            </el-checkbox-group>
            <div v-if="!selectedGradeForCombine" class="form-hint">请先选择年级</div>
            <div v-else-if="filteredClassesForCombine.length === 0" class="form-hint">该年级暂无班级</div>
          </el-form-item>
        </template>

        <!-- 分层模式：多教师选择 -->
        <el-form-item v-if="layerForm.group_type !== 'COMBINE'" label="任课教师">
          <div class="teacher-select-list">
            <div v-for="(_, idx) in layerForm.layer_count" :key="idx" class="teacher-select-item">
              <span class="layer-label">第{{ idx + 1 }}层:</span>
              <el-select 
                v-model="layerForm.teacher_ids[idx]" 
                placeholder="选择教师" 
                clearable 
                filterable
                style="width: 200px"
              >
                <el-option v-for="t in teachers" :key="t.id" :label="t.name" :value="t.id">
                  <span>{{ t.name }}</span>
                  <span style="color: #999; font-size: 12px; margin-left: 8px">
                    {{ t.type === 'CN' ? '中教' : '外教' }}
                  </span>
                </el-option>
              </el-select>
            </div>
          </div>
          <div class="form-hint">为每个层级指定一位任课教师，他们将在同一时间上课</div>
        </el-form-item>

        <!-- 合班模式：单教师选择 -->
        <el-form-item v-else label="任课教师">
          <el-select 
            v-model="layerForm.teacher_ids[0]" 
            placeholder="选择教师" 
            clearable 
            filterable
            style="width: 250px"
          >
            <el-option v-for="t in teachers" :key="t.id" :label="t.name" :value="t.id">
              <span>{{ t.name }}</span>
              <span style="color: #999; font-size: 12px; margin-left: 8px">
                {{ t.type === 'CN' ? '中教' : '外教' }}
              </span>
            </el-option>
          </el-select>
          <span class="form-hint">合班由一位教师负责</span>
        </el-form-item>
        
        <el-form-item label="周课时">
          <el-input-number v-model="layerForm.weekly_hours" :min="1" :max="10" />
          <span class="form-hint">节/周</span>
        </el-form-item>
        <el-form-item label="需要连堂">
          <el-switch v-model="layerForm.needs_continuous" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="saveLayerGroup">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Edit, Delete } from '@element-plus/icons-vue'
import { getLayerGroups, createLayerGroup, updateLayerGroup, deleteLayerGroup as deleteLayerGroupApi } from '@/api/layers'
import { getSubjects } from '@/api/subjects'
import { getTeachers } from '@/api/teachers'
import { getClasses } from '@/api/classes'

const showAddDialog = ref(false)
const loading = ref(false)
const layerGroups = ref([])
const subjects = ref([])
const teachers = ref([])
const classList = ref([])
const isEditing = ref(false)
const editingId = ref(null)
const selectedGradeForCombine = ref('')

const gradeOptions = ['G1', 'G2', 'G3', 'G4', 'G5', 'G6', 'G7', 'G8', 'G9', 'G10', 'G11']

const layerForm = ref({
  group_type: 'LAYER',  // LAYER 或 COMBINE
  subject_id: null,
  subject_name: '',
  grades: [],
  class_ids: [],        // 合班时使用；分层模式下也会自动填充
  class_type: 'ALL',    // 分层模式的班型筛选：I/N/ALL
  layer_count: 2,
  teacher_ids: [],
  is_cross_grade: false,
  weekly_hours: 5,
  needs_continuous: true,
  description: ''
})

// 对话框标题
const dialogTitle = computed(() => {
  if (isEditing.value) {
    return layerForm.value.group_type === 'COMBINE' ? '编辑合班上课' : '编辑分层课程'
  }
  return layerForm.value.group_type === 'COMBINE' ? '添加合班上课' : '添加分层课程'
})

// 合班模式下筛选当前年级的班级
const filteredClassesForCombine = computed(() => {
  if (!selectedGradeForCombine.value) return []
  return classList.value.filter(c => c.grade === selectedGradeForCombine.value)
})

// 根据分层数量动态生成教师选择数组
watch(() => layerForm.value.layer_count, (newCount, oldCount) => {
  if (layerForm.value.group_type === 'COMBINE') return
  
  const currentIds = layerForm.value.teacher_ids || []
  if (newCount > currentIds.length) {
    layerForm.value.teacher_ids = [...currentIds, ...Array(newCount - currentIds.length).fill(null)]
  } else if (newCount < currentIds.length) {
    layerForm.value.teacher_ids = currentIds.slice(0, newCount)
  }
}, { immediate: true })

// 打开添加对话框
const openAddDialog = (type) => {
  resetForm()
  layerForm.value.group_type = type
  if (type === 'COMBINE') {
    layerForm.value.layer_count = 1
    layerForm.value.teacher_ids = [null]
  }
  showAddDialog.value = true
}

const resetForm = () => {
  layerForm.value = {
    group_type: 'LAYER',
    subject_id: null,
    subject_name: '',
    grades: [],
    class_ids: [],
    class_type: 'ALL',
    layer_count: 2,
    teacher_ids: [null, null],
    is_cross_grade: false,
    weekly_hours: 5,
    needs_continuous: true,
    description: ''
  }
  selectedGradeForCombine.value = ''
  isEditing.value = false
  editingId.value = null
}

// 获取教师名称
const getTeacherName = (teacherId) => {
  if (!teacherId) return '未指定'
  const teacher = teachers.value.find(t => t.id === teacherId)
  return teacher ? teacher.name : '未知教师'
}

// 获取班级名称
const getClassName = (classId) => {
  if (!classId) return '未知班级'
  const cls = classList.value.find(c => c.id === classId)
  return cls ? cls.name : '未知班级'
}

// 获取分组类型标签
const getGroupTypeTag = (group) => {
  if (group.group_type === 'COMBINE') return 'success'
  if (group.is_cross_grade) return 'danger'
  return 'info'  // 默认使用 info 而不是空字符串
}

const getGroupTypeLabel = (group) => {
  if (group.group_type === 'COMBINE') return '合班上课'
  if (group.is_cross_grade) return '跨年级分层'
  return '同年级分层'
}

// 加载科目数据
const loadSubjects = async () => {
  try {
    const res = await getSubjects({ page: 1, page_size: 100 })
    subjects.value = res.data.items
  } catch (error) {
    console.error('加载科目失败', error)
  }
}

// 加载教师数据
const loadTeachers = async () => {
  try {
    const res = await getTeachers({ page: 1, page_size: 200 })
    teachers.value = res.data.items
  } catch (error) {
    console.error('加载教师失败', error)
  }
}

// 加载班级数据
const loadClasses = async () => {
  try {
    const res = await getClasses({ page: 1, page_size: 200 })
    classList.value = res.data.items.map(c => {
      let grade = c.grade
      if (!grade && c.name) {
        const match = c.name.match(/[IN]?(PK|KG|G\d+)/i)
        if (match) grade = match[1].toUpperCase()
      }
      return { id: c.id, name: c.name, grade: grade, type: c.type || 'I' }
    }).filter(c => c.grade)
  } catch (error) {
    console.error('加载班级失败', error)
  }
}

// 分层模式下：根据选中年级和班型，计算涉及的班级列表
const affectedLayerClasses = computed(() => {
  if (layerForm.value.group_type === 'COMBINE') return []
  if (layerForm.value.grades.length === 0) return []
  
  return classList.value.filter(c => {
    const gradeMatch = layerForm.value.grades.includes(c.grade)
    if (!gradeMatch) return false
    if (layerForm.value.class_type === 'ALL') return true
    return c.type === layerForm.value.class_type
  })
})

// 分层模式年级变化时，更新 class_ids
const onLayerGradesChange = () => {
  updateLayerClassIds()
}

// 分层模式班型变化时，更新 class_ids
const onLayerClassTypeChange = () => {
  updateLayerClassIds()
}

// 更新分层模式的 class_ids（自动从年级+班型推算）
const updateLayerClassIds = () => {
  if (layerForm.value.group_type === 'COMBINE') return
  layerForm.value.class_ids = affectedLayerClasses.value.map(c => c.id)
}

// 加载分层组数据
const loadLayerGroups = async () => {
  loading.value = true
  try {
    const res = await getLayerGroups()
    layerGroups.value = res.data.items.map(group => ({
      ...group,
      subjectName: subjects.value.find(s => s.id === group.subject_id)?.name || '未知科目',
      teacherNames: (group.teacher_ids || []).map(tid => getTeacherName(tid))
    }))
  } catch (error) {
    ElMessage.error('加载课程配置失败: ' + error.message)
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadSubjects(), loadTeachers(), loadClasses()])
  loadLayerGroups()
})

const handleSubjectChange = (val) => {
  const subject = subjects.value.find(s => s.id === val)
  if (subject) {
    layerForm.value.subject_name = subject.name
  }
}

// 合班模式年级变化时清空班级选择
const onCombineGradeChange = () => {
  layerForm.value.class_ids = []
  // 同时更新 grades 字段
  layerForm.value.grades = selectedGradeForCombine.value ? [selectedGradeForCombine.value] : []
}

const editLayerGroup = (group) => {
  isEditing.value = true
  editingId.value = group.id
  
  const groupType = group.group_type || 'LAYER'
  let teacherIds = group.teacher_ids || []
  
  if (groupType === 'COMBINE') {
    // 合班模式只有一个老师
    if (teacherIds.length === 0) teacherIds = [null]
    // 从 class_ids 推断年级
    if (group.class_ids && group.class_ids.length > 0) {
      const firstClass = classList.value.find(c => c.id === group.class_ids[0])
      if (firstClass) {
        selectedGradeForCombine.value = firstClass.grade
      }
    }
  } else {
    // 分层模式
    if (teacherIds.length < group.layer_count) {
      teacherIds = [...teacherIds, ...Array(group.layer_count - teacherIds.length).fill(null)]
    } else if (teacherIds.length > group.layer_count) {
      teacherIds = teacherIds.slice(0, group.layer_count)
    }
  }
  
  // 推断班型：从已有 class_ids 中推断
  let classType = 'ALL'
  const existingClassIds = group.class_ids || []
  if (existingClassIds.length > 0 && groupType !== 'COMBINE') {
    const matchedClasses = classList.value.filter(c => existingClassIds.includes(c.id))
    const types = new Set(matchedClasses.map(c => c.type))
    if (types.size === 1) {
      classType = types.values().next().value  // 只有一种班型
    }
  }
  
  layerForm.value = {
    group_type: groupType,
    subject_id: group.subject_id,
    subject_name: group.subjectName,
    grades: [...(group.grades || [])],
    class_ids: [...(group.class_ids || [])],
    class_type: classType,
    layer_count: group.layer_count || 1,
    teacher_ids: teacherIds,
    is_cross_grade: group.is_cross_grade || false,
    weekly_hours: group.weekly_hours,
    needs_continuous: group.needs_continuous,
    description: group.description || ''
  }
  showAddDialog.value = true
}

const saveLayerGroup = async () => {
  if (!layerForm.value.subject_id) {
    ElMessage.warning('请选择科目')
    return
  }
  
  const isCombine = layerForm.value.group_type === 'COMBINE'
  
  if (isCombine) {
    // 合班模式验证
    if (!selectedGradeForCombine.value) {
      ElMessage.warning('请先选择年级')
      return
    }
    if (layerForm.value.class_ids.length < 2) {
      ElMessage.warning('合班至少需要选择2个班级')
      return
    }
    if (!layerForm.value.teacher_ids[0]) {
      ElMessage.warning('请选择任课教师')
      return
    }
  } else {
    // 分层模式验证
    if (layerForm.value.grades.length === 0) {
      ElMessage.warning('请选择适用年级')
      return
    }
    // 检查是否至少配置了一个教师
    const hasTeacher = layerForm.value.teacher_ids.some(id => id && id > 0)
    if (!hasTeacher) {
      ElMessage.warning('请至少为一个层级配置教师')
      return
    }
  }
  
  // 分层模式下，确保 class_ids 已更新
  if (!isCombine) {
    updateLayerClassIds()
  }
  
  const data = {
    group_type: layerForm.value.group_type,
    subject_id: layerForm.value.subject_id,
    grades: layerForm.value.grades,
    class_ids: layerForm.value.class_ids,
    layer_count: isCombine ? 1 : layerForm.value.layer_count,
    teacher_ids: layerForm.value.teacher_ids.filter(id => id !== null && id > 0),
    is_cross_grade: isCombine ? false : layerForm.value.is_cross_grade,
    weekly_hours: layerForm.value.weekly_hours,
    needs_continuous: layerForm.value.needs_continuous,
    description: layerForm.value.description
  }
  
  try {
    if (isEditing.value && editingId.value) {
      await updateLayerGroup(editingId.value, data)
      ElMessage.success('更新成功')
    } else {
      await createLayerGroup(data)
      ElMessage.success('创建成功')
    }
    
    showAddDialog.value = false
    loadLayerGroups()
    resetForm()
  } catch (error) {
    ElMessage.error('保存失败: ' + error.message)
  }
}

const deleteLayerGroup = async (group) => {
  const typeName = group.group_type === 'COMBINE' ? '合班配置' : '分层课程'
  try {
    await ElMessageBox.confirm(`确定要删除这个${typeName}吗？`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await deleteLayerGroupApi(group.id)
    ElMessage.success('删除成功')
    loadLayerGroups()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败: ' + error.message)
    }
  }
}
</script>

<style lang="scss" scoped>
.layer-config {
  padding: 24px;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
  
  .toolbar-left {
    h3 {
      font-size: 16px;
      font-weight: 600;
      margin-bottom: 4px;
    }
    .hint {
      font-size: 13px;
      color: var(--text-secondary);
    }
  }
  
  .toolbar-right {
    display: flex;
    gap: 12px;
  }
}

.layer-groups {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
}

.layer-group-card {
  background: #fff;
  border: 1px solid var(--border-color);
  border-radius: 12px;
  overflow: hidden;
  transition: all 0.2s ease;
  
  &:hover {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  }
  
  &.highlight {
    border-color: #fecaca;
    background: linear-gradient(135deg, #fff 0%, #fef2f2 100%);
  }
  
  &.combine-card {
    border-color: #a7f3d0;
    background: linear-gradient(135deg, #fff 0%, #ecfdf5 100%);
  }
  
  .group-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 20px;
    background: var(--bg-color);
    border-bottom: 1px solid var(--border-color);
    
    .group-title {
      display: flex;
      align-items: center;
      gap: 10px;
      
      .title-text {
        font-weight: 600;
        font-size: 15px;
      }
    }
  }
  
  .group-content {
    padding: 20px;
    
    .info-row {
      display: flex;
      align-items: flex-start;
      margin-bottom: 12px;
      
      &:last-child {
        margin-bottom: 0;
      }
      
      .label {
        width: 80px;
        color: var(--text-secondary);
        font-size: 13px;
        flex-shrink: 0;
      }
      
      .value {
        flex: 1;
        font-size: 13px;
        
        strong {
          color: var(--primary-color);
          font-size: 15px;
        }
        
        .grade-tag {
          margin-right: 4px;
          margin-bottom: 4px;
        }
        
        .cross-hint {
          color: #dc2626;
          font-size: 12px;
          margin-left: 8px;
        }
      }
    }
    
    .cross-alert {
      margin-top: 12px;
    }
  }
}

.form-hint {
  margin-left: 8px;
  color: var(--text-secondary);
  font-size: 12px;
}

// 教师选择列表样式
.teacher-select-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  
  .teacher-select-item {
    display: flex;
    align-items: center;
    gap: 12px;
    
    .layer-label {
      width: 60px;
      font-size: 13px;
      color: var(--text-secondary);
    }
  }
}

// 教师标签样式
.teacher-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  
  .teacher-tag {
    margin: 0;
  }
  
  .no-teacher {
    color: var(--text-secondary);
    font-size: 13px;
  }
}

@media (max-width: 1000px) {
  .layer-groups {
    grid-template-columns: 1fr;
  }
}
</style>
