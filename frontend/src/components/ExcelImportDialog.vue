<template>
  <div>
    <!-- 导入对话框 -->
    <el-dialog
      v-model="visible"
      :title="title"
      width="600px"
      destroy-on-close
      @close="handleClose"
    >
      <div class="import-content">
        <el-upload
          ref="uploadRef"
          drag
          action="#"
          :auto-upload="false"
          accept=".xlsx,.xls,.csv"
          :limit="1"
          v-model:file-list="fileList"
          :before-upload="beforeUpload"
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
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" :loading="uploading" @click="confirmImport">
          确认导入
        </el-button>
      </template>
    </el-dialog>

    <!-- 导入结果对话框 -->
    <el-dialog
      v-model="resultVisible"
      title="导入结果"
      width="720px"
      destroy-on-close
    >
      <div v-if="result" class="result-summary">
        <el-row :gutter="16">
          <el-col :span="6">
            <div class="result-stat success">
              <div class="stat-value">{{ result.created || 0 }}</div>
              <div class="stat-label">新增</div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="result-stat warning">
              <div class="stat-value">{{ result.updated || 0 }}</div>
              <div class="stat-label">更新</div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="result-stat info">
              <div class="stat-value">{{ result.skipped || 0 }}</div>
              <div class="stat-label">跳过</div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="result-stat" :class="result.failed > 0 ? 'danger' : 'success'">
              <div class="stat-value">{{ result.failed || 0 }}</div>
              <div class="stat-label">失败</div>
            </div>
          </el-col>
        </el-row>
      </div>

      <el-divider v-if="errorList.length > 0" content-position="left">
        错误详情（共 {{ errorList.length }} 条）
      </el-divider>

      <el-table
        v-if="errorList.length > 0"
        :data="errorList"
        stripe
        height="300"
        size="small"
      >
        <el-table-column prop="rowNumber" label="行号" width="70" align="center" />
        <el-table-column prop="identifier" label="标识" width="140" />
        <el-table-column prop="message" label="错误原因" />
      </el-table>

      <div v-else-if="result" class="no-errors">
        <el-icon color="#16a34a" :size="20"><CircleCheck /></el-icon>
        <span>导入成功，未发现错误</span>
      </div>

      <template #footer>
        <el-button type="primary" @click="closeResult">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
/**
 * 通用 Excel/CSV 导入对话框组件
 *
 * 使用方法：
 *   <ExcelImportDialog
 *     v-model="showImportDialog"
 *     title="导入学生数据"
 *     template-url="http://localhost:8001/api/v1/students/import/template?format=xlsx"
 *     :import-api="importStudentsFile"
 *     @success="loadStudents"
 *   />
 */
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Upload, Download, CircleCheck } from '@element-plus/icons-vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  title: { type: String, default: '导入数据' },
  templateUrl: { type: String, required: true },
  importApi: { type: Function, required: true },
})

const emit = defineEmits(['update:modelValue', 'success'])

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
})

const uploadRef = ref(null)
const fileList = ref([])
const uploading = ref(false)
const resultVisible = ref(false)
const result = ref(null)
const errorList = ref([])

const beforeUpload = (file) => {
  const name = (file?.name || '').toLowerCase()
  const ok = name.endsWith('.xlsx') || name.endsWith('.xls') || name.endsWith('.csv')
  if (!ok) {
    ElMessage.error('仅支持 .xlsx / .xls / .csv 文件')
  }
  return false
}

const downloadTemplate = () => {
  if (!props.templateUrl) {
    ElMessage.warning('模板下载地址未配置')
    return
  }
  window.open(props.templateUrl, '_blank')
}

const confirmImport = async () => {
  const file = fileList.value?.[0]?.raw
  if (!file) {
    ElMessage.warning('请先选择要导入的文件')
    return
  }

  uploading.value = true
  try {
    const payload = await props.importApi(file)
    // 兼容两种返回格式：axios response 或已解包的 data
    const data = payload.data || payload
    const code = payload.code || 200

    if (code !== 200 && code !== 0) {
      ElMessage.error(payload.message || '导入失败')
    } else {
      const hasErrors = data?.failed > 0
      if (hasErrors) {
        ElMessage.warning('导入完成，部分数据失败')
      } else {
        ElMessage.success(payload.message || '导入完成')
      }
    }

    result.value = data || {}
    errorList.value = (data?.errors || []).map(e => ({
      rowNumber: e.rowNumber || e.row_number || '-',
      identifier: e.identifier || e.name || '-',
      message: e.message || '未知错误',
    }))

    visible.value = false
    resultVisible.value = true

    // 如果没有失败，触发 success 事件让父组件刷新列表
    if ((data?.failed || 0) === 0) {
      emit('success')
    }
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '导入失败')
  } finally {
    uploading.value = false
  }
}

const closeResult = () => {
  resultVisible.value = false
  // 无论成功与否，都触发 success 让父组件刷新（用户已看到结果）
  emit('success')
}

const handleClose = () => {
  fileList.value = []
  result.value = null
  errorList.value = []
}

// 监听 visible 变化，关闭时清理
watch(visible, (val) => {
  if (!val) {
    fileList.value = []
  }
})
</script>

<style scoped lang="scss">
.import-content .upload-icon {
  font-size: 48px;
  color: var(--el-color-primary);
  margin-bottom: 12px;
}

.import-content .upload-text p {
  margin: 0;
  color: var(--el-text-color-regular);
}
.import-content .upload-text p em {
  color: var(--el-color-primary);
  font-style: normal;
  font-weight: 600;
}
.import-content .upload-text .upload-hint {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 8px;
}

.import-content .template-download {
  text-align: center;
  margin-top: 16px;
}

.result-summary {
  margin-bottom: 8px;
}
.result-summary .result-stat {
  text-align: center;
  padding: 12px 8px;
  border-radius: 8px;
  background: var(--el-fill-color-light);
}
.result-summary .result-stat .stat-value {
  font-size: 24px;
  font-weight: 700;
  color: var(--el-text-color-primary);
}
.result-summary .result-stat .stat-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 4px;
}
.result-summary .result-stat.success {
  background: rgba(22, 163, 74, 0.08);
}
.result-summary .result-stat.success .stat-value {
  color: #16a34a;
}
.result-summary .result-stat.warning {
  background: rgba(245, 158, 11, 0.08);
}
.result-summary .result-stat.warning .stat-value {
  color: #f59e0b;
}
.result-summary .result-stat.info {
  background: rgba(59, 130, 246, 0.08);
}
.result-summary .result-stat.info .stat-value {
  color: #3b82f6;
}
.result-summary .result-stat.danger {
  background: rgba(239, 68, 68, 0.08);
}
.result-summary .result-stat.danger .stat-value {
  color: #ef4444;
}

.no-errors {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 24px;
  color: #16a34a;
  font-size: 14px;
}
</style>
