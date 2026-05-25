import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/dashboard'
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('@/views/Dashboard.vue'),
    meta: { title: '首页' }
  },
  {
    path: '/data',
    name: 'DataManagement',
    component: () => import('@/views/DataManagement.vue'),
    meta: { title: '数据管理' },
    children: [
      {
        path: 'teachers',
        name: 'Teachers',
        component: () => import('@/views/data/TeacherManagement.vue'),
        meta: { title: '教师管理' }
      },
      {
        path: 'classes',
        name: 'Classes',
        component: () => import('@/views/data/ClassManagement.vue'),
        meta: { title: '班级管理' }
      },
      {
        path: 'subjects',
        name: 'Subjects',
        component: () => import('@/views/data/SubjectManagement.vue'),
        meta: { title: '科目管理' }
      },
      {
        path: 'plan',
        name: 'TeachingPlan',
        component: () => import('@/views/data/TeachingPlan.vue'),
        meta: { title: '行政课程' }
      },
      {
        path: 'layers',
        name: 'LayerConfig',
        component: () => import('@/views/data/LayerConfig.vue'),
        meta: { title: '分层课程' }
      },
      {
        path: 'venues',
        name: 'VenueConfig',
        component: () => import('@/views/data/VenueConfig.vue'),
        meta: { title: '场地资源' }
      }
    ]
  },
  {
    path: '/constraints',
    name: 'Constraints',
    component: () => import('@/views/ConstraintSettings.vue'),
    meta: { title: '约束设置' }
  },
  {
    path: '/schedule',
    name: 'AutoSchedule',
    component: () => import('@/views/AutoSchedule.vue'),
    meta: { title: '自动排课' }
  },
  {
    path: '/timetable',
    name: 'Timetable',
    component: () => import('@/views/TimetableView.vue'),
    meta: { title: '课表管理' }
  },
  {
    path: '/export',
    name: 'Export',
    component: () => import('@/views/ExportPage.vue'),
    meta: { title: '导出' }
  },
  {
    path: '/help',
    name: 'Help',
    component: () => import('@/views/HelpGuide.vue'),
    meta: { title: '使用帮助' }
  },
  {
    path: '/alevel',
    name: 'ALevelManagement',
    component: () => import('@/views/ALevelManagement.vue'),
    meta: { title: 'A-Level' },
    children: [
      {
        path: 'students',
        name: 'ALevelStudents',
        component: () => import('@/views/alevel/ALevelStudentManagement.vue'),
        meta: { title: '学生管理' }
      },
      {
        path: 'subjects',
        name: 'ALevelSubjects',
        component: () => import('@/views/alevel/ALevelSubjectManagement.vue'),
        meta: { title: 'AL科目管理' }
      },
      {
        path: 'selections',
        name: 'CourseSelections',
        component: () => import('@/views/alevel/CourseSelectionManagement.vue'),
        meta: { title: '选课管理' }
      },
      {
        path: 'classes',
        name: 'CourseClasses',
        component: () => import('@/views/alevel/CourseClassManagement.vue'),
        meta: { title: '课程班管理' }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})

export default router
