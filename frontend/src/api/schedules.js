import request from './index'

/**
 * 触发自动排课
 * @param {Object} params - 排课参数
 * @param {string} params.scope - 排课范围: all/grade/class
 * @param {string[]} params.grades - 指定年级列表
 * @param {number[]} params.classes - 指定班级ID列表
 * @param {number} params.optimization - 优化程度 (1-5)
 * @param {number} params.plan_count - 生成方案数量 (1/3/5)
 * @param {boolean} params.keep_manual - 是否保留手动调整
 * @returns {Promise} 排课结果摘要
 */
export function generateSchedule(params = {}) {
  const optimization = params.optimization || 3
  const planCount = params.planCount || 1
  
  // 根据优化程度和方案数量计算超时时间（与后端 time_limits 对齐，加 60s 缓冲）
  // 后端: {1: 30s, 2: 60s, 3: 120s, 4: 300s, 5: 600s}
  const baseTimeout = [90, 120, 180, 360, 660][optimization - 1] || 180
  const timeout = baseTimeout * planCount * 1000  // 转换为毫秒
  
  return request.post('/schedules/generate', {
    scope: params.scope || 'all',
    grades: params.grades || [],
    classes: params.classes || [],
    optimization: optimization,
    plan_count: planCount,
    keep_manual: params.keepManual || false
  }, {
    timeout: timeout  // 为排课操作设置更长的超时时间
  })
}

/**
 * 获取所有课表列表
 * @returns {Promise} 课表列表
 */
export function getScheduleList() {
  return request.get('/schedules')
}

/**
 * 获取课表详情
 * @param {number} scheduleId - 课表 ID
 * @returns {Promise} 课表详情
 */
export function getScheduleDetail(scheduleId) {
  return request.get(`/schedules/${scheduleId}`)
}

/**
 * 获取班级课表
 * @param {number} scheduleId - 课表 ID
 * @param {number} classId - 班级 ID
 * @returns {Promise} 班级课表
 */
export function getClassTimetable(scheduleId, classId) {
  return request.get(`/schedules/${scheduleId}/by-class/${classId}`)
}

/**
 * 获取教师课表
 * @param {number} scheduleId - 课表 ID
 * @param {number} teacherId - 教师 ID
 * @returns {Promise} 教师课表
 */
export function getTeacherTimetable(scheduleId, teacherId) {
  return request.get(`/schedules/${scheduleId}/by-teacher/${teacherId}`)
}

/**
 * 获取场地/教室课表
 * @param {number} scheduleId - 课表 ID
 * @param {number} venueId - 场地 ID
 * @returns {Promise} 场地课表
 */
export function getVenueTimetable(scheduleId, venueId) {
  return request.get(`/schedules/${scheduleId}/by-venue/${venueId}`)
}

/**
 * 激活课表
 * @param {number} scheduleId - 课表 ID
 * @returns {Promise}
 */
export function activateSchedule(scheduleId) {
  return request.put(`/schedules/${scheduleId}/activate`)
}

/**
 * 删除课表
 * @param {number} scheduleId - 课表 ID
 * @returns {Promise}
 */
export function deleteSchedule(scheduleId) {
  return request.delete(`/schedules/${scheduleId}`)
}

/**
 * 交换两个课程的位置
 * @param {number} scheduleId - 课表 ID
 * @param {Object} params - 调换参数
 * @param {number} params.item1_day - 第一个课程的星期
 * @param {number} params.item1_period - 第一个课程的节次
 * @param {number} params.item1_class_id - 第一个课程的班级ID
 * @param {number} params.item2_day - 第二个课程的星期
 * @param {number} params.item2_period - 第二个课程的节次
 * @param {number} params.item2_class_id - 第二个课程的班级ID
 * @returns {Promise}
 */
export function swapScheduleItems(scheduleId, params) {
  return request.post(`/schedules/${scheduleId}/swap`, null, { params })
}

/**
 * 移动一个课程到新位置
 * @param {number} scheduleId - 课表 ID
 * @param {number} itemId - 课程项ID
 * @param {number} toDay - 目标星期
 * @param {number} toPeriod - 目标节次
 * @returns {Promise}
 */
export function moveScheduleItem(scheduleId, itemId, toDay, toPeriod) {
  return request.post(`/schedules/${scheduleId}/move`, null, {
    params: { item_id: itemId, to_day: toDay, to_period: toPeriod }
  })
}

/**
 * 获取约束配置
 * @returns {Promise} 当前约束配置
 */
export function getScheduleConfig() {
  return request.get('/schedules/config')
}

/**
 * 保存约束配置
 * @param {Object} data - { name, config: { soft_constraints, meeting_slots } }
 * @returns {Promise}
 */
export function saveScheduleConfig(data) {
  return request.put('/schedules/config', data)
}

/**
 * 锁定/解锁课程项
 * @param {number} scheduleId - 课表 ID
 * @param {number} itemId - 课程项 ID
 * @param {boolean} locked - 是否锁定
 * @returns {Promise}
 */
export function toggleLockItem(scheduleId, itemId, locked = true) {
  return request.put(`/schedules/${scheduleId}/items/${itemId}/lock`, null, {
    params: { locked }
  })
}

/**
 * 获取调换候选位置分析
 * @param {number} scheduleId - 课表 ID
 * @param {Object} params - { day, period, class_id }
 * @returns {Promise}
 */
export function getSwapCandidates(scheduleId, params) {
  return request.get(`/schedules/${scheduleId}/swap-candidates`, { params })
}

/**
 * 验证课表约束违反情况
 * @param {number} scheduleId - 课表 ID
 * @param {number|null} classId - 可选，限定班级视角
 * @returns {Promise}
 */
export function validateSchedule(scheduleId, classId = null) {
  const params = {}
  if (classId) params.class_id = classId
  return request.get(`/schedules/${scheduleId}/validate`, { params })
}
