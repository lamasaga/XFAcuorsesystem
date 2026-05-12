/**
 * ========================================
 * 统计数据 API
 * ========================================
 */

import request from './index'

/**
 * 获取系统概览统计
 * @returns {Promise} 统计数据
 */
export function getOverviewStats() {
  return request.get('/stats/overview')
}

/**
 * 检查排课数据准备状态
 * @returns {Promise} 检查结果
 */
export function checkDataReadiness() {
  return request.get('/stats/data-check')
}

/**
 * 获取指定课表的统计信息
 * @param {number} scheduleId - 课表 ID
 * @returns {Promise} 课表统计
 */
export function getScheduleStats(scheduleId) {
  return request.get(`/stats/schedule-stats/${scheduleId}`)
}
