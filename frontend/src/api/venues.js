/**
 * ========================================
 * 场地资源 API
 * ========================================
 */

import request from './index'

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
