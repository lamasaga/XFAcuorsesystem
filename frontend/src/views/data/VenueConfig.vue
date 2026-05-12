<template>
  <div class="venue-config">
    <div class="toolbar">
      <div class="toolbar-left">
        <h3>场地资源配置</h3>
        <span class="hint">配置场地容量限制，用于排课时的资源约束</span>
      </div>
      <div class="toolbar-right">
        <el-button @click="showImportDialog = true">
          <el-icon><Upload /></el-icon>导入
        </el-button>
        <el-button type="primary" @click="showAddDialog = true">
          <el-icon><Plus /></el-icon>添加场地
        </el-button>
      </div>
    </div>

    <!-- 场地卡片列表 -->
    <div class="venue-cards" v-loading="loading">
      <div v-if="venues.length === 0 && !loading" class="empty-state">
        <el-empty description="暂无场地资源，请点击右上角添加" />
      </div>

      <div v-for="venue in venues" :key="venue.id" 
        class="venue-card" 
        :class="{ 'limited': venue.capacity === 1 }">
        <div class="venue-icon" :class="getVenueIcon(venue.name)">
          <el-icon><component :is="getVenueIconComponent(venue.name)" /></el-icon>
        </div>
        <div class="venue-info">
          <div class="venue-name">
            {{ venue.name }}
            <el-tag v-if="venue.capacity === 1" size="small" type="danger">稀缺</el-tag>
          </div>
          <div class="venue-subjects">
            <el-tag v-for="sub in venue.subjects" :key="sub" size="small">{{ sub }}</el-tag>
          </div>
          <div class="venue-capacity">
            <span class="capacity-label">同时容纳</span>
            <span class="capacity-value" :class="{ warning: venue.capacity === 1 }">{{ venue.capacity }}</span>
            <span class="capacity-unit">个班</span>
          </div>
          <div class="venue-grades" v-if="venue.applicable_grades">
            <span class="grades-label">适用年级:</span>
            <el-tag v-for="g in venue.applicable_grades" :key="g" size="small" class="grade-tag">{{ g }}</el-tag>
          </div>
          <div class="venue-grades" v-else>
            <span class="grades-label">适用年级:</span>
            <span class="all-grades">所有年级</span>
          </div>
        </div>
        <div class="venue-actions">
          <el-button type="primary" link @click="editVenue(venue)"><el-icon><Edit /></el-icon></el-button>
          <el-button type="danger" link @click="deleteVenue(venue)"><el-icon><Delete /></el-icon></el-button>
        </div>
      </div>
    </div>

    <!-- 容量说明 -->
    <div class="capacity-summary card">
      <h4>场地使用分析</h4>
      <div class="summary-grid">
        <div class="summary-item">
          <div class="item-label">体育课需求</div>
          <div class="item-value">
            <span class="demand">约 62 节/周</span>
            <span class="supply">供给 4班×43槽 = 172 容量</span>
            <el-tag type="success" size="small">充足</el-tag>
          </div>
        </div>
        <div class="summary-item">
          <div class="item-label">美术课需求</div>
          <div class="item-value">
            <span class="demand">约 40 节/周</span>
            <span class="supply">供给 2班×43槽 = 86 容量</span>
            <el-tag type="success" size="small">充足</el-tag>
          </div>
        </div>
        <div class="summary-item warning">
          <div class="item-label">声乐课需求</div>
          <div class="item-value">
            <span class="demand">约 15 节/周</span>
            <span class="supply">供给 1班×43槽 = 43 容量</span>
            <el-tag type="warning" size="small">需关注</el-tag>
          </div>
        </div>
        <div class="summary-item warning">
          <div class="item-label">钢琴课需求</div>
          <div class="item-value">
            <span class="demand">约 15 节/周</span>
            <span class="supply">供给 1班×43槽 = 43 容量</span>
            <el-tag type="warning" size="small">需关注</el-tag>
          </div>
        </div>
      </div>
    </div>

    <!-- 导入对话框 -->
    <ExcelImportDialog
      v-model="showImportDialog"
      title="导入场地数据"
      :template-url="getVenueImportTemplateUrl('xlsx')"
      :import-api="importVenuesFile"
      @success="loadVenues"
    />

    <!-- 添加/编辑场地对话框 -->
    <el-dialog v-model="showAddDialog" :title="isEditing ? '编辑场地资源' : '添加场地资源'" width="500px" @close="resetForm">
      <el-form :model="venueForm" label-width="100px">
        <el-form-item label="场地名称">
          <el-input v-model="venueForm.name" placeholder="如: 实验室" />
        </el-form-item>
        <el-form-item label="关联科目">
          <el-select 
            v-model="venueForm.subjects" 
            multiple 
            placeholder="选择科目"
            :loading="subjectLoading"
            style="width: 100%"
          >
            <el-option v-for="s in subjectOptions" :key="s" :label="s" :value="s" />
          </el-select>
        </el-form-item>
        <el-form-item label="同时容量">
          <el-input-number v-model="venueForm.capacity" :min="1" :max="10" />
          <span class="form-hint">个班</span>
        </el-form-item>
        <el-form-item label="适用年级">
          <el-checkbox-group v-model="venueForm.grades">
            <el-checkbox v-for="g in gradeOptions" :key="g" :value="g">{{ g }}</el-checkbox>
          </el-checkbox-group>
          <div class="form-hint">留空表示适用所有年级</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="saveVenue">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Edit, Delete, Upload } from '@element-plus/icons-vue'
import { getVenues, createVenue, updateVenue, deleteVenue as deleteVenueApi, getVenueImportTemplateUrl, importVenuesFile } from '@/api/venues'
import { getSubjects } from '@/api/subjects'
import ExcelImportDialog from '@/components/ExcelImportDialog.vue'

const showAddDialog = ref(false)
const showImportDialog = ref(false)
const loading = ref(false)
const venues = ref([])
const isEditing = ref(false)
const editingId = ref(null)

// 科目选项 - 从科目管理 API 获取
const subjectOptions = ref([])
const subjectLoading = ref(false)
const gradeOptions = ['PK', 'KG', 'G1', 'G2', 'G3', 'G4', 'G5', 'G6', 'G7', 'G8', 'G9', 'G10', 'G11', 'G12']

const venueForm = ref({
  name: '',
  subjects: [],
  capacity: 1,
  grades: []
})

const resetForm = () => {
  venueForm.value = {
    name: '',
    subjects: [],
    capacity: 1,
    grades: []
  }
  isEditing.value = false
  editingId.value = null
}

// 加载场地数据
const loadVenues = async () => {
  loading.value = true
  try {
    const res = await getVenues()
    venues.value = res.data.items
  } catch (error) {
    ElMessage.error('加载场地资源失败: ' + error.message)
  } finally {
    loading.value = false
  }
}

// 加载科目数据（用于关联科目下拉选择）
const loadSubjects = async () => {
  subjectLoading.value = true
  try {
    const res = await getSubjects({ page_size: 100 })
    // 只获取需要特定场地的科目（如体育、美术、音乐类等），或者获取全部
    subjectOptions.value = res.data.items.map(s => s.name)
  } catch (error) {
    console.warn('加载科目失败，使用默认列表:', error.message)
    // 降级使用默认列表
    subjectOptions.value = ['体育', '轮滑', '美术', '声乐', '钢琴', '舞蹈', '实验', '计算机']
  } finally {
    subjectLoading.value = false
  }
}

onMounted(async () => {
  await loadSubjects()
  loadVenues()
})

const getVenueIcon = (name) => {
  if (name.includes('体育')) return 'pe'
  if (name.includes('美术')) return 'art'
  if (name.includes('音乐') || name.includes('声乐')) return 'music'
  if (name.includes('钢琴')) return 'piano'
  return '' // 默认样式
}

const getVenueIconComponent = (name) => {
  if (name.includes('体育')) return Soccer
  if (name.includes('美术')) return PictureFilled
  if (name.includes('音乐') || name.includes('声乐')) return Microphone
  if (name.includes('钢琴')) return Headset
  if (name.includes('电脑') || name.includes('计算机')) return Monitor
  return School
}

const editVenue = (venue) => {
  isEditing.value = true
  editingId.value = venue.id
  venueForm.value = {
    name: venue.name,
    subjects: venue.subjects ? [...venue.subjects] : [],
    capacity: venue.capacity,
    grades: venue.applicable_grades ? [...venue.applicable_grades] : []
  }
  showAddDialog.value = true
}

const saveVenue = async () => {
  if (!venueForm.value.name) {
    ElMessage.warning('请输入场地名称')
    return
  }
  if (venueForm.value.subjects.length === 0) {
    ElMessage.warning('请选择关联科目')
    return
  }

  const data = {
    name: venueForm.value.name,
    subjects: venueForm.value.subjects,
    capacity: venueForm.value.capacity,
    applicable_grades: venueForm.value.grades.length > 0 ? venueForm.value.grades : null,
    description: ''
  }

  try {
    if (isEditing.value && editingId.value) {
      await updateVenue(editingId.value, data)
      ElMessage.success('场地更新成功')
    } else {
      await createVenue(data)
      ElMessage.success('场地创建成功')
    }
    
    showAddDialog.value = false
    loadVenues()
    resetForm()
  } catch (error) {
    ElMessage.error('保存失败: ' + error.message)
  }
}

const deleteVenue = async (venue) => {
  try {
    await ElMessageBox.confirm(`确定要删除场地 ${venue.name} 吗？`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await deleteVenueApi(venue.id)
    ElMessage.success('删除成功')
    loadVenues()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败: ' + error.message)
    }
  }
}
</script>

<style lang="scss" scoped>
.venue-config {
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
}

.venue-cards {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
  margin-bottom: 24px;
}

.venue-card {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 20px;
  background: #fff;
  border: 1px solid var(--border-color);
  border-radius: 12px;
  transition: all 0.2s ease;
  
  &:hover {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  }
  
  &.limited {
    border-color: #fecaca;
    background: linear-gradient(135deg, #fff 0%, #fef2f2 100%);
  }
  
  .venue-icon {
    width: 56px;
    height: 56px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 28px;
    flex-shrink: 0;
    
    &.pe {
      background: #dcfce7;
      color: #16a34a;
    }
    &.art {
      background: #fef3c7;
      color: #d97706;
    }
    &.music {
      background: #fce7f3;
      color: #db2777;
    }
    &.piano {
      background: #e0e7ff;
      color: #4f46e5;
    }
  }
  
  .venue-info {
    flex: 1;
    
    .venue-name {
      font-size: 16px;
      font-weight: 600;
      margin-bottom: 8px;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    
    .venue-subjects {
      display: flex;
      gap: 4px;
      margin-bottom: 12px;
    }
    
    .venue-capacity {
      display: flex;
      align-items: baseline;
      gap: 4px;
      margin-bottom: 8px;
      
      .capacity-label {
        color: var(--text-secondary);
        font-size: 13px;
      }
      
      .capacity-value {
        font-size: 24px;
        font-weight: 700;
        color: var(--primary-color);
        
        &.warning {
          color: #dc2626;
        }
      }
      
      .capacity-unit {
        color: var(--text-secondary);
        font-size: 13px;
      }
    }
    
    .venue-note {
      display: flex;
      align-items: center;
      gap: 4px;
      font-size: 12px;
      color: var(--text-muted);
      
      .el-icon {
        font-size: 14px;
      }
    }
    
    .venue-grades {
      display: flex;
      align-items: center;
      flex-wrap: wrap;
      gap: 4px;
      margin-top: 8px;
      
      .grades-label {
        font-size: 12px;
        color: var(--text-secondary);
        margin-right: 4px;
      }
      
      .grade-tag {
        margin-bottom: 2px;
      }
    }
  }
  
  .venue-actions {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
}

.capacity-summary {
  padding: 20px;
  
  h4 {
    font-size: 15px;
    font-weight: 600;
    margin-bottom: 16px;
  }
  
  .summary-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 16px;
  }
  
  .summary-item {
    padding: 12px 16px;
    background: var(--bg-color);
    border-radius: 8px;
    
    &.warning {
      background: #fef3c7;
    }
    
    .item-label {
      font-size: 13px;
      color: var(--text-secondary);
      margin-bottom: 8px;
    }
    
    .item-value {
      display: flex;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
      
      .demand {
        font-weight: 600;
        color: var(--text-primary);
      }
      
      .supply {
        font-size: 12px;
        color: var(--text-muted);
      }
    }
  }
}

.form-hint {
  margin-left: 8px;
  color: var(--text-secondary);
  font-size: 13px;
}

@media (max-width: 900px) {
  .venue-cards,
  .summary-grid {
    grid-template-columns: 1fr;
  }
}
</style>
