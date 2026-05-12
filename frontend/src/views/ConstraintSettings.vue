<template>
  <div class="constraint-settings">
    <div class="page-header">
      <div class="page-title">
        <h1>约束设置</h1>
        <span class="subtitle">配置排课规则和优化偏好</span>
      </div>
      <el-button type="primary" :loading="saving" @click="saveAll">
        <el-icon><Check /></el-icon>保存设置
      </el-button>
    </div>

    <!-- ========== 系统硬约束 (物理限制) ========== -->
    <div class="tier-section">
      <div class="tier-header tier-1">
        <el-tag type="danger" effect="dark" size="large">系统硬约束</el-tag>
        <div>
          <h2>物理约束</h2>
          <span class="tier-desc">违反即无效解，系统自动强制执行，无法禁用</span>
        </div>
      </div>
      <div class="tier-body">
        <div class="constraint-item locked" v-for="c in hardConstraints" :key="c.id">
          <div class="item-info">
            <el-tag type="danger" size="small">{{ c.id }}</el-tag>
            <span class="item-title">{{ c.title }}</span>
            <span class="item-desc">{{ c.desc }}</span>
          </div>
          <el-tag type="info" effect="plain"><el-icon><Lock /></el-icon> 系统锁定</el-tag>
        </div>
      </div>
    </div>

    <!-- ========== 业务约束 (可配置) ========== -->
    <div class="tier-section">
      <div class="tier-header tier-2">
        <el-tag type="primary" effect="dark" size="large">业务规则</el-tag>
        <div>
          <h2>排课规则配置</h2>
          <span class="tier-desc">可切换硬/软约束模式。硬约束必须满足；软约束通过权重优化。</span>
        </div>
        <el-button type="primary" link @click="resetDefaults">恢复默认</el-button>
      </div>
      <div class="tier-body">
        <div class="config-list">
          <div
            v-for="item in configurableConstraints"
            :key="item.id"
            class="config-item"
            :class="{ 'is-hard': item.type === 'hard', 'is-disabled': !item.enabled }"
          >
            <div class="item-header">
              <div class="info">
                <span class="title">{{ item.label }}</span>
                <span class="desc">{{ item.description }}</span>
              </div>
              <div class="controls-top">
                <el-switch
                  v-model="item.enabled"
                  inline-prompt
                  active-text="启用"
                  inactive-text="禁用"
                  style="--el-switch-on-color: #13ce66; --el-switch-off-color: #ff4949"
                />
              </div>
            </div>

            <div class="item-body" v-if="item.enabled">
              <!-- 模式选择 -->
              <div class="mode-select">
                <span class="label">约束模式:</span>
                <el-radio-group v-model="item.type" size="small">
                  <el-radio-button label="hard">硬约束 (强制)</el-radio-button>
                  <el-radio-button label="soft">软约束 (优化)</el-radio-button>
                </el-radio-group>
              </div>

              <!-- 权重滑块 (仅软约束显示) -->
              <div class="weight-control" v-if="item.type === 'soft'">
                <span class="label">权重 ({{ item.weight }}):</span>
                <el-slider
                  v-model="item.weight"
                  :min="1"
                  :max="10"
                  :show-tooltip="false"
                  class="weight-slider"
                />
                <span class="weight-desc">
                  {{ getWeightDesc(item.weight) }}
                </span>
              </div>
              <div class="hard-hint" v-else>
                <el-icon><CircleCheckFilled /></el-icon>
                <span>违反此规则将直接导致排课无解</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Check, Lock, CircleCheckFilled } from '@element-plus/icons-vue'
import { getScheduleConfig, saveScheduleConfig } from '@/api/schedules'

const saving = ref(false)

// -------- 系统硬约束 --------
const hardConstraints = [
  { id: 'H1', title: '课程必须排入', desc: '每个课程必须且仅排入一个时间槽' },
  { id: 'H2', title: '教师无冲突', desc: '同一教师同一时刻最多上一节课' },
  { id: 'H3', title: '班级无冲突', desc: '同一班级同一时刻最多上一节课' },
  { id: 'H_L', title: '分层同步', desc: '同一分层组的所有层级在相同时间上课' },
  { id: 'H4', title: '场地容量上限', desc: '同一时段使用同一场地不超过物理容量' },
  { id: 'H_C', title: '连堂课要求', desc: '标记连堂的课程每周恰好 1 次连堂（2 节连续）' },
  { id: 'H_U', title: '教师不可用时间', desc: '教师标记的不可用时间段不排课' },
]

// -------- 可配置约束默认值 --------
const CONFIG_DEFAULTS = [
  { id: 'daily_subject_limit', label: '每日同科目上限', description: '同一班级每天同一科目最多 2 节课', type: 'hard', enabled: true, weight: 10 },
  { id: 'main_morning', label: '主科优先上午', description: '语数英尽量安排在上午（第1-5节）', type: 'soft', enabled: true, weight: 8 },
  { id: 'balanced_distribution', label: '科目均匀分布', description: '同一科目在一周内均匀分布', type: 'soft', enabled: true, weight: 6 },
  { id: 'artpe_not_first', label: '艺体课避开首节', description: '体育、美术、音乐等不排第 1 节', type: 'soft', enabled: true, weight: 5 },
  { id: 'venue_dispersion', label: '场地分散使用', description: '同类场地使用在时间上尽量分散', type: 'soft', enabled: true, weight: 4 },
  { id: 'teacher_shift', label: '早晚班教师约束', description: '晚班教师上午尽量不排课', type: 'soft', enabled: true, weight: 3 },
  { id: 'meeting_reservation', label: '会议/教研预留', description: '预留教研和会议时间段', type: 'soft', enabled: true, weight: 2 },
  { id: 'department_meeting', label: '教研组组会时间', description: '同一教研组的教师每周须有 2 节连续空闲用于组会', type: 'hard', enabled: true, weight: 7 },
  { id: 'admin_afternoon', label: '管理干部会议时间', description: '小学管理干部周一下午不排课，中学管理干部周二下午不排课', type: 'hard', enabled: true, weight: 8 },
]

const configurableConstraints = ref(JSON.parse(JSON.stringify(CONFIG_DEFAULTS)))

const getWeightDesc = (w) => {
  if (w >= 9) return '极高优先级'
  if (w >= 7) return '高优先级'
  if (w >= 5) return '中等优先级'
  return '低优先级'
}

// -------- 加载配置 --------
const loadConfig = async () => {
  try {
    const res = await getScheduleConfig()
    const cfg = res.data?.config
    if (cfg) {
      // 优先读取 constraints，兼容 soft_constraints
      const savedList = cfg.constraints || cfg.soft_constraints || []
      
      if (savedList.length > 0) {
        const serverMap = {}
        savedList.forEach(c => { serverMap[c.id] = c })
        
        configurableConstraints.value = CONFIG_DEFAULTS.map(d => {
          const srv = serverMap[d.id]
          if (srv) {
            // 合并属性，确保 type 存在
            return { 
              ...d, 
              enabled: srv.enabled !== false,
              type: srv.type || (srv.enabled ? d.type : 'soft'), // 如果旧配置没 type，沿用默认
              weight: srv.weight || d.weight 
            }
          }
          return { ...d }
        })
      }
    }
  } catch (e) {
    console.warn('加载配置失败', e)
  }
}

// -------- 保存 --------
const saveAll = async () => {
  saving.value = true
  try {
    const configData = {
      constraints: configurableConstraints.value.map(c => ({
        id: c.id,
        enabled: c.enabled,
        type: c.type,
        weight: c.weight
      })),
      meeting_slots: [], // TODO: 如果有会议预留界面，需在此合并
    }
    // 同时保留 soft_constraints 以兼容旧代码（虽然此时旧代码应该已更新）
    configData.soft_constraints = configData.constraints

    await saveScheduleConfig({ name: '自定义配置', config: configData })
    ElMessage.success('约束设置已保存')
  } catch (e) {
    ElMessage.error('保存失败: ' + (e.message || e))
  } finally {
    saving.value = false
  }
}

const resetDefaults = () => {
  configurableConstraints.value = JSON.parse(JSON.stringify(CONFIG_DEFAULTS))
  ElMessage.success('已恢复默认设置')
}

onMounted(loadConfig)
</script>

<style lang="scss" scoped>
.constraint-settings {
  max-width: 1000px;
  margin: 0 auto;
  padding-bottom: 40px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 28px;
  h1 { font-size: 24px; font-weight: 600; }
  .subtitle { font-size: 14px; color: var(--text-secondary); margin-left: 12px; }
}

.tier-section {
  margin-bottom: 28px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  overflow: hidden;
  border: 1px solid var(--border-color);
}

.tier-header {
  display: flex; align-items: center; gap: 16px;
  padding: 16px 24px;
  border-bottom: 1px solid var(--border-color);
  background: #f8fafc;
  
  h2 { font-size: 16px; font-weight: 600; margin: 0; color: var(--text-primary); }
  .tier-desc { font-size: 13px; color: var(--text-secondary); }
  
  &.tier-1 { border-left: 4px solid #ef4444; }
  &.tier-2 { border-left: 4px solid #3b82f6; }
}

.tier-body { padding: 20px; }

/* 系统硬约束项 */
.constraint-item {
  display: flex; justify-content: space-between; align-items: center;
  padding: 12px 16px; margin-bottom: 8px;
  background: #f8fafc; border-radius: 8px; border: 1px solid #e2e8f0;
  
  .item-info {
    display: flex; align-items: center; gap: 12px;
    .item-title { font-weight: 600; font-size: 14px; color: var(--text-primary); }
    .item-desc { font-size: 13px; color: var(--text-secondary); }
  }
}

/* 业务约束卡片 */
.config-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(450px, 1fr));
  gap: 16px;
}

.config-item {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 16px;
  transition: all 0.2s ease;
  
  &:hover {
    border-color: #cbd5e1;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
  }
  
  &.is-hard { border-left: 3px solid #ef4444; }
  &.is-disabled { opacity: 0.6; filter: grayscale(0.8); }

  .item-header {
    display: flex; justify-content: space-between; align-items: flex-start;
    margin-bottom: 16px;
    .info {
      .title { display: block; font-weight: 600; font-size: 15px; color: var(--text-primary); margin-bottom: 4px; }
      .desc { font-size: 13px; color: var(--text-secondary); line-height: 1.4; }
    }
  }
  
  .item-body {
    background: #f8fafc;
    border-radius: 8px;
    padding: 12px;
    
    .mode-select {
      display: flex; align-items: center; justify-content: space-between;
      margin-bottom: 12px;
      .label { font-size: 13px; font-weight: 500; color: var(--text-secondary); }
    }
    
    .weight-control {
      display: flex; align-items: center; gap: 12px;
      .label { font-size: 13px; color: var(--text-secondary); min-width: 60px; }
      .weight-slider { flex: 1; margin: 0 8px; }
      .weight-desc { font-size: 12px; color: #3b82f6; min-width: 70px; text-align: right; }
    }
    
    .hard-hint {
      display: flex; align-items: center; gap: 6px;
      color: #ef4444; font-size: 13px; font-weight: 500;
      padding: 8px 0;
    }
  }
}
</style>