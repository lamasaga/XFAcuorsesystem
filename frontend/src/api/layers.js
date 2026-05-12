/**
 * ========================================
 * 分层/合班课程 API (Layer & Combine Courses)
 * ========================================
 * 
 * 支持两种模式：
 * 1. LAYER (分层)：年级内所有班级参与，学生按能力分层，多个老师同时教
 * 2. COMBINE (合班)：指定班级合并上课，同一个老师教多个班
 */

import request from './index'

/**
 * 获取分层/合班课程列表
 * @param {Object} params - 查询参数
 */
export function getLayerGroups(params) {
  return request.get('/layers', { params })
}

/**
 * 获取单个分层/合班课程
 * @param {number} id - 课程 ID
 */
export function getLayerGroup(id) {
  return request.get(`/layers/${id}`)
}

/**
 * 创建分层/合班课程
 * @param {Object} data - 课程数据
 *   - group_type: 类型 'LAYER' | 'COMBINE'
 *   - subject_id: 科目ID
 *   - grades: 适用年级列表 (分层模式必填)
 *   - class_ids: 合班班级ID列表 (合班模式必填)
 *   - layer_count: 分层数量 (分层模式使用)
 *   - teacher_ids: 教师ID列表 (分层多个，合班一个)
 *   - weekly_hours: 周课时
 *   - is_cross_grade: 是否跨年级 (仅分层模式)
 *   - needs_continuous: 是否需要连堂
 */
export function createLayerGroup(data) {
  return request.post('/layers', data)
}

/**
 * 更新分层/合班课程
 * @param {number} id - 课程 ID
 * @param {Object} data - 更新数据
 */
export function updateLayerGroup(id, data) {
  return request.put(`/layers/${id}`, data)
}

/**
 * 删除分层/合班课程
 * @param {number} id - 课程 ID
 */
export function deleteLayerGroup(id) {
  return request.delete(`/layers/${id}`)
}
