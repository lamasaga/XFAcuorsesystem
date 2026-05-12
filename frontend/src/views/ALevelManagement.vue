<template>
  <div class="alevel-management">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="page-title">
        <h1>
          <el-icon size="24" color="#2563eb"><Notebook /></el-icon>
          A-Level 一生一课表
        </h1>
        <span class="subtitle">管理学生、科目、选课和课程班</span>
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
      <router-view v-if="$route.path !== '/alevel'" />
      <div v-else class="default-content">
        <ALevelStudentManagement />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, markRaw } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { User, Collection, DocumentChecked, School, Notebook } from '@element-plus/icons-vue'
import ALevelStudentManagement from './alevel/ALevelStudentManagement.vue'

const route = useRoute()
const router = useRouter()

const activeType = ref('students')

const dataCards = ref([
  { 
    type: 'students',
    icon: markRaw(User), 
    title: '学生管理', 
    count: 0, 
    unit: '人',
    bgColor: '#dbeafe',
    iconColor: '#2563eb',
    path: '/alevel/students'
  },
  { 
    type: 'subjects',
    icon: markRaw(Collection), 
    title: 'AL科目管理', 
    count: 0, 
    unit: '门',
    bgColor: '#ffedd5',
    iconColor: '#ea580c',
    path: '/alevel/subjects'
  },
  { 
    type: 'selections',
    icon: markRaw(DocumentChecked), 
    title: '选课管理', 
    count: 0, 
    unit: '条记录',
    bgColor: '#dcfce7',
    iconColor: '#16a34a',
    path: '/alevel/selections'
  },
  { 
    type: 'classes',
    icon: markRaw(School), 
    title: '课程班管理', 
    count: 0, 
    unit: '个班',
    bgColor: '#ede9fe',
    iconColor: '#7c3aed',
    path: '/alevel/classes'
  }
])

const selectType = (type) => {
  activeType.value = type
  const card = dataCards.value.find(c => c.type === type)
  if (card) {
    router.push(card.path)
  }
}

watch(() => route.path, (path) => {
  if (path.includes('/alevel/students')) activeType.value = 'students'
  else if (path.includes('/alevel/subjects')) activeType.value = 'subjects'
  else if (path.includes('/alevel/selections')) activeType.value = 'selections'
  else if (path.includes('/alevel/classes')) activeType.value = 'classes'
}, { immediate: true })
</script>

<style lang="scss" scoped>
.alevel-management {
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 24px;
  
  h1 {
    font-size: 24px;
    font-weight: 600;
    color: var(--text-primary);
    display: flex;
    align-items: center;
    gap: 10px;
  }
  
  .subtitle {
    font-size: 14px;
    color: var(--text-secondary);
    margin-left: 12px;
  }
}

.data-type-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
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

.data-content {
  padding: 0;
  min-height: 500px;
}

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
