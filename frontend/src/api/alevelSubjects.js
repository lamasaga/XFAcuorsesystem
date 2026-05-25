/**
 * ========================================
 * A-Level 科目管理 API
 * ========================================
 */

import request, { getBaseURL } from './index'
import axios from 'axios'

export function getAlevelSubjects(params) {
  return request.get('/alevel-subjects', { params })
}

export function getAlevelSubject(id) {
  return request.get(`/alevel-subjects/${id}`)
}

export function createAlevelSubject(data) {
  return request.post('/alevel-subjects', data)
}

export function updateAlevelSubject(id, data) {
  return request.put(`/alevel-subjects/${id}`, data)
}

export function deleteAlevelSubject(id) {
  return request.delete(`/alevel-subjects/${id}`)
}

// ========== 批量导入/模板 ==========

export function getAlevelSubjectImportTemplateUrl(format = 'xlsx') {
  const fmt = (format || 'xlsx').toLowerCase()
  return `${getBaseURL()}/alevel-subjects/import/template?format=${encodeURIComponent(fmt)}`
}

export async function importAlevelSubjectsFile(file) {
  const formData = new FormData()
  formData.append('file', file)
  const res = await axios.post(`${getBaseURL()}/alevel-subjects/import`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
  return res.data
}
