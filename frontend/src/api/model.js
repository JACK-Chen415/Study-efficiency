import { request } from './client.js'

export function trainModel(payload = {}) {
  return request('/model/train', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function predictSession(payload) {
  return request('/model/predict', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function predictNext(payload) {
  return request('/model/predict-next', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function getModelMetrics() {
  return request('/model/metrics')
}

export function getFeatureImportance() {
  return request('/model/feature-importance')
}
