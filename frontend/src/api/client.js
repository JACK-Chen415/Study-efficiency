const DEFAULT_API_BASE_URL = '/api'
const BUILD_ENV = import.meta.env || {}

export const API_BASE_URL = (BUILD_ENV.VITE_API_BASE_URL || DEFAULT_API_BASE_URL).replace(/\/$/, '')

function buildUrl(path) {
  if (/^https?:\/\//.test(path)) {
    return path
  }
  return `${API_BASE_URL}${path.startsWith('/') ? path : `/${path}`}`
}

function normalizeErrorMessage(status, body) {
  if (status === 409 && body?.detail === 'user already has an in-progress session') {
    return '已有未结束的学习会话，请先结束当前学习。'
  }
  if (body && typeof body.detail === 'string') {
    return body.detail
  }
  if (status === 422) {
    return '表单字段校验失败，请补全或修正后重试。'
  }
  if (Array.isArray(body?.detail)) {
    return '表单字段校验失败，请补全或修正后重试。'
  }
  return '请求失败，请稍后重试。'
}

export async function request(path, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  }

  try {
    const response = await fetch(buildUrl(path), {
      ...options,
      headers,
    })

    let body = null
    const text = await response.text()
    if (text) {
      try {
        body = JSON.parse(text)
      } catch {
        body = text
      }
    }

    if (!response.ok) {
      const error = new Error(normalizeErrorMessage(response.status, body))
      error.status = response.status
      error.body = body
      throw error
    }

    return body
  } catch (error) {
    if (error instanceof TypeError) {
      const networkError = new Error('无法连接后端，请检查 API 地址或后端服务。')
      networkError.isNetworkError = true
      throw networkError
    }
    throw error
  }
}
