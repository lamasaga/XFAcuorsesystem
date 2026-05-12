/**
 * ========================================
 * 科目管理 API
 * ========================================
 */

import request from './index'
import axios from 'axios'

function getBaseURL() {
  if (import.meta.env.VITE_API_BASE) {
    return import.meta.env.VITE_API_BASE
  }
  return 'http://localhost:8000/api/v1'
}

/**
 * 获取科目列表
 * @param {Object} params - 查询参数
 */
export function getSubjects(params) {
  return request.get('/subjects', { params })
}

/**
 * 获取单个科目
 * @param {number} id - 科目 ID
 */
export function getSubject(id) {
  return request.get(`/subjects/${id}`)
}

/**
 * 创建科目
 * @param {Object} data - 科目数据
 */
export function createSubject(data) {
  return request.post('/subjects', data)
}

/**
 * 更新科目
 * @param {number} id - 科目 ID
 * @param {Object} data - 更新数据
 */
export function updateSubject(id, data) {
  return request.put(`/subjects/${id}`, data)
}

/**
 * 删除科目
 * @param {number} id - 科目 ID
 */
export function deleteSubject(id) {
  return request.delete(`/subjects/${id}`)
}

// ========== 批量导入/模板 ==========

export function getSubjectImportTemplateUrl(format = 'xlsx') {
  const fmt = (format || 'xlsx').toLowerCase()
  return `${getBaseURL()}/subjects/import/template?format=${encodeURIComponent(fmt)}`
}

export async function importSubjectsFile(file) {
  const formData = new FormData()
  formData.append('file', file)
  const res = await axios.post(`${getBaseURL()}/subjects/import`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
  return res.data
}
