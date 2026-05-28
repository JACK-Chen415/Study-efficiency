const USER_KEY = 'study-efficiency:user'
const SESSION_KEY = 'study-efficiency:active-session'

function readJson(key) {
  try {
    const raw = localStorage.getItem(key)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

function writeJson(key, value) {
  localStorage.setItem(key, JSON.stringify(value))
}

export function loadUser() {
  return readJson(USER_KEY)
}

export function saveUser(user) {
  writeJson(USER_KEY, user)
}

export function clearUser() {
  localStorage.removeItem(USER_KEY)
}

export function loadActiveSession() {
  return readJson(SESSION_KEY)
}

export function saveActiveSession(session) {
  writeJson(SESSION_KEY, session)
}

export function clearActiveSession() {
  localStorage.removeItem(SESSION_KEY)
}

