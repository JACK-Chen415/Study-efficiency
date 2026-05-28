import { request } from './client.js'

export function simpleLogin(payload) {
  return request('/users/simple-login', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

