/**
 * ========================================
 * 课程班管理 API
 * ========================================
 */

import request from './index'

export function getCourseClasses(params) {
  return request.get('/course-classes', { params })
}

export function getCourseClass(id) {
  return request.get(`/course-classes/${id}`)
}

export function createCourseClass(data) {
  return request.post('/course-classes', data)
}

export function updateCourseClass(id, data) {
  return request.put(`/course-classes/${id}`, data)
}

export function deleteCourseClass(id) {
  return request.delete(`/course-classes/${id}`)
}

export function getCourseClassMembers(classId) {
  return request.get(`/course-classes/${classId}/members`)
}

export function addCourseClassMember(classId, data) {
  return request.post(`/course-classes/${classId}/members`, data)
}

export function removeCourseClassMember(memberId) {
  return request.delete(`/course-classes/members/${memberId}`)
}
