import { request } from './client.js'

export function uploadMotion(payload) {
  return request('/motion/upload', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

