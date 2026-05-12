/**
 * ========================================
 * 场地资源 API
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
 * 获取场地列表
 * @param {Object} params - 查询参数
 */
export function getVenues(params) {
  return request.get('/venues', { params })
}

/**
 * 获取单个场地
 * @param {number} id - 场地 ID
 */
export function getVenue(id) {
  return request.get(`/venues/${id}`)
}

/**
 * 创建场地
 * @param {Object} data - 场地数据
 */
export function createVenue(data) {
  return request.post('/venues', data)
}

/**
 * 更新场地
 * @param {number} id - 场地 ID
 * @param {Object} data - 更新数据
 */
export function updateVenue(id, data) {
  return request.put(`/venues/${id}`, data)
}

/**
 * 删除场地
 * @param {number} id - 场地 ID
 */
export function deleteVenue(id) {
  return request.delete(`/venues/${id}`)
}

// ========== 批量导入/模板 ==========

export function getVenueImportTemplateUrl(format = 'xlsx') {
  const fmt = (format || 'xlsx').toLowerCase()
  return `${getBaseURL()}/venues/import/template?format=${encodeURIComponent(fmt)}`
}

export async function importVenuesFile(file) {
  const formData = new FormData()
  formData.append('file', file)
  const res = await axios.post(`${getBaseURL()}/venues/import`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
  return res.data
}
