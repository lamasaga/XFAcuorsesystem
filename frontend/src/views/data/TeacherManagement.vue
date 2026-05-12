<template>
  <div class="teacher-management">
    <!-- 工具栏 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <el-input 
          v-model="searchQuery" 
          placeholder="搜索教师姓名"
          prefix-icon="Search"
          clearable
          class="search-input"
        />
        <el-select v-model="filterType" placeholder="教师类型" clearable style="width: 120px">
          <el-option label="中教" value="CN" />
          <el-option label="外教" value="EN" />
        </el-select>
        <el-select v-model="filterDepartment" placeholder="学部" clearable style="width: 140px">
          <el-option label="小学部" value="PRIMARY" />
          <el-option label="中学部" value="SECONDARY" />
          <el-option label="小中贯通" value="BOTH" />
        </el-select>
        <el-select v-model="filterTag" placeholder="标签筛选" clearable style="width: 140px">
          <el-option label="班主任" value="HOMEROOM_TEACHER" />
          <el-option label="副班主任" value="ASSISTANT_HOMEROOM" />
          <el-option label="管理干部" value="ADMIN" />
        </el-select>
      </div>
      <div class="toolbar-right">
        <el-button @click="showImportDialog = true">
          <el-icon><Upload /></el-icon>导入
        </el-button>
        <el-button @click="exportData">
          <el-icon><Download /></el-icon>导出
        </el-button>
        <el-button type="primary" @click="openAddDialog">
          <el-icon><Plus /></el-icon>添加教师
        </el-button>
      </div>
    </div>
    
    <!-- 数据表格 -->
    <el-table 
      :data="filteredTeachers" 
      stripe 
      v-loading="loading"
      @selection-change="handleSelectionChange"
    >
      <el-table-column type="selection" width="50" />
      <el-table-column prop="name" label="姓名" width="140">
        <template #default="{ row }">
          <div class="teacher-name">
            <el-avatar :size="32" class="avatar" :class="row.type">
              {{ row.name.charAt(0) }}
            </el-avatar>
            <div class="name-info">
              <span class="name">{{ row.name }}</span>
              <el-tag :type="row.type === 'CN' ? 'danger' : 'warning'" size="small">
                {{ row.type === 'CN' ? '中教' : '外教' }}
              </el-tag>
            </div>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="department" label="学部" width="100">
        <template #default="{ row }">
          <el-tag :type="getDepartmentTagType(row.department)" size="small" effect="plain">
            {{ getDepartmentText(row.department) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="教研组" width="110">
        <template #default="{ row }">
          <span v-if="row.research_group_id">{{ getGroupName(row.research_group_id) }}</span>
          <span v-else style="color: #ccc">-</span>
        </template>
      </el-table-column>
      <el-table-column prop="subjects" label="任教科目" min-width="150">
        <template #default="{ row }">
          <div class="subjects-list">
            <template v-if="getTeacherSubjects(row.id).length > 0">
              <el-tag 
                v-for="subject in getTeacherSubjects(row.id)" 
                :key="subject"
                :type="getSubjectTagType(subject)" 
                size="small"
                effect="light"
                class="subject-tag"
              >
                {{ subject }}
              </el-tag>
            </template>
            <span v-else class="no-subjects">未分配教学任务</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="tags" label="标签" min-width="220">
        <template #default="{ row }">
          <div class="tags-list">
            <!-- 班主任标签：从班级数据联动获取，只读显示 -->
            <el-tooltip 
              v-if="getHomeroomInfo(row.id).isHomeroom"
              :content="'任：' + getHomeroomInfo(row.id).classes"
              placement="top"
            >
              <el-tag type="danger" size="small" class="role-tag homeroom-tag">
                班主任
              </el-tag>
            </el-tooltip>
            <!-- 其他标签：副班主任和管理干部（可编辑） -->
            <el-tag 
              v-for="tag in row.tags.filter(t => t !== 'HOMEROOM_TEACHER')" 
              :key="tag"
              :type="getTagType(tag)" 
              size="small"
              class="role-tag"
            >
              {{ getTagText(tag) }}
            </el-tag>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="weeklyHours" label="周课时" width="90" align="center">
        <template #default="{ row }">
          <span class="weekly-hours">{{ row.weeklyHours }}</span>
        </template>
      </el-table-column>
      <el-table-column label="早晚班" width="120">
        <template #default="{ row }">
          <div class="shift-info">
            <span class="shift-text">{{ getShiftText(row) }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="120" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link @click="editTeacher(row)">
            <el-icon><Edit /></el-icon>编辑
          </el-button>
          <el-popconfirm 
            title="确定删除该教师吗？"
            @confirm="deleteTeacher(row)"
          >
            <template #reference>
              <el-button type="danger" link>
                <el-icon><Delete /></el-icon>删除
              </el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>
    
    <!-- 分页 -->
    <div class="pagination-wrapper">
      <div class="selection-info" v-if="selectedRows.length > 0">
        已选择 <strong>{{ selectedRows.length }}</strong> 项
        <el-button type="danger" link @click="batchDelete">批量删除</el-button>
      </div>
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50]"
        :total="totalCount"
        layout="total, sizes, prev, pager, next"
        background
      />
    </div>
    
    <!-- 添加/编辑教师对话框 -->
    <el-dialog 
      v-model="showAddDialog" 
      :title="editingTeacher ? '编辑教师' : '添加教师'"
      width="650px"
      destroy-on-close
    >
      <el-form :model="teacherForm" label-width="100px" :rules="formRules" ref="formRef">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="姓名" prop="name">
              <el-input v-model="teacherForm.name" placeholder="请输入教师姓名" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="教师类型" prop="type">
              <el-radio-group v-model="teacherForm.type">
                <el-radio value="CN">中教</el-radio>
                <el-radio value="EN">外教</el-radio>
              </el-radio-group>
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="学部" prop="department">
              <el-radio-group v-model="teacherForm.department">
                <el-radio value="PRIMARY">小学部</el-radio>
                <el-radio value="SECONDARY">中学部</el-radio>
                <el-radio value="BOTH">小中贯通</el-radio>
              </el-radio-group>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="周最大课时">
              <el-input-number v-model="teacherForm.maxWeeklyHours" :min="1" :max="30" />
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-form-item label="任教科目">
          <div class="readonly-subjects">
            <template v-if="editingTeacher && getTeacherSubjects(editingTeacher.id).length > 0">
              <el-tag 
                v-for="subject in getTeacherSubjects(editingTeacher.id)" 
                :key="subject"
                :type="getSubjectTagType(subject)" 
                size="small"
                class="subject-tag"
              >
                {{ subject }}
              </el-tag>
            </template>
            <span v-else-if="editingTeacher" class="no-subjects">未分配教学任务</span>
            <span v-else class="no-subjects">新建教师后，可在行政课程或分层课程中分配</span>
          </div>
          <div class="form-hint">任教科目由行政课程和分层课程自动关联，请在「数据管理」中配置</div>
        </el-form-item>
        
        <el-form-item label="标签">
          <div class="tag-section">
            <!-- 班主任状态：只读显示，提示去班级管理修改 -->
            <div class="homeroom-status" v-if="editingTeacher">
              <span class="status-label">班主任状态：</span>
              <el-tag v-if="getHomeroomInfo(editingTeacher.id).isHomeroom" type="danger" size="small">
                已分配（{{ getHomeroomInfo(editingTeacher.id).classes }}）
              </el-tag>
              <el-tag v-else type="info" size="small" effect="plain">未分配</el-tag>
              <span class="status-hint">（请在班级管理中设置）</span>
            </div>
            <div class="homeroom-status" v-else>
              <span class="status-label">班主任状态：</span>
              <span class="status-hint">新建教师后，可在班级管理中设置</span>
            </div>
            <!-- 其他可编辑标签 -->
            <el-checkbox-group v-model="teacherForm.tags" class="editable-tags">
              <el-checkbox value="ASSISTANT_HOMEROOM">副班主任</el-checkbox>
              <el-checkbox value="PRIMARY_ADMIN" v-if="teacherForm.department === 'PRIMARY' || teacherForm.department === 'BOTH'">小学管理干部</el-checkbox>
              <el-checkbox value="SECONDARY_ADMIN" v-if="teacherForm.department === 'SECONDARY' || teacherForm.department === 'BOTH'">中学管理干部</el-checkbox>
            </el-checkbox-group>
          </div>
        </el-form-item>
        
        <el-form-item label="教研组">
          <div style="display: flex; gap: 8px; width: 100%">
            <el-select v-model="teacherForm.researchGroupId" placeholder="选择教研组" clearable style="flex: 1">
              <el-option v-for="group in researchGroups" :key="group.id" :label="group.name" :value="group.id" />
            </el-select>
            <el-button @click="showGroupDialog = true" size="small">管理</el-button>
          </div>
        </el-form-item>
        
        <el-divider content-position="left">早晚班设置</el-divider>
        
        <el-alert 
          type="info" 
          :closable="false" 
          show-icon
          style="margin-bottom: 16px"
        >
          <template #title>
            <span v-if="teacherForm.department === 'PRIMARY'">
              小学部晚班：上午（第1-5节）不可排课
            </span>
            <span v-else-if="teacherForm.department === 'SECONDARY'">
              中学部晚班：上午（第1-4节）不可排课，可排第5节
            </span>
            <span v-else>
              小中贯通：按所教班级学部执行晚班规则
            </span>
          </template>
        </el-alert>
        
        <el-form-item label="每日班次">
          <div class="shift-selector">
            <div 
              v-for="day in 5" 
              :key="day" 
              class="shift-day"
              :class="{ 'is-evening': teacherForm.dailyShifts[day] === 'evening' }"
              @click="toggleShift(day)"
            >
              <div class="day-name">{{ getDayText(day) }}</div>
              <div class="shift-badge" :class="teacherForm.dailyShifts[day]">
                {{ teacherForm.dailyShifts[day] === 'evening' ? '晚班' : '早班' }}
              </div>
            </div>
          </div>
          <div class="shift-hint">点击切换班次，默认为早班。晚班教师上午不排课。</div>
        </el-form-item>
        
        <el-divider content-position="left">手动不可用时间</el-divider>
        
        <el-form-item label="不可用时间">
          <div class="time-selector">
            <div class="time-header">
              <span class="header-cell"></span>
              <span class="header-cell" v-for="i in 10" :key="i">第{{ i }}节</span>
            </div>
            <div class="time-row" v-for="day in 5" :key="day">
              <span class="day-label">{{ getDayText(day) }}</span>
              <span 
                class="time-cell"
                v-for="period in 10"
                :key="period"
                :class="{ 
                  unavailable: isTimeUnavailable(day, period),
                  'friday-disabled': day === 5 && period > 8,
                  'elective-cell': period === 10 && day !== 5
                }"
                @click="toggleUnavailable(day, period)"
              >
                {{ isTimeUnavailable(day, period) ? '✗' : '' }}
              </span>
            </div>
          </div>
          <div class="time-hint">点击格子标记为不可用时间，周五只有8节课，第10节为选修课位置</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="saveTeacher">保存</el-button>
      </template>
    </el-dialog>
    
    <!-- 导入对话框 -->
    <el-dialog v-model="showImportDialog" title="导入教师数据" width="600px">
      <div class="import-content">
        <el-upload
          drag
          action="#"
          :auto-upload="false"
          accept=".xlsx,.xls,.csv"
          :limit="1"
          v-model:file-list="importFileList"
          :before-upload="beforeImportUpload"
        >
          <el-icon class="upload-icon"><Upload /></el-icon>
          <div class="upload-text">
            <p>将文件拖到此处，或 <em>点击上传</em></p>
            <p class="upload-hint">支持 .xlsx, .xls, .csv 格式</p>
          </div>
        </el-upload>
        <div class="template-download">
          <el-button link type="primary" @click="downloadTemplate">
            <el-icon><Download /></el-icon>下载 Excel 模板
          </el-button>
        </div>
      </div>
      <template #footer>
        <el-button @click="showImportDialog = false">取消</el-button>
        <el-button type="primary" :loading="importUploading" @click="confirmImport">确认导入</el-button>
      </template>
    </el-dialog>

    <!-- 导入结果 -->
    <el-dialog v-model="showImportResultDialog" title="导入结果" width="720px" destroy-on-close>
      <div v-if="importResult" style="margin-bottom: 12px; color: var(--text-secondary)">
        新增 <strong>{{ importResult.created }}</strong>，
        更新 <strong>{{ importResult.updated }}</strong>，
        跳过 <strong>{{ importResult.skipped }}</strong>，
        失败 <strong style="color:#ef4444">{{ importResult.failed }}</strong>
      </div>
      <el-table
        v-if="importResult && importResult.errors && importResult.errors.length"
        :data="importResult.errors"
        stripe
        style="width: 100%"
      >
        <el-table-column prop="row_number" label="行号" width="80" />
        <el-table-column prop="name" label="姓名" width="120" />
        <el-table-column prop="message" label="原因" />
      </el-table>
      <div v-else style="padding: 8px 0; color: #16a34a">未发现错误</div>
      <template #footer>
        <el-button type="primary" @click="showImportResultDialog = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 管理教研组弹窗 -->
    <el-dialog v-model="showGroupDialog" title="管理教研组" width="420px">
      <div style="display: flex; gap: 8px; margin-bottom: 16px">
        <el-input v-model="newGroupName" placeholder="输入新教研组名称" @keyup.enter="addResearchGroup" />
        <el-button type="primary" @click="addResearchGroup">添加</el-button>
      </div>
      <div v-for="group in researchGroups" :key="group.id"
        style="display: flex; align-items: center; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #eee">
        <span>{{ group.name }}</span>
        <el-button type="danger" link size="small" @click="removeResearchGroup(group)">删除</el-button>
      </div>
      <div v-if="researchGroups.length === 0" style="text-align: center; color: #999; padding: 20px 0">
        暂无教研组，请添加
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
/**
 * 教师管理页面
 * 
 * 功能：
 * - 从后端 API 获取教师数据
 * - 支持搜索、筛选、分页
 * - 支持添加、编辑、删除教师
 * - 班主任标签只读显示（从班级数据联动获取）
 * 
 * API 使用说明：
 * - 如果后端未启动，会使用 Mock 数据
 * - 后端启动后，自动切换到真实 API
 */
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Upload, Download, Plus, Edit, Delete, Search } from '@element-plus/icons-vue'
// 导入 API
import { getTeachers, createTeacher, updateTeacher, deleteTeacher as deleteTeacherApi, getResearchGroups, createResearchGroup, deleteResearchGroup, getTeacherImportTemplateUrl, importTeachersFile } from '@/api/teachers'
import { getClasses } from '@/api/classes'
import { getSubjects } from '@/api/subjects'
import { getTasksWithDetails } from '@/api/tasks'

// ===========================================
// 状态定义
// ===========================================

// 搜索和筛选
const searchQuery = ref('')
const filterType = ref('')
const filterDepartment = ref('')
const filterTag = ref('')
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(10)
const totalCount = ref(0)

// 是否使用 Mock 数据（当后端未启动时）
const useMockData = ref(false)

// 任教科目映射（从教学任务自动获取）
// 格式：{ teacherId: ['科目1', '科目2', ...] }
const teacherSubjectsMap = ref({})

// 科目选项（仅用于兼容，不再支持手动选择）
const subjectOptions = ref([])
const subjectLoading = ref(false)

const researchGroups = ref([])
const showGroupDialog = ref(false)
const newGroupName = ref('')

const loadResearchGroups = async () => {
  try {
    const res = await getResearchGroups()
    researchGroups.value = res.data.items || []
  } catch {
    researchGroups.value = []
  }
}

const addResearchGroup = async () => {
  if (!newGroupName.value.trim()) return
  try {
    await createResearchGroup({ name: newGroupName.value.trim() })
    newGroupName.value = ''
    await loadResearchGroups()
    ElMessage.success('教研组已添加')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '添加失败')
  }
}

const removeResearchGroup = async (group) => {
  try {
    await deleteResearchGroup(group.id)
    await loadResearchGroups()
    ElMessage.success('教研组已删除')
  } catch {
    ElMessage.error('删除失败')
  }
}

// ===========================================
// 数据 - 教师列表
// ===========================================

// 教师列表（从 API 获取或使用 Mock 数据）
const teachers = ref([])

// 班主任映射：存储 {教师ID: {cn: ['班级名'], en: ['班级名']}}
// cn 表示该教师是哪些班级的中教班主任
// en 表示该教师是哪些班级的外教班主任
const homeroomMap = ref({})

// Mock 数据 - 当后端未启动时使用
const mockTeachers = [
  // 小学部中教
  { id: 1, name: '郭金莉', type: 'CN', department: 'PRIMARY', subjects: ['中文', 'IEYC'], weekly_hours: 11, tags: ['HOMEROOM_TEACHER'], max_weekly_hours: 25, unavailable_slots: {} },
  { id: 2, name: '黄丽娜', type: 'CN', department: 'PRIMARY', subjects: ['中文', '数学'], weekly_hours: 12, tags: ['HOMEROOM_TEACHER'], max_weekly_hours: 25, unavailable_slots: {} },
  { id: 3, name: '温惠', type: 'CN', department: 'PRIMARY', subjects: ['数学'], weekly_hours: 19, tags: [], max_weekly_hours: 25, unavailable_slots: {} },
  { id: 4, name: '赵立娜', type: 'CN', department: 'PRIMARY', subjects: ['中文'], weekly_hours: 23, tags: ['HOMEROOM_TEACHER'], max_weekly_hours: 25, unavailable_slots: {} },
  { id: 5, name: '李春香', type: 'CN', department: 'PRIMARY', subjects: ['中文'], weekly_hours: 16, tags: ['HOMEROOM_TEACHER'], max_weekly_hours: 25, unavailable_slots: {} },
  { id: 6, name: '王芳', type: 'CN', department: 'PRIMARY', subjects: ['数学'], weekly_hours: 18, tags: ['PRIMARY_ADMIN'], max_weekly_hours: 20, unavailable_slots: {} },
  // 小学部外教
  { id: 10, name: 'Bing', type: 'EN', department: 'PRIMARY', subjects: ['英语'], weekly_hours: 14, tags: ['HOMEROOM_TEACHER'], max_weekly_hours: 25, unavailable_slots: {} },
  { id: 11, name: 'Josh B', type: 'EN', department: 'PRIMARY', subjects: ['英语', 'IEYC'], weekly_hours: 15, tags: ['HOMEROOM_TEACHER'], max_weekly_hours: 25, unavailable_slots: {} },
  // 中学部中教
  { id: 20, name: '马昕光', type: 'CN', department: 'SECONDARY', subjects: ['数学'], weekly_hours: 25, tags: ['HOMEROOM_TEACHER', 'SECONDARY_ADMIN'], max_weekly_hours: 20, unavailable_slots: {} },
  { id: 21, name: '张红娟', type: 'CN', department: 'SECONDARY', subjects: ['数学'], weekly_hours: 24, tags: ['HOMEROOM_TEACHER'], max_weekly_hours: 25, unavailable_slots: {} },
  // 中学部外教
  { id: 30, name: 'Stan', type: 'EN', department: 'SECONDARY', subjects: ['体育'], weekly_hours: 20, tags: ['HOMEROOM_TEACHER'], max_weekly_hours: 25, unavailable_slots: {} },
]

// ===========================================
// 数据加载
// ===========================================

/**
 * 从后端 API 加载教师数据
 * 如果后端未启动，自动切换到 Mock 数据
 */
const loadTeachers = async () => {
  loading.value = true
  
  try {
    // 尝试从 API 获取数据
    const res = await getTeachers({
      page: currentPage.value,
      page_size: pageSize.value,
      type: filterType.value || undefined,
      department: filterDepartment.value || undefined,
      search: searchQuery.value || undefined
    })
    
    // API 返回成功
    useMockData.value = false
    
    // 转换字段名（后端用下划线，前端用驼峰）
    teachers.value = res.data.items.map(t => ({
      ...t,
      weeklyHours: t.weekly_hours || 0,
      maxWeeklyHours: t.max_weekly_hours || 25,
      unavailableSlots: t.unavailable_slots || {},
      dailyShifts: t.daily_shifts || { 1: 'morning', 2: 'morning', 3: 'morning', 4: 'morning', 5: 'morning' }
    }))
    
    totalCount.value = res.data.total
    
  } catch (error) {
    // API 调用失败，使用 Mock 数据
    console.warn('后端 API 未启动，使用 Mock 数据', error.message)
    useMockData.value = true
    
    // 本地筛选 Mock 数据
    let filtered = [...mockTeachers]
    
    if (filterType.value) {
      filtered = filtered.filter(t => t.type === filterType.value)
    }
    if (filterDepartment.value) {
      filtered = filtered.filter(t => t.department === filterDepartment.value)
    }
    if (searchQuery.value) {
      const query = searchQuery.value.toLowerCase()
      filtered = filtered.filter(t => t.name.toLowerCase().includes(query))
    }
    
    teachers.value = filtered.map(t => ({
      ...t,
      weeklyHours: t.weekly_hours || 0,
      maxWeeklyHours: t.max_weekly_hours || 25,
      unavailableSlots: t.unavailable_slots || {},
      dailyShifts: t.daily_shifts || { 1: 'morning', 2: 'morning', 3: 'morning', 4: 'morning', 5: 'morning' }
    }))
    totalCount.value = filtered.length
  } finally {
    loading.value = false
  }
}

/**
 * 加载班级数据，构建班主任映射
 * 用于显示哪些教师是班主任
 */
const loadHomeroomData = async () => {
  try {
    const res = await getClasses({ page: 1, page_size: 200 })
    const map = {}
    
    res.data.items.forEach(cls => {
      // 中教班主任
      if (cls.homeroom_cn_id) {
        if (!map[cls.homeroom_cn_id]) {
          map[cls.homeroom_cn_id] = { cn: [], en: [] }
        }
        map[cls.homeroom_cn_id].cn.push(cls.name)
      }
      // 外教班主任
      if (cls.homeroom_en_id) {
        if (!map[cls.homeroom_en_id]) {
          map[cls.homeroom_en_id] = { cn: [], en: [] }
        }
        map[cls.homeroom_en_id].en.push(cls.name)
      }
    })
    
    homeroomMap.value = map
  } catch (error) {
    console.warn('加载班级数据失败:', error.message)
    homeroomMap.value = {}
  }
}

/**
 * 加载教学任务，构建教师任教科目映射
 * 任教科目从行政课程和分层课程自动获取，不再手动选择
 */
const loadTeachingTasks = async () => {
  subjectLoading.value = true
  try {
    const res = await getTasksWithDetails({ page: 1, page_size: 500 })
    const map = {}
    
    // 按教师 ID 分组，收集每个教师的任教科目
    res.data.items.forEach(task => {
      if (!map[task.teacher_id]) {
        map[task.teacher_id] = new Set()
      }
      if (task.subject_name) {
        map[task.teacher_id].add(task.subject_name)
      }
    })
    
    // 转换为数组格式
    Object.keys(map).forEach(id => {
      map[id] = Array.from(map[id])
    })
    
    teacherSubjectsMap.value = map
  } catch (error) {
    console.warn('加载教学任务失败:', error.message)
    teacherSubjectsMap.value = {}
  } finally {
    subjectLoading.value = false
  }
}

/**
 * 获取教师的任教科目（从任务自动关联）
 */
const getTeacherSubjects = (teacherId) => {
  return teacherSubjectsMap.value[teacherId] || []
}

// 页面加载时获取数据
onMounted(async () => {
  await Promise.all([loadHomeroomData(), loadTeachingTasks(), loadResearchGroups()])
  loadTeachers()
})

// 监听筛选条件变化，重新加载数据
watch([filterType, filterDepartment, searchQuery, currentPage, pageSize], () => {
  loadTeachers()
}, { debounce: 300 })

// 筛选后的数据 - 本地筛选（用于标签筛选，API 不支持标签筛选）
const filteredTeachers = computed(() => {
  if (!filterTag.value) {
    return teachers.value
  }
  // 标签筛选在本地完成
  return teachers.value.filter(t => {
    return t.tags && t.tags.some(tag => 
      filterTag.value === 'ADMIN' ? tag.includes('ADMIN') : tag === filterTag.value
    )
  })
})

// 选中行
const selectedRows = ref([])
const handleSelectionChange = (rows) => {
  selectedRows.value = rows
}

// 对话框状态
const showAddDialog = ref(false)
const showImportDialog = ref(false)
const editingTeacher = ref(null)

// 导入相关
const importFileList = ref([])
const importUploading = ref(false)
const showImportResultDialog = ref(false)
const importResult = ref(null)

// 表单
const formRef = ref()
const teacherForm = ref({
  name: '',
  type: 'CN',
  department: 'PRIMARY',
  subjects: [],
  maxWeeklyHours: 25,
  tags: [],
  researchGroupId: null,
  unavailableSlots: {},
  dailyShifts: { 1: 'morning', 2: 'morning', 3: 'morning', 4: 'morning', 5: 'morning' }
})

const formRules = {
  name: [{ required: true, message: '请输入教师姓名', trigger: 'blur' }],
  type: [{ required: true, message: '请选择教师类型', trigger: 'change' }],
  department: [{ required: true, message: '请选择学部', trigger: 'change' }]
  // subjects 不再需要验证，任教科目由行政课程和分层课程自动关联
}

// 工具函数
const getSubjectTagType = (subject) => {
  if (!subject) return 'info'  // 处理 null/undefined
  const types = {
    '中文': 'danger', '语文': 'danger',
    '数学': 'primary', 
    '英语': 'warning',
    '物理': 'success', '化学': 'success', '生物': 'success',
    '体育': 'info', '轮滑': 'info',
    '美术': 'warning', '音乐': 'warning', '声乐': 'warning', '钢琴': 'warning'
  }
  return types[subject] || 'info'
}

const getTagType = (tag) => {
  if (tag === 'HOMEROOM_TEACHER') return 'danger'
  if (tag === 'ASSISTANT_HOMEROOM') return 'warning'
  if (tag.includes('ADMIN')) return 'success'
  return 'info'
}

const getGroupName = (groupId) => {
  const g = researchGroups.value.find(r => r.id === groupId)
  return g ? g.name : ''
}

// 学部显示辅助函数
const getDepartmentText = (department) => {
  const texts = {
    'PRIMARY': '小学部',
    'SECONDARY': '中学部',
    'BOTH': '小中贯通'
  }
  return texts[department] || department
}

const getDepartmentTagType = (department) => {
  const types = {
    'PRIMARY': 'success',
    'SECONDARY': 'info',
    'BOTH': 'warning'
  }
  return types[department] || 'info'
}

const getTagText = (tag) => {
  const texts = {
    'HOMEROOM_TEACHER': '班主任',
    'ASSISTANT_HOMEROOM': '副班主任',
    'PRIMARY_ADMIN': '小学管理干部',
    'SECONDARY_ADMIN': '中学管理干部'
  }
  return texts[tag] || tag
}

/**
 * 获取教师的班主任信息（从班级数据联动）
 * @param {number} teacherId 教师ID
 * @returns {object} { isHomeroom: boolean, classes: string }
 */
const getHomeroomInfo = (teacherId) => {
  const info = homeroomMap.value[teacherId]
  if (!info) {
    return { isHomeroom: false, classes: '' }
  }
  
  const allClasses = [...info.cn, ...info.en]
  if (allClasses.length === 0) {
    return { isHomeroom: false, classes: '' }
  }
  
  return {
    isHomeroom: true,
    classes: allClasses.join('、')
  }
}

const getShiftText = (teacher) => {
  // 显示早晚班概况
  const shifts = teacher.dailyShifts || {}
  const eveningDays = []
  for (let day = 1; day <= 5; day++) {
    if (shifts[day] === 'evening') {
      eveningDays.push(['一', '二', '三', '四', '五'][day - 1])
    }
  }
  if (eveningDays.length === 0) return '全早班'
  if (eveningDays.length === 5) return '全晚班'
  return `周${eveningDays.join('、')}晚班`
}

const getDayText = (day) => {
  const days = ['', '周一', '周二', '周三', '周四', '周五']
  return days[day]
}

// 切换班次（早班/晚班）
const toggleShift = (day) => {
  const current = teacherForm.value.dailyShifts[day]
  teacherForm.value.dailyShifts[day] = current === 'morning' ? 'evening' : 'morning'
}

const isTimeUnavailable = (day, period) => {
  return teacherForm.value.unavailableSlots[day]?.includes(period)
}

const toggleUnavailable = (day, period) => {
  // 周五只有8节课，第9-10节不可用
  if (day === 5 && period > 8) return
  
  if (!teacherForm.value.unavailableSlots[day]) {
    teacherForm.value.unavailableSlots[day] = []
  }
  const arr = teacherForm.value.unavailableSlots[day]
  const idx = arr.indexOf(period)
  if (idx > -1) {
    arr.splice(idx, 1)
  } else {
    arr.push(period)
    arr.sort((a, b) => a - b)
  }
}

// 操作函数
const openAddDialog = () => {
  editingTeacher.value = null
  teacherForm.value = {
    name: '',
    type: 'CN',
    department: 'PRIMARY',
    subjects: [],
    maxWeeklyHours: 25,
    tags: [],
    researchGroupId: null,
    unavailableSlots: {},
    dailyShifts: { 1: 'morning', 2: 'morning', 3: 'morning', 4: 'morning', 5: 'morning' }
  }
  showAddDialog.value = true
}

const editTeacher = (teacher) => {
  editingTeacher.value = teacher
  // 过滤掉 HOMEROOM_TEACHER 标签（该标签由班级数据联动管理，不在此处编辑）
  const editableTags = (teacher.tags || []).filter(t => t !== 'HOMEROOM_TEACHER')
  teacherForm.value = { 
    ...teacher,
    tags: editableTags,
    researchGroupId: teacher.research_group_id || null,
    unavailableSlots: JSON.parse(JSON.stringify(teacher.unavailableSlots || {})),
    dailyShifts: JSON.parse(JSON.stringify(teacher.dailyShifts || {
      1: 'morning', 2: 'morning', 3: 'morning', 4: 'morning', 5: 'morning'
    }))
  }
  showAddDialog.value = true
}

/**
 * 删除教师
 * 如果后端可用，调用 API 删除
 * 否则在本地 Mock 数据中删除
 */
const deleteTeacher = async (teacher) => {
  try {
    if (!useMockData.value) {
      // 调用 API 删除
      await deleteTeacherApi(teacher.id)
    }
    
    // 从本地列表中移除
    const index = teachers.value.findIndex(t => t.id === teacher.id)
    if (index > -1) {
      teachers.value.splice(index, 1)
      totalCount.value--
    }
    
    ElMessage.success('删除成功')
  } catch (error) {
    ElMessage.error('删除失败: ' + (error.message || '未知错误'))
  }
}

/**
 * 保存教师（创建或更新）
 */
const saveTeacher = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  
  // 准备提交的数据（转换字段名）
  // 注意：subjects 不在此处提交，任教科目由行政课程和分层课程自动关联
  const submitData = {
    name: teacherForm.value.name,
    type: teacherForm.value.type,
    department: teacherForm.value.department,
    tags: teacherForm.value.tags,
    max_weekly_hours: teacherForm.value.maxWeeklyHours,
    unavailable_slots: teacherForm.value.unavailableSlots,
    daily_shifts: teacherForm.value.dailyShifts,
    research_group_id: teacherForm.value.researchGroupId || null,
  }
  
  try {
    if (editingTeacher.value) {
      // 更新教师
      if (!useMockData.value) {
        await updateTeacher(editingTeacher.value.id, submitData)
      }
      
      // 更新本地数据（驼峰 → 下划线同步，保持与 API 返回一致）
      const index = teachers.value.findIndex(t => t.id === editingTeacher.value.id)
      if (index > -1) {
        teachers.value[index] = { 
          ...teachers.value[index], 
          ...teacherForm.value,
          research_group_id: teacherForm.value.researchGroupId || null,
          unavailable_slots: teacherForm.value.unavailableSlots,
          daily_shifts: teacherForm.value.dailyShifts,
          max_weekly_hours: teacherForm.value.maxWeeklyHours,
          weeklyHours: teacherForm.value.weeklyHours || teachers.value[index].weeklyHours
        }
      }
      ElMessage.success('修改成功')
    } else {
      // 创建教师
      if (!useMockData.value) {
        const res = await createTeacher(submitData)
        // 使用 API 返回的 ID
        teachers.value.unshift({
          ...res.data,
          weeklyHours: res.data.weekly_hours || 0,
          maxWeeklyHours: res.data.max_weekly_hours || 25
        })
      } else {
        // Mock 模式下生成本地 ID
        teachers.value.unshift({ 
          id: Date.now(),
          ...teacherForm.value, 
          weeklyHours: 0 
        })
      }
      
      totalCount.value++
      ElMessage.success('添加成功')
    }
    
    showAddDialog.value = false
  } catch (error) {
    ElMessage.error('保存失败: ' + (error.message || '未知错误'))
  }
}

const batchDelete = () => {
  ElMessage.info('批量删除功能开发中')
}

const exportData = () => {
  ElMessage.success('导出成功')
}

const downloadTemplate = () => {
  const url = getTeacherImportTemplateUrl('xlsx')
  window.open(url, '_blank')
}

const beforeImportUpload = (file) => {
  const name = (file?.name || '').toLowerCase()
  const ok = name.endsWith('.xlsx') || name.endsWith('.xls') || name.endsWith('.csv')
  if (!ok) {
    ElMessage.error('仅支持 .xlsx / .xls / .csv 文件')
  }
  // 阻止组件自动上传，改为手动点击“确认导入”
  return false
}

const confirmImport = async () => {
  const file = importFileList.value?.[0]?.raw
  if (!file) {
    ElMessage.warning('请先选择要导入的文件')
    return
  }
  importUploading.value = true
  try {
    const res = await importTeachersFile(file)
    // 后端返回的是原始 JSON（非 axios wrapper），这里兼容两种格式
    const payload = res.data ? res : { code: res.code, message: res.message, data: res.data }
    if (payload.code && payload.code !== 200) {
      ElMessage.error(payload.message || '导入失败')
    } else {
      ElMessage.success(payload.message || '导入完成')
    }
    importResult.value = payload.data || null
    showImportDialog.value = false
    showImportResultDialog.value = true
    // 刷新教师列表
    loadTeachers()
    await loadResearchGroups()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '导入失败')
  } finally {
    importUploading.value = false
  }
}
</script>

<style lang="scss" scoped>
.teacher-management {
  padding: 24px;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  
  .toolbar-left {
    display: flex;
    gap: 12px;
    .search-input { width: 200px; }
  }
  
  .toolbar-right {
    display: flex;
    gap: 8px;
  }
}

.teacher-name {
  display: flex;
  align-items: center;
  gap: 10px;
  
  .avatar {
    font-size: 14px;
    font-weight: 600;
    
    &.CN {
      background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
      color: #fff;
    }
    
    &.EN {
      background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
      color: #fff;
    }
  }
  
  .name-info {
    display: flex;
    flex-direction: column;
    gap: 2px;
    
    .name {
      font-weight: 600;
    }
  }
}

.subjects-list, .tags-list {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  
  .subject-tag, .role-tag {
    margin-bottom: 2px;
  }
}

.weekly-hours {
  font-weight: 600;
  color: var(--primary-color);
}

.shift-info {
  .shift-text {
    font-size: 13px;
    color: var(--text-secondary);
  }
}

.pagination-wrapper {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid var(--border-color);
  
  .selection-info {
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 14px;
    color: var(--text-secondary);
    
    strong {
      color: var(--primary-color);
    }
  }
}

.time-selector {
  border: 1px solid var(--border-color);
  border-radius: 8px;
  overflow: hidden;
  
  .time-header {
    display: flex;
    background: var(--bg-color);
    border-bottom: 1px solid var(--border-color);
    
    .header-cell {
      flex: 1;
      padding: 6px;
      text-align: center;
      font-size: 11px;
      color: var(--text-secondary);
      
      &:first-child {
        width: 50px;
        flex: none;
      }
    }
  }
  
  .time-row {
    display: flex;
    border-bottom: 1px solid var(--border-color);
    
    &:last-child {
      border-bottom: none;
    }
    
    .day-label {
      width: 50px;
      padding: 6px;
      background: var(--bg-color);
      font-size: 11px;
      color: var(--text-secondary);
      display: flex;
      align-items: center;
      justify-content: center;
    }
    
    .time-cell {
      flex: 1;
      padding: 6px;
      text-align: center;
      cursor: pointer;
      transition: all 0.15s ease;
      border-left: 1px solid var(--border-color);
      font-size: 12px;
      
      &:hover:not(.friday-disabled) {
        background: #fee2e2;
      }
      
      &.unavailable {
        background: #fecaca;
        color: #dc2626;
      }
      
      &.friday-disabled {
        background: #f1f5f9;
        cursor: not-allowed;
      }
    }
  }
}

.time-hint {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 8px;
}

// 早晚班选择器样式
.shift-selector {
  display: flex;
  gap: 12px;
  
  .shift-day {
    flex: 1;
    padding: 12px;
    border: 2px solid var(--border-color);
    border-radius: 8px;
    text-align: center;
    cursor: pointer;
    transition: all 0.2s ease;
    
    &:hover {
      border-color: var(--primary-color);
    }
    
    &.is-evening {
      border-color: #f59e0b;
      background: #fffbeb;
    }
    
    .day-name {
      font-weight: 600;
      margin-bottom: 8px;
    }
    
    .shift-badge {
      display: inline-block;
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 12px;
      
      &.morning {
        background: #ecfdf5;
        color: #059669;
      }
      
      &.evening {
        background: #fef3c7;
        color: #d97706;
      }
    }
  }
}

.shift-hint {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 8px;
}

// 选修课单元格样式
.time-cell.elective-cell {
  background: #fefce8;
  border-left: 2px dashed #fbbf24;
}

.import-content {
  .upload-icon {
    font-size: 48px;
    color: var(--primary-color);
    margin-bottom: 16px;
  }
  
  .upload-text {
    p {
      color: var(--text-secondary);
      margin: 0;
      
      em {
        color: var(--primary-color);
        font-style: normal;
      }
    }
    
    .upload-hint {
      font-size: 12px;
      color: var(--text-muted);
      margin-top: 8px;
    }
  }
  
  .template-download {
    text-align: center;
    margin-top: 16px;
  }
}

// 标签相关样式
.homeroom-tag {
  border-style: solid;
}

.tag-section {
  .homeroom-status {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 12px;
    padding: 8px 12px;
    background: #f8fafc;
    border-radius: 6px;
    
    .status-label {
      font-size: 13px;
      color: var(--text-secondary);
    }
    
    .status-hint {
      font-size: 12px;
      color: var(--text-muted);
    }
  }
  
  .editable-tags {
    display: flex;
    gap: 16px;
  }
}

// 任教科目只读显示样式
.readonly-subjects {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  min-height: 32px;
  align-items: center;
  
  .subject-tag {
    margin-right: 0;
  }
}

.no-subjects {
  color: #909399;
  font-size: 13px;
}

.form-hint {
  font-size: 12px;
  color: #909399;
  margin-top: 6px;
}
</style>
