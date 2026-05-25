/**
 * ========================================
 * 学生管理 API
 * ========================================
 */

import request, { getBaseURL } from './index'
import axios from 'axios'

/**
 * 获取学生列表
 * @param {Object} params - 查询参数
 * @param {number} params.page - 页码
 * @param {number} params.page_size - 每页数量
 * @param {string} params.grade - 年级过滤
 * @param {string} params.status - 状态过滤
 * @param {string} params.search - 搜索关键词
 * @param {string} params.student_no - 学号精确过滤
 */
export function getStudents(params) {
  return request.get('/students', { params })
}

export function getStudent(id) {
  return request.get(`/students/${id}`)
}

export function createStudent(data) {
  return request.post('/students', data)
}

export function updateStudent(id, data) {
  return request.put(`/students/${id}`, data)
}

export function deleteStudent(id) {
  return request.delete(`/students/${id}`)
}

// ========== 批量导入/模板 ==========

export function getStudentImportTemplateUrl(format = 'xlsx') {
  const fmt = (format || 'xlsx').toLowerCase()
  return `${getBaseURL()}/students/import/template?format=${encodeURIComponent(fmt)}`
}

export async function importStudentsFile(file) {
  const formData = new FormData()
  formData.append('file', file)
  const res = await axios.post(`${getBaseURL()}/students/import`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
  return res.data
}

/**
 * 一键升年级
 * @param {Object} data - { grades?: string[] }
 */
export function promoteStudents(data) {
  return request.post('/students/promote', data)
}
