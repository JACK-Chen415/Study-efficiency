import { request } from './client.js'

function userParams(userId) {
  return new URLSearchParams({ user_id: String(userId) }).toString()
}

export function getAnalyticsOverview(userId) {
  return request(`/analytics/overview?${userParams(userId)}`)
}

export function getAnalyticsTrend(userId) {
  return request(`/analytics/trend?${userParams(userId)}`)
}

export function getAnalyticsFactorAnalysis(userId) {
  return request(`/analytics/factor-analysis?${userParams(userId)}`)
}
