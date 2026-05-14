<template>
  <div class="app-container">
    <!-- 后端就绪检测遮罩 -->
    <div v-if="!backendReady" class="backend-loading-overlay">
      <div class="backend-loading-content">
        <el-icon class="loading-icon" :size="48"><Loading /></el-icon>
        <p class="loading-text">正在连接后端服务...</p>
        <p class="loading-hint">请稍候，首次启动可能需要 5-10 秒</p>
      </div>
    </div>

    <!-- 顶部导航栏 -->
    <header class="app-header">
      <div class="header-left">
        <div class="logo">
          <img class="logo-img" src="/logo.png" alt="logo" />
          <span class="logo-text">智能排课系统</span>
        </div>
      </div>
      
      <nav class="header-nav">
        <router-link 
          v-for="item in navItems" 
          :key="item.path"
          :to="item.path"
          class="nav-item"
          :class="{ active: isActiveRoute(item.path) }"
        >
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.title }}</span>
        </router-link>
      </nav>
      
      <div class="header-right">
        <div class="system-badge">
          <img class="badge-img" src="/logo.png" alt="logo" />
          <span>K-12 智能排课</span>
        </div>
      </div>
    </header>
    
    <!-- 主内容区域 -->
    <main class="app-main">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>
    
    <!-- 底部状态栏 -->
    <footer class="app-footer">
      <div class="status-left">
        <span class="status-item">
          <el-icon><User /></el-icon>
          教师 <strong>{{ stats.teachers }}</strong> 人
        </span>
        <span class="status-divider">|</span>
        <span class="status-item">
          <el-icon><OfficeBuilding /></el-icon>
          班级 <strong>{{ stats.classes }}</strong> 个
        </span>
        <span class="status-divider">|</span>
        <span class="status-item">
          <el-icon><Reading /></el-icon>
          科目 <strong>{{ stats.subjects }}</strong> 门
        </span>
        <span class="status-divider">|</span>
        <span class="status-item">
          <el-icon><User /></el-icon>
          A-Level学生 <strong>{{ stats.students }}</strong> 人
        </span>
        <span class="status-divider">|</span>
        <span class="status-item">
          <el-icon><School /></el-icon>
          课程班 <strong>{{ stats.courseClasses }}</strong> 个
        </span>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { ref, computed, markRaw, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { 
  User, OfficeBuilding, Reading, Clock, HomeFilled, DataAnalysis,
  SetUp, Refresh, Calendar, Download, Cpu, Notebook, School, Loading
} from '@element-plus/icons-vue'
import { getOverviewStats } from '@/api/stats'
import { getStudents } from '@/api/students'
import { getCourseClasses } from '@/api/courseClasses'

const route = useRoute()

// 后端就绪状态
const backendReady = ref(false)
const backendCheckAttempts = ref(0)
const MAX_BACKEND_CHECK_ATTEMPTS = 60  // 最多检测 60 次（约 30 秒）

/**
 * 轮询检测后端是否就绪
 */
const checkBackendReady = async () => {
  const baseURL = import.meta.env.VITE_API_BASE || 'http://localhost:8001/api/v1'
  const healthURL = baseURL.replace('/api/v1', '')  // 去掉 /api/v1，访问根路径

  while (backendCheckAttempts.value < MAX_BACKEND_CHECK_ATTEMPTS) {
    try {
      const response = await fetch(healthURL, { method: 'GET', mode: 'no-cors' })
      // no-cors 模式下无法读取 response，但只要不抛错就说明后端已启动
      backendReady.value = true
      break
    } catch {
      backendCheckAttempts.value++
      await new Promise(r => setTimeout(r, 500))
    }
  }

  // 即使检测失败（超时），也放行，让页面正常显示（后续请求自行处理错误）
  if (!backendReady.value) {
    backendReady.value = true
  }
}

// 导航项配置 - 使用 markRaw 包装图标组件避免响应式警告
const navItems = [
  { path: '/dashboard', title: '首页', icon: markRaw(HomeFilled) },
  { path: '/data', title: '数据管理', icon: markRaw(DataAnalysis) },
  { path: '/alevel', title: 'A-Level', icon: markRaw(Notebook) },
  { path: '/constraints', title: '约束设置', icon: markRaw(SetUp) },
  { path: '/schedule', title: '自动排课', icon: markRaw(Refresh) },
  { path: '/timetable', title: '课表管理', icon: markRaw(Calendar) },
  { path: '/export', title: '导出', icon: markRaw(Download) }
]

// 统计数据（从 API 动态获取）
const stats = ref({
  teachers: 0,
  classes: 0,
  subjects: 0,
  students: 0,
  courseClasses: 0
})

/**
 * 加载底部状态栏统计数据
 */
const loadFooterStats = async () => {
  try {
    const res = await getOverviewStats()
    const data = res.data
    stats.value.teachers = data.teacher_count || 0
    stats.value.classes = data.class_count || 0
    stats.value.subjects = data.subject_count || 0
  } catch {
    // 静默失败
  }
  
  try {
    const studentRes = await getStudents({ page: 1, page_size: 1 })
    stats.value.students = studentRes.data?.total || 0
  } catch {
    // 静默失败
  }
  
  try {
    const classRes = await getCourseClasses({ page: 1, page_size: 1 })
    stats.value.courseClasses = classRes.data?.total || 0
  } catch {
    // 静默失败
  }
}

onMounted(() => {
  checkBackendReady().then(() => {
    loadFooterStats()
  })
})

// 判断路由是否激活
const isActiveRoute = (path) => {
  if (path === '/dashboard') {
    return route.path === '/dashboard' || route.path === '/'
  }
  return route.path.startsWith(path)
}
</script>

<style lang="scss" scoped>
.app-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: linear-gradient(135deg, #f0f4ff 0%, #f8fafc 50%, #f0fdf4 100%);
}

// 顶部导航栏
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 64px;
  padding: 0 24px;
  background: linear-gradient(135deg, #1e3a5f 0%, #2563eb 100%);
  box-shadow: 0 2px 12px rgba(37, 99, 235, 0.2);
  position: relative;
  z-index: 100;
  
  &::after {
    content: '';
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
  }
}

.header-left {
  .logo {
    display: flex;
    align-items: center;
    gap: 10px;
    
    .logo-img {
      width: 32px;
      height: 32px;
      object-fit: contain;
      border-radius: 6px;
      background: rgba(255, 255, 255, 0.12);
      padding: 2px;
      box-shadow: 0 2px 6px rgba(0, 0, 0, 0.12);
    }
    
    .logo-text {
      font-size: 18px;
      font-weight: 600;
      color: #fff;
      letter-spacing: 1px;
    }
  }
}

.header-nav {
  display: flex;
  gap: 4px;
  
  .nav-item {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 16px;
    color: rgba(255, 255, 255, 0.75);
    text-decoration: none;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 500;
    transition: all 0.2s ease;
    
    .el-icon {
      font-size: 16px;
    }
    
    &:hover {
      color: #fff;
      background: rgba(255, 255, 255, 0.1);
    }
    
    &.active {
      color: #fff;
      background: rgba(255, 255, 255, 0.2);
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
      
      &::after {
        content: '';
        position: absolute;
        bottom: -8px;
        left: 50%;
        transform: translateX(-50%);
        width: 24px;
        height: 3px;
        background: #fbbf24;
        border-radius: 2px;
      }
    }
  }
}

.header-right {
  .system-badge {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 14px;
    border-radius: 20px;
    background: rgba(255, 255, 255, 0.1);
    color: rgba(255, 255, 255, 0.8);
    font-size: 13px;
    
    .badge-img {
      width: 16px;
      height: 16px;
      object-fit: contain;
      border-radius: 3px;
      background: rgba(255, 255, 255, 0.18);
      padding: 1px;
    }
  }
}

// 主内容区域
.app-main {
  flex: 1;
  padding: 24px;
  overflow: auto;
}

// 底部状态栏
.app-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 40px;
  padding: 0 24px;
  background: #fff;
  border-top: 1px solid var(--border-color);
  font-size: 13px;
  color: var(--text-secondary);
}

.status-left,
.status-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 4px;
  
  .el-icon {
    font-size: 14px;
    color: var(--text-muted);
  }
  
  strong {
    color: var(--primary-color);
    font-weight: 600;
  }
}

.status-divider {
  color: var(--border-color);
  margin: 0 4px;
}

// 引擎标识
.status-engine {
  font-weight: 500;
  color: var(--text-secondary);
}

// 后端加载遮罩
.backend-loading-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.96);
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;

  .backend-loading-content {
    text-align: center;

    .loading-icon {
      color: var(--el-color-primary);
      animation: spin 1.5s linear infinite;
    }

    .loading-text {
      margin-top: 16px;
      font-size: 16px;
      font-weight: 500;
      color: var(--el-text-color-primary);
    }

    .loading-hint {
      margin-top: 8px;
      font-size: 13px;
      color: var(--el-text-color-secondary);
    }
  }
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
