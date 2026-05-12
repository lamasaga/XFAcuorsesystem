<template>
  <div class="dashboard">
    <!-- 欢迎区域 -->
    <div class="welcome-section">
      <div class="welcome-content">
        <h1 class="welcome-title">
          <span class="greeting">{{ greeting }}，</span>
          <span class="username">欢迎回来</span>
        </h1>
        <p class="welcome-desc">智能排课系统 · {{ currentDate }}</p>
      </div>
      <div class="quick-actions">
        <el-button type="primary" size="large" @click="$router.push('/schedule')">
          <el-icon><Cpu /></el-icon>
          开始排课
        </el-button>
        <el-button size="large" @click="$router.push('/data')">
          <el-icon><DataAnalysis /></el-icon>
          数据管理
        </el-button>
      </div>
    </div>
    
    <!-- 统计卡片 -->
    <div class="stats-grid">
      <div class="stat-card" v-for="stat in statsCards" :key="stat.label">
        <div class="stat-icon" :class="stat.color">
          <el-icon><component :is="stat.icon" /></el-icon>
        </div>
        <div class="stat-value">{{ stat.value }}</div>
        <div class="stat-label">{{ stat.label }}</div>
      </div>
    </div>
    
    <!-- 主内容区 -->
    <div class="main-content">
      <!-- 排课状态卡片 -->
      <div class="card schedule-status">
        <div class="card-header">
          <h3>排课状态</h3>
          <el-tag :type="scheduleStatus.type">{{ scheduleStatus.text }}</el-tag>
        </div>
        <div class="status-info">
          <div class="status-item">
            <span class="label">教学任务</span>
            <span class="value">{{ scheduleDetail.taskCount }} 条</span>
          </div>
          <div class="status-item">
            <span class="label">课时完成率</span>
            <el-progress 
              :percentage="scheduleDetail.completionRate" 
              :stroke-width="10"
              :status="scheduleDetail.completionRate >= 95 ? 'success' : ''"
              :color="scheduleDetail.completionRate >= 95 ? '#67c23a' : '#3b82f6'"
            />
          </div>
          <div class="status-item">
            <span class="label">分层组</span>
            <span class="value">{{ scheduleDetail.layerGroupCount }} 组</span>
          </div>
          <div class="status-item">
            <span class="label">特殊场地</span>
            <span class="value">{{ scheduleDetail.venueCount }} 个</span>
          </div>
        </div>
        <el-button 
          type="primary" 
          plain 
          class="view-detail-btn" 
          :disabled="!scheduleDetail.hasActiveSchedule"
          @click="$router.push('/timetable')"
        >
          {{ scheduleDetail.hasActiveSchedule ? '查看完整课表' : '暂无已激活的课表' }}
          <el-icon><ArrowRight /></el-icon>
        </el-button>
      </div>
      
      <!-- 快速操作 -->
      <div class="card quick-operations">
        <div class="card-header">
          <h3>快速操作</h3>
        </div>
        <div class="operations-grid">
          <div 
            class="operation-item" 
            v-for="op in operations" 
            :key="op.title"
            @click="$router.push(op.path)"
          >
            <div class="op-icon" :style="{ background: op.bgColor }">
              <el-icon :style="{ color: op.iconColor }">
                <component :is="op.icon" />
              </el-icon>
            </div>
            <div class="op-info">
              <div class="op-title">{{ op.title }}</div>
              <div class="op-desc">{{ op.desc }}</div>
            </div>
            <el-icon class="op-arrow"><ArrowRight /></el-icon>
          </div>
        </div>
      </div>
      
      <!-- 系统信息 -->
      <div class="card system-info">
        <div class="card-header">
          <h3>系统信息</h3>
        </div>
        <div class="info-list">
          <div class="info-item">
            <span class="info-label">约束体系</span>
            <span class="info-value">三层 (硬约束 / 严格约束 / 软约束)</span>
          </div>
          <div class="info-item">
            <span class="info-label">方案保留</span>
            <span class="info-value">最近 6 个批次</span>
          </div>
          <div class="info-item">
            <span class="info-label">适用规模</span>
            <span class="info-value">28 班 / 50-80 教师</span>
          </div>
          <div class="info-item">
            <span class="info-label">课时模式</span>
            <span class="info-value">周一至周四 9 节 · 周五 7 节</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { 
  Cpu, User, OfficeBuilding, Reading, Calendar,
  ArrowRight, Download, Setting, DataAnalysis
} from '@element-plus/icons-vue'
import { getOverviewStats } from '@/api/stats'

// 问候语
const greeting = computed(() => {
  const hour = new Date().getHours()
  if (hour < 12) return '上午好'
  if (hour < 18) return '下午好'
  return '晚上好'
})

// 当前日期
const currentDate = computed(() => {
  const now = new Date()
  const weekDays = ['日', '一', '二', '三', '四', '五', '六']
  return `${now.getFullYear()}年${now.getMonth() + 1}月${now.getDate()}日 星期${weekDays[now.getDay()]}`
})

// 统计卡片数据
const statsCards = ref([
  { icon: 'User', value: 0, label: '教师总数', color: 'blue' },
  { icon: 'OfficeBuilding', value: 0, label: '班级总数', color: 'green' },
  { icon: 'Reading', value: 0, label: '科目总数', color: 'orange' },
  { icon: 'Calendar', value: 0, label: '已排课时', color: 'purple' }
])

// 排课状态
const scheduleStatus = ref({
  type: 'info',
  text: '未排课'
})

// 排课详情（来自 API 真实数据）
const scheduleDetail = ref({
  taskCount: 0,
  completionRate: 0,
  hasActiveSchedule: false,
  layerGroupCount: 0,
  venueCount: 0
})

/**
 * 加载统计数据
 */
const loadStats = async () => {
  try {
    const res = await getOverviewStats()
    const data = res.data
    
    // 更新统计卡片
    statsCards.value = [
      { icon: 'User', value: data.teacher_count, label: '教师总数', color: 'blue' },
      { icon: 'OfficeBuilding', value: data.class_count, label: '班级总数', color: 'green' },
      { icon: 'Reading', value: data.subject_count, label: '科目总数', color: 'orange' },
      { icon: 'Calendar', value: data.scheduled_periods, label: '已排课时', color: 'purple' }
    ]
    
    // 更新排课状态
    if (data.schedule_status.has_active) {
      scheduleStatus.value = {
        type: 'success',
        text: `排课完成 (${data.schedule_status.completion_rate}%)`
      }
    } else if (data.schedule_status.has_schedule) {
      scheduleStatus.value = {
        type: 'warning',
        text: '有课表但未激活'
      }
    } else {
      scheduleStatus.value = {
        type: 'info',
        text: '未排课'
      }
    }
    
    // 更新排课详情
    scheduleDetail.value = {
      taskCount: data.task_count,
      completionRate: data.schedule_status.completion_rate,
      hasActiveSchedule: data.schedule_status.has_active,
      layerGroupCount: data.layer_group_count || 0,
      venueCount: data.venue_count || 0
    }
    
  } catch (error) {
    console.error('加载统计数据失败:', error)
    // 保持默认值
  }
}

// 页面加载时获取数据
onMounted(() => {
  loadStats()
})

// 快速操作
const operations = ref([
  { 
    icon: 'User', 
    title: '教师管理', 
    desc: '添加或编辑教师信息',
    path: '/data/teachers',
    bgColor: '#dbeafe',
    iconColor: '#2563eb'
  },
  { 
    icon: 'OfficeBuilding', 
    title: '班级管理', 
    desc: '管理年级和班级',
    path: '/data/classes',
    bgColor: '#dcfce7',
    iconColor: '#16a34a'
  },
  { 
    icon: 'Setting', 
    title: '约束设置', 
    desc: '配置排课规则和约束优先级',
    path: '/constraints',
    bgColor: '#fef3c7',
    iconColor: '#d97706'
  },
  { 
    icon: 'Download', 
    title: '导出课表', 
    desc: '导出课表数据',
    path: '/export',
    bgColor: '#ede9fe',
    iconColor: '#7c3aed'
  }
])
</script>

<style lang="scss" scoped>
.dashboard {
  max-width: 1400px;
  margin: 0 auto;
}

// 欢迎区域
.welcome-section {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 32px;
  background: linear-gradient(135deg, #1e3a5f 0%, #2563eb 50%, #3b82f6 100%);
  border-radius: 16px;
  margin-bottom: 24px;
  box-shadow: 0 10px 40px rgba(37, 99, 235, 0.3);
  position: relative;
  overflow: hidden;
  
  &::before {
    content: '';
    position: absolute;
    top: -50%;
    right: -20%;
    width: 60%;
    height: 200%;
    background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
    pointer-events: none;
  }
  
  .welcome-content {
    position: relative;
    z-index: 1;
    
    .welcome-title {
      font-size: 28px;
      font-weight: 600;
      color: #fff;
      margin-bottom: 8px;
      
      .greeting {
        opacity: 0.9;
      }
      
      .username {
        color: #fbbf24;
      }
    }
    
    .welcome-desc {
      color: rgba(255, 255, 255, 0.8);
      font-size: 15px;
    }
  }
  
  .quick-actions {
    display: flex;
    gap: 12px;
    position: relative;
    z-index: 1;
    
    .el-button {
      padding: 12px 24px;
      font-size: 15px;
      border-radius: 10px;
      
      &--primary {
        background: #fbbf24;
        border-color: #fbbf24;
        color: #1e3a5f;
        
        &:hover {
          background: #fcd34d;
          border-color: #fcd34d;
        }
      }
      
      &:not(.el-button--primary) {
        background: rgba(255, 255, 255, 0.15);
        border-color: rgba(255, 255, 255, 0.3);
        color: #fff;
        
        &:hover {
          background: rgba(255, 255, 255, 0.25);
        }
      }
    }
  }
}

// 统计卡片网格
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 24px;
}

// 主内容区
.main-content {
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: auto auto;
  gap: 20px;
  
  .card {
    padding: 24px;
    
    .card-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 20px;
      
      h3 {
        font-size: 16px;
        font-weight: 600;
        color: var(--text-primary);
      }
    }
  }
}

// 排课状态卡片
.schedule-status {
  .status-info {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    margin-bottom: 20px;
    
    .status-item {
      .label {
        display: block;
        font-size: 13px;
        color: var(--text-secondary);
        margin-bottom: 8px;
      }
      
      .value {
        font-size: 20px;
        font-weight: 600;
        color: var(--primary-color);
      }
      
      :deep(.el-progress) {
        .el-progress__text {
          font-weight: 600;
        }
      }
    }
  }
  
  .view-detail-btn {
    width: 100%;
    justify-content: center;
    gap: 8px;
  }
}

// 快速操作
.quick-operations {
  .operations-grid {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  
  .operation-item {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 16px;
    background: var(--bg-color);
    border-radius: 12px;
    cursor: pointer;
    transition: all 0.2s ease;
    
    &:hover {
      background: #fff;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
      transform: translateX(4px);
      
      .op-arrow {
        opacity: 1;
        transform: translateX(0);
      }
    }
    
    .op-icon {
      width: 48px;
      height: 48px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
      
      .el-icon {
        font-size: 24px;
      }
    }
    
    .op-info {
      flex: 1;
      
      .op-title {
        font-size: 15px;
        font-weight: 600;
        color: var(--text-primary);
        margin-bottom: 4px;
      }
      
      .op-desc {
        font-size: 13px;
        color: var(--text-secondary);
      }
    }
    
    .op-arrow {
      color: var(--text-muted);
      opacity: 0;
      transform: translateX(-8px);
      transition: all 0.2s ease;
    }
  }
}

// 系统信息
.system-info {
  grid-column: span 2;
  
  .info-list {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 12px;
  }
  
  .info-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 16px;
    background: var(--bg-color);
    border-radius: 8px;
    
    .info-label {
      font-size: 13px;
      color: var(--text-secondary);
    }
    
    .info-value {
      font-size: 13px;
      font-weight: 500;
      color: var(--text-primary);
    }
  }
}

// 响应式
@media (max-width: 1200px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .main-content {
    grid-template-columns: 1fr;
    
    .system-info {
      grid-column: span 1;
    }
  }
}

@media (max-width: 768px) {
  .welcome-section {
    flex-direction: column;
    text-align: center;
    gap: 20px;
    
    .quick-actions {
      flex-direction: column;
      width: 100%;
      
      .el-button {
        width: 100%;
      }
    }
  }
  
  .stats-grid {
    grid-template-columns: 1fr;
  }
}
</style>
