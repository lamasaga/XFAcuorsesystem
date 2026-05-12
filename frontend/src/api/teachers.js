/**
 * ========================================
 * 教师管理 API
 * ========================================
 * 
 * 封装所有与教师相关的 API 调用。
 * 
 * 使用方法：
 *   import { getTeachers, createTeacher } from '@/api/teachers'
 *   
 *   // 获取教师列表
 *   const res = await getTeachers({ page: 1, page_size: 20 })
 *   console.log(res.data.items)  // 教师列表
 *   
 *   // 创建教师
 *   await createTeacher({ name: '张三', type: 'CN' })
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
 * 获取教师列表
 * 
 * @param {Object} params - 查询参数
 * @param {number} params.page - 页码（默认 1）
 * @param {number} params.page_size - 每页数量（默认 20）
 * @param {string} params.type - 教师类型过滤（CN/EN）
 * @param {string} params.department - 学部过滤（PRIMARY/SECONDARY）
 * @param {string} params.search - 搜索关键词
 * @param {number} params.max_weekly_hours - 每周最大课时过滤
 * @returns {Promise} API 响应
 * 
 * @example
 *   // 获取第一页，每页20条
 *   const res = await getTeachers({ page: 1, page_size: 20 })
 *   
 *   // 只获取中教
 *   const res = await getTeachers({ type: 'CN' })
 */
export function getTeachers(params) {
  return request.get('/teachers', { params })
}

/**
 * 获取单个教师详情
 * 
 * @param {number} id - 教师 ID
 * @returns {Promise} API 响应
 */
export function getTeacher(id) {
  return request.get(`/teachers/${id}`)
}

/**
 * 创建教师
 * 
 * @param {Object} data - 教师数据
 * @param {string} data.name - 教师姓名（必填）
 * @param {string} data.type - 教师类型（CN/EN，默认 CN）
 * @param {string} data.department - 学部（PRIMARY/SECONDARY）
 * @param {string[]} data.subjects - 任教科目列表
 * @param {string[]} data.tags - 教师标签
 * @param {number} data.max_weekly_hours - 每周最大课时
 * @returns {Promise} API 响应
 * 
 * @example
 *   await createTeacher({
 *     name: '张三',
 *     type: 'CN',
 *     department: 'PRIMARY',
 *     subjects: ['语文', '数学'],
 *     tags: ['HOMEROOM_TEACHER']
 *   })
 */
export function createTeacher(data) {
  return request.post('/teachers', data)
}

/**
 * 更新教师信息
 * 
 * @param {number} id - 教师 ID
 * @param {Object} data - 更新数据（只传需要更新的字段）
 * @returns {Promise} API 响应
 * 
 * @example
 *   // 只更新姓名
 *   await updateTeacher(1, { name: '李四' })
 */
export function updateTeacher(id, data) {
  return request.put(`/teachers/${id}`, data)
}

/**
 * 删除教师
 * 
 * @param {number} id - 教师 ID
 * @returns {Promise} API 响应
 */
export function deleteTeacher(id) {
  return request.delete(`/teachers/${id}`)
}

// ========== 教研组 API ==========

export function getResearchGroups() {
  return request.get('/teachers/research-groups')
}

export function createResearchGroup(data) {
  return request.post('/teachers/research-groups', data)
}

export function deleteResearchGroup(id) {
  return request.delete(`/teachers/research-groups/${id}`)
}

// ========== 批量导入/模板 ==========

export function getTeacherImportTemplateUrl(format = 'xlsx') {
  const fmt = (format || 'xlsx').toLowerCase()
  return `${getBaseURL()}/teachers/import/template?format=${encodeURIComponent(fmt)}`
}

export async function importTeachersFile(file) {
  const formData = new FormData()
  formData.append('file', file)
  const res = await axios.post(`${getBaseURL()}/teachers/import`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
  return res.data
}
