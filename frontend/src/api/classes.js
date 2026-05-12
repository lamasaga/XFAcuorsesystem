/**
 * ========================================
 * 班级管理 API
 * ========================================
 */

import request from './index'

/**
 * 获取班级列表
 * @param {Object} params - 查询参数
 */
export function getClasses(params) {
  return request.get('/classes', { params })
}

/**
 * 获取单个班级
 * @param {number} id - 班级 ID
 */
export function getClass(id) {
  return request.get(`/classes/${id}`)
}

/**
 * 创建班级
 * @param {Object} data - 班级数据
 */
export function createClass(data) {
  return request.post('/classes', data)
}

/**
 * 更新班级
 * @param {number} id - 班级 ID
 * @param {Object} data - 更新数据
 */
export function updateClass(id, data) {
  return request.put(`/classes/${id}`, data)
}

/**
 * 删除班级
 * @param {number} id - 班级 ID
 */
export function deleteClass(id) {
  return request.delete(`/classes/${id}`)
}
