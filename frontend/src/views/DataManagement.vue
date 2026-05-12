<template>
  <div class="data-management">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="page-title">
        <h1>数据管理</h1>
        <span class="subtitle">管理教师、班级、科目、行政课程和分层课程</span>
      </div>
    </div>
    
    <!-- 数据类型选择卡片 -->
    <div class="data-type-cards">
      <div 
        v-for="card in dataCards" 
        :key="card.type"
        class="type-card"
        :class="{ active: activeType === card.type }"
        @click="selectType(card.type)"
      >
        <div class="card-icon" :style="{ background: card.bgColor }">
          <el-icon :style="{ color: card.iconColor }">
            <component :is="card.icon" />
          </el-icon>
        </div>
        <div class="card-info">
          <div class="card-title">{{ card.title }}</div>
          <div class="card-count">{{ card.count }} {{ card.unit }}</div>
        </div>
      </div>
    </div>
    
    <!-- 数据内容区 -->
    <div class="data-content card">
      <router-view v-if="$route.path !== '/data'" />
      
      <!-- 默认显示教师管理 -->
      <div v-else class="default-content">
        <TeacherManagement />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, markRaw } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { User, OfficeBuilding, Reading, Document, School, Share, Location } from '@element-plus/icons-vue'
import TeacherManagement from './data/TeacherManagement.vue'
import { getOverviewStats } from '@/api/stats'

const route = useRoute()
const router = useRouter()

const activeType = ref('teachers')

// 数据卡片配置
const dataCards = ref([
  { 
    type: 'teachers',
    icon: markRaw(User), 
    title: '教师管理', 
    count: 0, 
    unit: '人',
    bgColor: '#dbeafe',
    iconColor: '#2563eb',
    path: '/data/teachers'
  },
  { 
    type: 'classes',
    icon: markRaw(OfficeBuilding), 
    title: '班级管理', 
    count: 0, 
    unit: '个',
    bgColor: '#dcfce7',
    iconColor: '#16a34a',
    path: '/data/classes'
  },
  { 
    type: 'subjects',
    icon: markRaw(Reading), 
    title: '科目管理', 
    count: 0, 
    unit: '门',
    bgColor: '#ffedd5',
    iconColor: '#ea580c',
    path: '/data/subjects'
  },
  { 
    type: 'plan',
    icon: markRaw(Document), 
    title: '行政课程', 
    count: 0, 
    unit: '个任务',
    bgColor: '#ede9fe',
    iconColor: '#7c3aed',
    path: '/data/plan'
  },
  { 
    type: 'layers',
    icon: markRaw(Share), 
    title: '分层课程', 
    count: 0, 
    unit: '组',
    bgColor: '#fce7f3',
    iconColor: '#db2777',
    path: '/data/layers'
  },
  { 
    type: 'venues',
    icon: markRaw(Location), 
    title: '场地资源', 
    count: 0, 
    unit: '个',
    bgColor: '#ccfbf1',
    iconColor: '#0d9488',
    path: '/data/venues'
  }
])

/**
 * 加载统计数据
 */
const loadStats = async () => {
  try {
    const res = await getOverviewStats()
    const data = res.data
    
    // 更新各卡片的数量
    const counts = {
      teachers: data.teacher_count,
      classes: data.class_count,
      subjects: data.subject_count,
      plan: data.task_count,
      layers: data.layer_group_count,
      venues: data.venue_count
    }
    
    dataCards.value.forEach(card => {
      if (counts[card.type] !== undefined) {
        card.count = counts[card.type]
      }
    })
  } catch (error) {
    console.error('加载统计数据失败:', error)
  }
}

// 页面加载时获取数据
onMounted(() => {
  loadStats()
})

// 选择数据类型
const selectType = (type) => {
  activeType.value = type
  const card = dataCards.value.find(c => c.type === type)
  if (card) {
    router.push(card.path)
  }
}

// 监听路由变化
watch(() => route.path, (path) => {
  if (path.includes('teachers')) activeType.value = 'teachers'
  else if (path.includes('classes')) activeType.value = 'classes'
  else if (path.includes('subjects')) activeType.value = 'subjects'
  else if (path.includes('plan')) activeType.value = 'plan'
  else if (path.includes('layers')) activeType.value = 'layers'
  else if (path.includes('venues')) activeType.value = 'venues'
}, { immediate: true })
</script>

<style lang="scss" scoped>
.data-management {
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 24px;
  
  h1 {
    font-size: 24px;
    font-weight: 600;
    color: var(--text-primary);
  }
  
  .subtitle {
    font-size: 14px;
    color: var(--text-secondary);
    margin-left: 12px;
  }
}

// 数据类型卡片
.data-type-cards {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.type-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  background: #fff;
  border-radius: 12px;
  border: 2px solid transparent;
  cursor: pointer;
  transition: all 0.25s ease;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  
  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
  }
  
  &.active {
    border-color: var(--primary-color);
    background: linear-gradient(135deg, #f0f7ff 0%, #fff 100%);
    
    .card-title {
      color: var(--primary-color);
    }
  }
  
  .card-icon {
    width: 56px;
    height: 56px;
    border-radius: 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    
    .el-icon {
      font-size: 28px;
    }
  }
  
  .card-info {
    .card-title {
      font-size: 15px;
      font-weight: 600;
      color: var(--text-primary);
      margin-bottom: 4px;
    }
    
    .card-count {
      font-size: 13px;
      color: var(--text-secondary);
    }
  }
}

// 数据内容区
.data-content {
  padding: 0;
  min-height: 500px;
}

// 响应式
@media (max-width: 1200px) {
  .data-type-cards {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  .data-type-cards {
    grid-template-columns: 1fr;
  }
}
</style>
