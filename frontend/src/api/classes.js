/**
 * ========================================
 * 班级管理 API
 * ========================================
 */

import request, { getBaseURL } from './index'
import axios from 'axios'

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

// ========== 批量导入/模板 ==========

export function getClassImportTemplateUrl(format = 'xlsx') {
  const fmt = (format || 'xlsx').toLowerCase()
  return `${getBaseURL()}/classes/import/template?format=${encodeURIComponent(fmt)}`
}

export async function importClassesFile(file) {
  const formData = new FormData()
  formData.append('file', file)
  const res = await axios.post(`${getBaseURL()}/classes/import`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
  return res.data
}

/**
 * 一键升班
 * @param {Object} data - { grades?: string[] }
 */
export function promoteClasses(data) {
  return request.post('/classes/promote', data)
}
