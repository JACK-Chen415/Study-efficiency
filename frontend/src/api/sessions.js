import { request } from './client.js'

export function startSession(payload) {
  return request('/sessions/start', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function endSession(payload) {
  return request('/sessions/end', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function listSessions({ userId, limit = 50, offset = 0 }) {
  const params = new URLSearchParams({
    user_id: String(userId),
    limit: String(limit),
    offset: String(offset),
  })
  return request(`/sessions/list?${params.toString()}`)
}

export function getSession(sessionId) {
  return request(`/sessions/${sessionId}`)
}

export function abandonSession(sessionId, payload = { reason: 'user_requested' }) {
  return request(`/sessions/${sessionId}/abandon`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateSession(sessionId, payload) {
  return request(`/sessions/${sessionId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export function deleteSession(sessionId) {
  return request(`/sessions/${sessionId}`, {
    method: 'DELETE',
  })
}
