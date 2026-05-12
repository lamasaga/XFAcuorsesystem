/**
 * ========================================
 * 教学任务管理 API
 * ========================================
 */

import request from './index'

/**
 * 获取教学任务列表
 * @param {Object} params - 查询参数
 */
export function getTasks(params) {
  return request.get('/tasks', { params })
}

/**
 * 获取包含详细信息的教学任务列表
 * 返回数据包含教师姓名、班级名称、科目名称等
 * 
 * @param {Object} params - 查询参数
 * @param {number} params.class_id - 按班级过滤
 * @param {string} params.grade - 按年级过滤
 */
export function getTasksWithDetails(params) {
  return request.get('/tasks/with-details', { params })
}

/**
 * 获取单个教学任务
 * @param {number} id - 任务 ID
 */
export function getTask(id) {
  return request.get(`/tasks/${id}`)
}

/**
 * 创建教学任务
 * @param {Object} data - 任务数据
 * @param {number} data.teacher_id - 教师 ID
 * @param {number} data.class_id - 班级 ID
 * @param {number} data.subject_id - 科目 ID
 * @param {number} data.weekly_hours - 周课时数
 * @param {boolean} data.is_continuous - 是否连堂
 */
export function createTask(data) {
  return request.post('/tasks', data)
}

/**
 * 批量创建教学任务
 * @param {Array} tasks - 任务数据数组
 */
export function createTasksBatch(tasks) {
  return request.post('/tasks/batch', tasks)
}

/**
 * 更新教学任务
 * @param {number} id - 任务 ID
 * @param {Object} data - 更新数据
 */
export function updateTask(id, data) {
  return request.put(`/tasks/${id}`, data)
}

/**
 * 删除教学任务
 * @param {number} id - 任务 ID
 */
export function deleteTask(id) {
  return request.delete(`/tasks/${id}`)
}
