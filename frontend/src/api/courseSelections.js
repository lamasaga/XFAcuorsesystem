/**
 * ========================================
 * 选课管理 API
 * ========================================
 */

import request from './index'

export function getCourseSelections(params) {
  return request.get('/course-selections', { params })
}

export function getCourseSelection(id) {
  return request.get(`/course-selections/${id}`)
}

export function createCourseSelection(data) {
  return request.post('/course-selections', data)
}

export function updateCourseSelection(id, data) {
  return request.put(`/course-selections/${id}`, data)
}

export function deleteCourseSelection(id) {
  return request.delete(`/course-selections/${id}`)
}
