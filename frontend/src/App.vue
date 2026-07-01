<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { showConfirmDialog, showToast } from 'vant'
import {
  getAnalyticsFactorAnalysis,
  getAnalyticsOverview,
  getAnalyticsTrend,
} from './api/analytics'
import { uploadMotion } from './api/motion'
import { predictNext, predictSession, trainModel } from './api/model'
import { simpleLogin } from './api/users'
import {
  abandonSession,
  deleteSession,
  endSession,
  getSession,
  listSessions,
  startSession,
  updateSession,
} from './api/sessions'
import { useMotionTracker } from './composables/useMotionTracker'
import {
  clearActiveSession,
  clearUser,
  loadActiveSession,
  loadUser,
  saveActiveSession,
  saveUser,
} from './storage'

const locationOptions = [
  { label: '宿舍', value: 'dormitory' },
  { label: '图书馆', value: 'library' },
  { label: '教室', value: 'classroom' },
  { label: '自习室', value: 'study_room' },
  { label: '其他', value: 'other' },
]

const taskTypeOptions = [
  { label: '课程作业', value: 'coursework' },
  { label: '考试复习', value: 'exam_review' },
  { label: '编程实践', value: 'coding' },
  { label: '阅读论文', value: 'paper_reading' },
  { label: '考研学习', value: 'postgraduate_prep' },
  { label: '其他', value: 'other' },
]

const labelMap = {
  low: '低效率',
  medium: '中等效率',
  high: '高效率',
}

const timePeriodMap = {
  morning: '上午',
  afternoon: '下午',
  evening: '晚上',
  late_night: '深夜',
}

const featureNameMap = {
  duration_minutes: '学习时长',
  goal_clarity: '目标清晰度',
  light_level: '光照感受',
  noise_level: '噪声程度',
  fatigue_level: '疲劳程度',
  mood_stress: '心情/压力',
  phone_distraction: '手机干扰',
  move_count: '移动次数',
  shake_count: '晃动次数',
  still_ratio: '静止占比',
  avg_acceleration: '平均加速度',
  max_acceleration: '最大加速度',
  motion_available: '运动特征可用',
}

const statusMap = {
  in_progress: '进行中',
  completed: '已完成',
  abandoned: '已放弃',
}

const scaleFields = [
  {
    key: 'goal_clarity',
    label: '目标清晰度',
    descriptions: [
      '1 分：完全不清楚本次要完成什么。',
      '2 分：大致有方向，但任务和标准都模糊。',
      '3 分：知道主要任务，但步骤或完成标准一般。',
      '4 分：目标、步骤比较清楚。',
      '5 分：目标、步骤和完成标准都非常明确。',
    ],
  },
  {
    key: 'light_level',
    label: '光照感受',
    descriptions: [
      '1 分：过暗、刺眼或明显影响阅读。',
      '2 分：光照不太舒服，需要频繁调整。',
      '3 分：基本可接受，对学习影响不大。',
      '4 分：光线稳定、比较舒适。',
      '5 分：光照非常舒适，几乎没有干扰。',
    ],
  },
  {
    key: 'noise_level',
    label: '噪声程度',
    descriptions: [
      '1 分：非常安静。',
      '2 分：偶尔有轻微声音。',
      '3 分：有背景声音，但还能专注。',
      '4 分：较吵，明显分散注意力。',
      '5 分：非常吵，很难保持学习状态。',
    ],
  },
  {
    key: 'fatigue_level',
    label: '疲劳程度',
    descriptions: [
      '1 分：精力充足，几乎不累。',
      '2 分：轻微疲劳，不影响学习。',
      '3 分：有疲劳感，需要主动维持专注。',
      '4 分：比较疲惫，效率明显下降。',
      '5 分：非常疲劳，难以继续有效学习。',
    ],
  },
  {
    key: 'mood_stress',
    label: '心情/压力',
    descriptions: [
      '1 分：心情平稳，压力很低。',
      '2 分：有一点压力，但状态较好。',
      '3 分：压力中等，偶尔影响注意力。',
      '4 分：压力较高，明显影响学习。',
      '5 分：压力很大或情绪很差，难以投入。',
    ],
  },
  {
    key: 'phone_distraction',
    label: '手机干扰程度',
    descriptions: [
      '1 分：几乎没有看手机或被打断。',
      '2 分：偶尔查看手机，影响很小。',
      '3 分：有几次分心，需要重新进入状态。',
      '4 分：频繁被手机打断。',
      '5 分：手机严重干扰，本次学习被明显破坏。',
    ],
  },
  {
    key: 'efficiency_score',
    label: '学习效率评分',
    descriptions: [
      '1 分：几乎没有完成有效学习。',
      '2 分：完成很少，效率偏低。',
      '3 分：完成了基本任务，效率中等。',
      '4 分：完成较好，效率较高。',
      '5 分：高度专注，完成质量和效率都很好。',
    ],
  },
]

const storedUser = loadUser()
const storedActiveSession = loadActiveSession()
const user = ref(storedUser)
const pendingActiveSession = ref(storedActiveSession)
const activeSession = ref(null)
const view = ref(user.value ? 'home' : 'login')
const loading = ref(false)
const sessionRestoring = ref(Boolean(user.value?.id && pendingActiveSession.value?.id))
const recordsLoading = ref(false)
const dashboardLoading = ref(false)
const trainingModel = ref(false)
const predictingSessionId = ref(null)
const deletingRecordId = ref(null)
const editingRecordId = ref(null)
const activeScaleHelp = ref('')
const errorMessage = ref('')
const noticeMessage = ref('')
const noticeTone = ref('info')
const records = ref([])
const total = ref(0)
const analyticsOverview = ref(null)
const analyticsTrend = ref([])
const analyticsFactors = ref(null)
const now = ref(Date.now())
const appBackStack = ref([])
const pageVisible = ref(typeof document === 'undefined' ? true : !document.hidden)
const backgroundPauseCount = ref(0)
const backgroundPauseSeconds = ref(0)
const backgroundWarning = ref('')
const wakeLockStatus = ref('idle')
const editFormSnapshot = ref(null)
const predictingNext = ref(false)
const predictNextResult = ref(null)
const predictNextForm = reactive({
  location: '',
  task_type: '',
  duration_minutes: 60,
  goal_clarity: 3,
  light_level: 3,
  noise_level: 3,
  fatigue_level: 3,
  mood_stress: 3,
  phone_distraction: 3,
})

let timer = null
let browserHistoryReady = false
let hiddenStartedAt = null
let wakeLockSentinel = null

const {
  aggregatedFeatures: motionFeatures,
  beginSession: beginMotionSession,
  cancelSession: cancelMotionSession,
  finishSession: finishMotionSession,
  isListening: isMotionListening,
  message: motionMessage,
  requestPermission: requestMotionPermission,
  requiresPermission: motionRequiresPermission,
  sampleCount: motionSampleCount,
  status: motionStatus,
} = useMotionTracker()

const loginForm = reactive({
  nickname: '',
  grade: '',
  major: '',
})

const endForm = reactive({
  location: '',
  task_type: '',
  goal_clarity: 3,
  light_level: 3,
  noise_level: 3,
  fatigue_level: 3,
  mood_stress: 3,
  phone_distraction: 3,
  efficiency_score: 3,
})

const editForm = reactive({
  location: '',
  task_type: '',
  goal_clarity: 3,
  light_level: 3,
  noise_level: 3,
  fatigue_level: 3,
  mood_stress: 3,
  phone_distraction: 3,
  efficiency_score: 3,
})

const isLoggedIn = computed(() => Boolean(user.value?.id))
const hasActiveSession = computed(() => Boolean(activeSession.value?.id))
const currentStatus = computed(() => {
  if (sessionRestoring.value) return '校验中'
  return hasActiveSession.value ? '学习中' : '未开始'
})
const activeStartTime = computed(() => activeSession.value?.start_time || '')
const elapsedText = computed(() => formatElapsed(activeSession.value?.start_time, now.value))
const motionStatusLabel = computed(() => {
  const labels = {
    idle: '未启用',
    permission_required: '等待授权',
    listening: '采集中',
    unavailable: '不可用',
    empty: '无有效数据',
    collected: '已采集',
  }
  return labels[motionStatus.value] || '未启用'
})
const motionStatusClass = computed(() => {
  if (motionStatus.value === 'listening' || motionStatus.value === 'collected') return 'success'
  if (motionStatus.value === 'unavailable' || motionStatus.value === 'empty') return 'warning'
  return 'neutral'
})
const showBackButton = computed(() => isLoggedIn.value && view.value !== 'home' && view.value !== 'login')
const foregroundStatusLabel = computed(() => (pageVisible.value ? '前台采集中' : '后台/隐藏'))
const foregroundStatusClass = computed(() => (pageVisible.value ? 'success' : 'warning'))
const wakeLockStatusLabel = computed(() => {
  const labels = {
    idle: '未启用',
    active: '已尽量保持亮屏',
    released: '已释放',
    unsupported: '浏览器不支持',
    failed: '启用失败',
  }
  return labels[wakeLockStatus.value] || '未启用'
})
const wakeLockStatusClass = computed(() => (wakeLockStatus.value === 'active' ? 'success' : 'warning'))
const backgroundPauseText = computed(() => formatDuration(backgroundPauseSeconds.value))
const hasEndFormDraft = computed(() => {
  return Boolean(
    endForm.location ||
      endForm.task_type ||
      endForm.goal_clarity !== 3 ||
      endForm.light_level !== 3 ||
      endForm.noise_level !== 3 ||
      endForm.fatigue_level !== 3 ||
      endForm.mood_stress !== 3 ||
      endForm.phone_distraction !== 3 ||
      endForm.efficiency_score !== 3,
  )
})
const hasEditFormDraft = computed(() => {
  if (!editFormSnapshot.value) return false
  return JSON.stringify(editFormSnapshot.value) !== JSON.stringify(snapshotEditForm())
})
const dashboardReady = computed(() => Boolean(analyticsOverview.value || analyticsTrend.value.length || analyticsFactors.value))
const maxTrendDuration = computed(() => Math.max(1, ...analyticsTrend.value.map((item) => item.duration_minutes || 0)))
const maxTrendScore = computed(() => Math.max(5, ...analyticsTrend.value.map((item) => item.avg_efficiency_score || 0)))
const maxPeriodDuration = computed(() =>
  Math.max(1, ...(analyticsFactors.value?.time_periods || []).map((item) => item.duration_minutes || 0)),
)
const maxFeatureImportance = computed(() =>
  Math.max(0.0001, ...(analyticsFactors.value?.model_snapshot?.feature_importance || []).map((item) => item.importance_score || 0)),
)
const motionScatterBounds = computed(() => {
  const points = analyticsFactors.value?.motion_efficiency_points || []
  return {
    maxMove: Math.max(1, ...points.map((item) => item.move_count || 0)),
    maxScore: 5,
  }
})
const latestPrediction = computed(() => analyticsOverview.value?.latest_prediction || null)
const topActiveSuggestions = computed(() => {
  const suggestions = analyticsFactors.value?.rule_suggestions || []
  const active = suggestions.filter((item) => item.active)
  return active.length ? active : suggestions.slice(0, 2)
})

const autoTimePeriod = computed(() => {
  const hour = new Date().getHours()
  if (hour < 12) return 'morning'
  if (hour < 18) return 'afternoon'
  if (hour < 22) return 'evening'
  return 'late_night'
})

const predictNextReady = computed(() => Boolean(predictNextForm.location && predictNextForm.task_type))

onMounted(() => {
  timer = window.setInterval(() => {
    now.value = Date.now()
  }, 1000)
  initializeBrowserHistory()
  document.addEventListener('visibilitychange', handleVisibilityChange)
  window.addEventListener('popstate', handlePopState)
  window.addEventListener('beforeunload', handleBeforeUnload)

  if (pendingActiveSession.value?.id) {
    syncActiveSessionWithBackend('startup', {
      restoreView: true,
      startCollection: true,
      silentValid: true,
    })
  } else {
    sessionRestoring.value = false
  }
})

onBeforeUnmount(() => {
  window.clearInterval(timer)
  document.removeEventListener('visibilitychange', handleVisibilityChange)
  window.removeEventListener('popstate', handlePopState)
  window.removeEventListener('beforeunload', handleBeforeUnload)
  cancelMotionSession()
  releaseWakeLock()
})

function setError(error) {
  errorMessage.value = error?.message || '操作失败，请稍后重试。'
  showToast({ message: errorMessage.value, wordBreak: 'break-word' })
}

function clearError() {
  errorMessage.value = ''
}

function setNotice(message, tone = 'info') {
  noticeMessage.value = message
  noticeTone.value = tone
}

function clearNotice() {
  noticeMessage.value = ''
  noticeTone.value = 'info'
}

function formatDate(value) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function formatElapsed(startTime, currentTime) {
  if (!startTime) return '00:00:00'
  const start = new Date(startTime).getTime()
  if (Number.isNaN(start)) return '00:00:00'
  const seconds = Math.max(0, Math.floor((currentTime - start) / 1000))
  const hours = String(Math.floor(seconds / 3600)).padStart(2, '0')
  const minutes = String(Math.floor((seconds % 3600) / 60)).padStart(2, '0')
  const rest = String(seconds % 60).padStart(2, '0')
  return `${hours}:${minutes}:${rest}`
}

function formatDuration(totalSeconds) {
  const seconds = Math.max(0, Math.floor(totalSeconds || 0))
  if (seconds < 60) return `${seconds} 秒`
  const minutes = Math.floor(seconds / 60)
  const rest = seconds % 60
  return rest ? `${minutes} 分 ${rest} 秒` : `${minutes} 分钟`
}

function optionLabel(options, value) {
  return options.find((item) => item.value === value)?.label || value || '-'
}

function resetEndForm() {
  endForm.location = ''
  endForm.task_type = ''
  endForm.goal_clarity = 3
  endForm.light_level = 3
  endForm.noise_level = 3
  endForm.fatigue_level = 3
  endForm.mood_stress = 3
  endForm.phone_distraction = 3
  endForm.efficiency_score = 3
}

function resetEditForm() {
  editForm.location = ''
  editForm.task_type = ''
  editForm.goal_clarity = 3
  editForm.light_level = 3
  editForm.noise_level = 3
  editForm.fatigue_level = 3
  editForm.mood_stress = 3
  editForm.phone_distraction = 3
  editForm.efficiency_score = 3
  editFormSnapshot.value = null
}

function fillEditForm(record) {
  editForm.location = record.location || ''
  editForm.task_type = record.task_type || ''
  editForm.goal_clarity = record.goal_clarity || 3
  editForm.light_level = record.light_level || 3
  editForm.noise_level = record.noise_level || 3
  editForm.fatigue_level = record.fatigue_level || 3
  editForm.mood_stress = record.mood_stress || 3
  editForm.phone_distraction = record.phone_distraction || 3
  editForm.efficiency_score = record.efficiency_score || 3
  editFormSnapshot.value = snapshotEditForm()
}

function normalizeActiveSession(session) {
  return {
    id: session.id,
    user_id: session.user_id,
    start_time: session.start_time,
    status: 'in_progress',
  }
}

function isBackendActiveSession(session) {
  return Boolean(session?.id && !session.end_time && !session.abandoned_at && session.status === 'in_progress')
}

function sessionBelongsToCurrentUser(session) {
  if (!user.value?.id || !session?.user_id) return true
  return Number(session.user_id) === Number(user.value.id)
}

function applyActiveSessionFromBackend(session, options = {}) {
  const normalized = normalizeActiveSession(session)
  activeSession.value = normalized
  pendingActiveSession.value = null
  sessionRestoring.value = false
  saveActiveSession(normalized)
  now.value = Date.now()

  if (options.startCollection) {
    beginMotionSession()
  }
  if (options.requestWakeLock !== false) {
    requestWakeLock()
  }

  return normalized
}

function clearLocalActiveSessionState(message = '', tone = 'warning', options = {}) {
  activeSession.value = null
  pendingActiveSession.value = null
  sessionRestoring.value = false
  clearActiveSession()
  cancelMotionSession()
  releaseWakeLock()
  hiddenStartedAt = null
  backgroundPauseCount.value = 0
  backgroundPauseSeconds.value = 0
  backgroundWarning.value = ''
  resetEndForm()

  if (message) {
    setNotice(message, tone)
    showToast({ message, wordBreak: 'break-word' })
  }

  if (options.resetView) {
    const target = user.value?.id ? 'home' : 'login'
    if (view.value !== target) {
      go(target, { resetStack: true })
    } else {
      appBackStack.value = []
      replaceBrowserState()
    }
  }
}

async function syncActiveSessionWithBackend(reason, options = {}) {
  const candidate = activeSession.value || pendingActiveSession.value || loadActiveSession()
  if (!candidate?.id) {
    pendingActiveSession.value = null
    sessionRestoring.value = false
    return false
  }

  if (!user.value?.id) {
    clearLocalActiveSessionState('上次学习状态已失效，请重新开始。', 'warning', { resetView: true })
    return false
  }

  if (!sessionBelongsToCurrentUser(candidate)) {
    clearLocalActiveSessionState('上次学习状态已失效，请重新开始。', 'warning', { resetView: true })
    return false
  }

  try {
    const detail = await getSession(candidate.id)
    if (!sessionBelongsToCurrentUser(detail)) {
      clearLocalActiveSessionState('上次学习状态已失效，请重新开始。', 'warning', { resetView: true })
      return false
    }

    if (isBackendActiveSession(detail)) {
      applyActiveSessionFromBackend(detail, {
        startCollection: Boolean(options.startCollection),
        requestWakeLock: options.requestWakeLock,
      })

      if (options.restoreView) {
        appBackStack.value = ['home']
        setView('study')
        replaceBrowserState()
        pushBrowserState()
      }

      if (!options.silentValid && reason === 'startup') {
        setNotice('已恢复未结束学习，以服务器开始时间继续计时。', 'info')
      }
      return true
    }

    if (detail?.status === 'abandoned' || detail?.abandoned_at) {
      clearLocalActiveSessionState('上次学习已放弃，请重新开始。', 'info', {
        resetView: options.resetView !== false,
      })
      await refreshRecords()
      return false
    }

    clearLocalActiveSessionState('上次学习已完成，已刷新历史记录。', 'info', {
      resetView: options.resetView !== false,
    })
    await refreshRecords()
    return false
  } catch (error) {
    if (error?.status === 404) {
      clearLocalActiveSessionState('上次学习状态已失效，请重新开始。', 'warning', { resetView: true })
      return false
    }

    pendingActiveSession.value = null
    sessionRestoring.value = false
    if (options.showNetworkWarning !== false) {
      setNotice('暂时无法校验上次学习状态，请检查网络后重试。', 'warning')
    }
    return false
  }
}

async function recoverOpenSessionFromList() {
  if (!user.value?.id) return false

  const result = await listSessions({ userId: user.value.id, limit: 100 })
  const openSession = (result.items || []).find((record) => record.status === 'in_progress' && !record.end_time)
  if (!openSession?.id) return false

  const detail = await getSession(openSession.id)
  if (!isBackendActiveSession(detail) || !sessionBelongsToCurrentUser(detail)) return false

  applyActiveSessionFromBackend(detail, { startCollection: true })
  return true
}

function snapshotEditForm() {
  return {
    location: editForm.location,
    task_type: editForm.task_type,
    goal_clarity: editForm.goal_clarity,
    light_level: editForm.light_level,
    noise_level: editForm.noise_level,
    fatigue_level: editForm.fatigue_level,
    mood_stress: editForm.mood_stress,
    phone_distraction: editForm.phone_distraction,
    efficiency_score: editForm.efficiency_score,
  }
}

function setView(nextView) {
  clearError()
  activeScaleHelp.value = ''
  view.value = nextView
  if (nextView === 'history') {
    refreshRecords()
  }
  if (nextView === 'dashboard') {
    refreshDashboard()
  }
  window.requestAnimationFrame(() => {
    window.scrollTo({ top: 0, behavior: 'smooth' })
  })
}

function go(nextView, options = {}) {
  if ((nextView === 'study' || nextView === 'end') && !hasActiveSession.value) {
    setError(new Error('当前没有进行中的学习会话，请重新开始。'))
    return
  }

  const previousView = view.value
  if (!options.resetStack && !options.skipStack && previousView !== nextView) {
    appBackStack.value.push(previousView)
  }

  if (options.resetStack) {
    appBackStack.value = options.backStack ? [...options.backStack] : []
  }

  setView(nextView)

  if (options.replace) {
    replaceBrowserState()
  } else if (options.resetStack) {
    replaceBrowserState()
  } else {
    pushBrowserState()
  }
}

function initializeBrowserHistory() {
  if (!window.history?.replaceState) return
  browserHistoryReady = true
  window.history.replaceState(buildBrowserState(), '', window.location.href)
  if (hasActiveSession.value) {
    window.history.pushState(buildBrowserState(), '', window.location.href)
  }
}

function buildBrowserState() {
  return {
    studyEfficiencyApp: true,
    view: view.value,
    stackDepth: appBackStack.value.length,
  }
}

function pushBrowserState() {
  if (!browserHistoryReady || !window.history?.pushState) return
  window.history.pushState(buildBrowserState(), '', window.location.href)
}

function replaceBrowserState() {
  if (!browserHistoryReady || !window.history?.replaceState) return
  window.history.replaceState(buildBrowserState(), '', window.location.href)
}

function getBackTarget(currentView = view.value) {
  if (currentView === 'history') return 'home'
  if (currentView === 'dashboard') return 'home'
  if (currentView === 'study') return 'home'
  if (currentView === 'end') return 'study'
  if (currentView === 'edit') return 'history'
  return user.value ? 'home' : 'login'
}

function lastBackStackView() {
  return appBackStack.value[appBackStack.value.length - 1]
}

async function confirmLeaveCurrentView(currentView = view.value) {
  if (currentView === 'end' && hasEndFormDraft.value) {
    try {
      await showConfirmDialog({
        title: '返回学习中',
        message: '当前结束表单还没有提交，返回后表单内容可能不会保存。确定返回吗？',
        confirmButtonText: '返回',
        cancelButtonText: '继续填写',
      })
    } catch {
      return false
    }
  }

  if (currentView === 'edit' && hasEditFormDraft.value) {
    try {
      await showConfirmDialog({
        title: '放弃修改',
        message: '当前修改还没有保存，返回后本次修改不会写入数据库。确定返回吗？',
        confirmButtonText: '返回',
        cancelButtonText: '继续修改',
      })
    } catch {
      return false
    }
  }

  return true
}

async function handleAppBack() {
  const currentView = view.value
  const target = getBackTarget()
  const canLeave = await confirmLeaveCurrentView()
  if (!canLeave) return

  if ((target === 'study' || target === 'end') && !(await syncActiveSessionWithBackend('navigation', { silentValid: true }))) {
    return
  }

  if (lastBackStackView() === target) {
    appBackStack.value.pop()
  }

  cleanupAfterLeaving(currentView, target)
  setView(target)
  replaceBrowserState()
}

async function handlePopState() {
  const currentView = view.value
  const target = lastBackStackView()
  if (target) {
    const canLeave = await confirmLeaveCurrentView()
    if (!canLeave) {
      pushBrowserState()
      return
    }
    if (
      (target === 'study' || target === 'end') &&
      !(await syncActiveSessionWithBackend('navigation', { silentValid: true }))
    ) {
      return
    }
    appBackStack.value.pop()
    cleanupAfterLeaving(currentView, target)
    setView(target)
    replaceBrowserState()
    return
  }

  if (hasActiveSession.value || view.value === 'end') {
    pushBrowserState()
    showToast({ message: '学习仍在进行，请先结束学习并提交记录后再退出。', wordBreak: 'break-word' })
  }
}

function cleanupAfterLeaving(currentView, targetView) {
  if (currentView === 'edit' && targetView !== 'edit') {
    resetEditForm()
    editingRecordId.value = null
  }
}

function handleBeforeUnload(event) {
  if (!hasActiveSession.value && !(view.value === 'end' && hasEndFormDraft.value)) return
  event.preventDefault()
  event.returnValue = ''
  return ''
}

async function requestWakeLock() {
  if (!hasActiveSession.value) return
  if (!('wakeLock' in navigator)) {
    wakeLockStatus.value = 'unsupported'
    return
  }

  try {
    wakeLockSentinel = await navigator.wakeLock.request('screen')
    wakeLockStatus.value = 'active'
    wakeLockSentinel.addEventListener('release', () => {
      wakeLockStatus.value = wakeLockSentinel ? 'released' : 'idle'
    })
  } catch {
    wakeLockStatus.value = 'failed'
  }
}

async function releaseWakeLock() {
  if (!wakeLockSentinel) {
    wakeLockStatus.value = 'idle'
    return
  }

  const sentinel = wakeLockSentinel
  wakeLockSentinel = null
  try {
    await sentinel.release()
  } catch {
    // Wake Lock may already be released by the browser.
  }
  wakeLockStatus.value = 'idle'
}

async function handleVisibilityChange() {
  pageVisible.value = !document.hidden
  if (!hasActiveSession.value) return

  if (document.hidden) {
    hiddenStartedAt = Date.now()
    backgroundWarning.value = '页面已进入后台或锁屏，手机运动传感器可能暂停。'
    return
  }

  const stillValid = await syncActiveSessionWithBackend('foreground', {
    silentValid: true,
    showNetworkWarning: false,
  })
  if (!stillValid) return

  if (hiddenStartedAt) {
    const pauseSeconds = Math.max(1, Math.round((Date.now() - hiddenStartedAt) / 1000))
    backgroundPauseCount.value += 1
    backgroundPauseSeconds.value += pauseSeconds
    hiddenStartedAt = null
    backgroundWarning.value = '后台期间手机传感器可能暂停，本次学习记录仍会保存。'
    showToast({ message: backgroundWarning.value, wordBreak: 'break-word' })
  }

  requestWakeLock()
}

function scaleHelpId(formName, fieldKey) {
  return `${formName}:${fieldKey}`
}

function toggleScaleHelp(helpId) {
  activeScaleHelp.value = activeScaleHelp.value === helpId ? '' : helpId
}

async function handleLogin() {
  clearError()
  const nickname = loginForm.nickname.trim()
  if (!nickname) {
    setError(new Error('请填写昵称。'))
    return
  }

  loading.value = true
  try {
    const result = await simpleLogin({
      nickname,
      grade: loginForm.grade.trim() || null,
      major: loginForm.major.trim() || null,
    })
    user.value = result
    saveUser(result)
    showToast('登录成功')
    const localSession = activeSession.value || pendingActiveSession.value || loadActiveSession()
    if (localSession?.id) {
      const restored = await syncActiveSessionWithBackend('login', {
        restoreView: true,
        startCollection: true,
        silentValid: true,
      })
      if (!restored) {
        go('home', { resetStack: true })
      }
    } else {
      go('home', { resetStack: true })
    }
  } catch (error) {
    setError(error)
  } finally {
    loading.value = false
  }
}

function handleLogout() {
  if (hasActiveSession.value) {
    setError(new Error('已有未结束的学习会话，请结束学习后再退出。'))
    return
  }
  cancelMotionSession()
  user.value = null
  activeSession.value = null
  clearUser()
  clearActiveSession()
  records.value = []
  total.value = 0
  analyticsOverview.value = null
  analyticsTrend.value = []
  analyticsFactors.value = null
  releaseWakeLock()
  go('login', { resetStack: true })
}

async function handleStart() {
  if (!user.value?.id) {
    setError(new Error('请先输入昵称进入系统。'))
    go('login')
    return
  }

  clearError()
  clearNotice()
  loading.value = true
  try {
    const session = await startSession({ user_id: user.value.id })
    activeSession.value = normalizeActiveSession(session)
    saveActiveSession(activeSession.value)
    beginMotionSession()
    requestWakeLock()
    showToast('已开始学习')
    go('study')
  } catch (error) {
    if (error?.status === 409) {
      try {
        const recovered = await recoverOpenSessionFromList()
        if (recovered) {
          const message = '检测到已有未结束学习，已恢复。'
          setNotice(message, 'info')
          showToast({ message, wordBreak: 'break-word' })
          go('study', { resetStack: true, backStack: ['home'] })
          return
        }
      } catch {
        // Fall through to the original 409 message.
      }
    }
    setError(error)
  } finally {
    loading.value = false
  }
}

async function handleMotionPermission() {
  await requestMotionPermission()
  await requestWakeLock()
}

async function openEndForm() {
  const stillValid = await syncActiveSessionWithBackend('before-end-form', { silentValid: true })
  if (!stillValid) return
  resetEndForm()
  go('end')
}

function validateEndForm() {
  if (!activeSession.value?.id) return '当前没有进行中的学习会话。'
  if (!endForm.location) return '请选择学习地点。'
  if (!endForm.task_type) return '请选择任务类型。'
  return ''
}

function validateEditForm() {
  if (!editingRecordId.value) return '请选择要修改的历史记录。'
  if (!editForm.location) return '请选择学习地点。'
  if (!editForm.task_type) return '请选择任务类型。'
  return ''
}

function recordStatusText(record) {
  if (record.efficiency_label) return labelMap[record.efficiency_label]
  return statusMap[record.status] || '进行中'
}

function recordStatusClass(record) {
  return record.efficiency_label || record.status || 'pending'
}

function labelText(label) {
  return labelMap[label] || label || '-'
}

function timePeriodText(period) {
  return timePeriodMap[period] || period || '-'
}

function featureText(featureName) {
  if (!featureName) return '-'
  const normalized = String(featureName).split('_').slice(0, 2).join('_')
  return featureNameMap[featureName] || featureNameMap[normalized] || featureName
}

function formatPercent(value) {
  return `${Math.round((Number(value) || 0) * 100)}%`
}

function barPercent(value, maxValue) {
  return `${Math.max(4, Math.round(((Number(value) || 0) / Math.max(1, Number(maxValue) || 1)) * 100))}%`
}

function scatterStyle(point) {
  const bounds = motionScatterBounds.value
  const x = ((Number(point.move_count) || 0) / bounds.maxMove) * 92 + 4
  const y = 96 - ((Number(point.efficiency_score) || 0) / bounds.maxScore) * 88
  return {
    left: `${Math.max(4, Math.min(96, x))}%`,
    top: `${Math.max(8, Math.min(94, y))}%`,
  }
}

async function refreshDashboard() {
  if (!user.value?.id) return
  clearError()
  dashboardLoading.value = true
  try {
    const [overview, trend, factors, history] = await Promise.all([
      getAnalyticsOverview(user.value.id),
      getAnalyticsTrend(user.value.id),
      getAnalyticsFactorAnalysis(user.value.id),
      listSessions({ userId: user.value.id }),
    ])
    analyticsOverview.value = overview
    analyticsTrend.value = trend.items || []
    analyticsFactors.value = factors
    records.value = history.items || []
    total.value = history.total || 0
  } catch (error) {
    setError(error)
  } finally {
    dashboardLoading.value = false
  }
}

async function handleTrainDemoModel() {
  clearError()
  trainingModel.value = true
  try {
    const result = await trainModel({ data_source: 'mock' })
    const sourceText = result.data_source === 'real' ? '真实数据' : 'mock/demo 数据'
    const message = `模型训练完成：${sourceText} ${result.sample_count} 条样本。`
    setNotice(message, result.valid_for_research_conclusion ? 'success' : 'warning')
    showToast({ message, wordBreak: 'break-word' })
    await refreshDashboard()
  } catch (error) {
    setError(error)
  } finally {
    trainingModel.value = false
  }
}

async function handlePredictLatest() {
  if (!records.value.length) {
    await refreshRecords()
  }
  const completed = records.value.find((record) => record.status === 'completed' && record.efficiency_score)
  if (!completed?.id) {
    setError(new Error('暂无可预测的已完成学习记录。'))
    return
  }
  predictingSessionId.value = completed.id
  try {
    await predictSession({ session_id: completed.id })
    showToast('预测结果已生成')
    await refreshRecords()
    await refreshDashboard()
  } catch (error) {
    setError(error)
  } finally {
    predictingSessionId.value = null
  }
}

function resetPredictNextForm() {
  predictNextForm.location = ''
  predictNextForm.task_type = ''
  predictNextForm.duration_minutes = 60
  predictNextForm.goal_clarity = 3
  predictNextForm.light_level = 3
  predictNextForm.noise_level = 3
  predictNextForm.fatigue_level = 3
  predictNextForm.mood_stress = 3
  predictNextForm.phone_distraction = 3
  predictNextResult.value = null
}

async function handlePredictNext() {
  if (!predictNextForm.location || !predictNextForm.task_type) {
    setError(new Error('请先选择学习地点和任务类型。'))
    return
  }
  clearError()
  predictingNext.value = true
  try {
    const result = await predictNext({
      location: predictNextForm.location,
      task_type: predictNextForm.task_type,
      duration_minutes: predictNextForm.duration_minutes,
      time_period: autoTimePeriod.value,
      goal_clarity: predictNextForm.goal_clarity,
      light_level: predictNextForm.light_level,
      noise_level: predictNextForm.noise_level,
      fatigue_level: predictNextForm.fatigue_level,
      mood_stress: predictNextForm.mood_stress,
      phone_distraction: predictNextForm.phone_distraction,
    })
    predictNextResult.value = result
  } catch (error) {
    setError(error)
  } finally {
    predictingNext.value = false
  }
}

async function handleStartWithPrediction() {
  if (!predictNextForm.location || !predictNextForm.task_type) {
    setError(new Error('请先选择学习地点和任务类型。'))
    return
  }
  if (!user.value?.id) {
    setError(new Error('请先输入昵称进入系统。'))
    go('login')
    return
  }
  clearError()
  clearNotice()
  loading.value = true
  try {
    const session = await startSession({ user_id: user.value.id })
    activeSession.value = normalizeActiveSession(session)
    saveActiveSession(activeSession.value)
    beginMotionSession()
    requestWakeLock()

    endForm.location = predictNextForm.location
    endForm.task_type = predictNextForm.task_type
    endForm.goal_clarity = predictNextForm.goal_clarity
    endForm.light_level = predictNextForm.light_level
    endForm.noise_level = predictNextForm.noise_level
    endForm.fatigue_level = predictNextForm.fatigue_level
    endForm.mood_stress = predictNextForm.mood_stress
    endForm.phone_distraction = predictNextForm.phone_distraction
    endForm.efficiency_score = 3

    showToast('已开始学习，环境参数已预填。')
    go('study')
  } catch (error) {
    if (error?.status === 409) {
      try {
        const recovered = await recoverOpenSessionFromList()
        if (recovered) {
          const message = '检测到已有未结束学习，已恢复。'
          setNotice(message, 'info')
          showToast({ message, wordBreak: 'break-word' })
          go('study', { resetStack: true, backStack: ['home'] })
          return
        }
      } catch {
        // Fall through to the original 409 message.
      }
    }
    setError(error)
  } finally {
    loading.value = false
  }
}

async function tryPredictCompletedSession(sessionId) {
  try {
    await predictSession({ session_id: sessionId })
    return true
  } catch {
    return false
  }
}

async function handleEndSubmit() {
  clearError()
  const validationError = validateEndForm()
  if (validationError) {
    setError(new Error(validationError))
    return
  }

  loading.value = true
  try {
    const stillValid = await syncActiveSessionWithBackend('before-end', { silentValid: true })
    if (!stillValid) return

    const sessionId = activeSession.value.id
    await endSession({
      session_id: sessionId,
      location: endForm.location,
      task_type: endForm.task_type,
      goal_clarity: endForm.goal_clarity,
      light_level: endForm.light_level,
      noise_level: endForm.noise_level,
      fatigue_level: endForm.fatigue_level,
      mood_stress: endForm.mood_stress,
      phone_distraction: endForm.phone_distraction,
      efficiency_score: endForm.efficiency_score,
    })

    const features = finishMotionSession()
    let completedNotice = '学习记录已保存，本次无运动特征。'
    let completedTone = 'info'
    if (features) {
      try {
        await uploadMotion({ session_id: sessionId, ...features })
        completedNotice = '学习记录已保存，运动特征已上传。'
        completedTone = 'success'
      } catch {
        completedNotice = '学习记录已保存，但运动特征上传失败。'
        completedTone = 'warning'
      }
    }

    const predicted = await tryPredictCompletedSession(sessionId)
    if (predicted) {
      completedNotice += ' 预测结果已生成。'
    }

    activeSession.value = null
    clearActiveSession()
    releaseWakeLock()
    hiddenStartedAt = null
    setNotice(completedNotice, completedTone)
    showToast({ message: completedNotice, wordBreak: 'break-word' })
    await refreshRecords()
    go('history', { resetStack: true, backStack: ['home'] })
  } catch (error) {
    if (error?.status === 404) {
      clearLocalActiveSessionState('上次学习状态已失效，请重新开始。', 'warning', { resetView: true })
      return
    }
    setError(error)
  } finally {
    loading.value = false
  }
}

async function continueActiveStudy() {
  const stillValid = await syncActiveSessionWithBackend('continue', { silentValid: true })
  if (!stillValid) return
  go('study')
}

async function handleAbandonStudy() {
  const stillValid = await syncActiveSessionWithBackend('before-abandon', { silentValid: true })
  if (!stillValid) return
  const sessionId = activeSession.value?.id
  if (!sessionId) {
    clearLocalActiveSessionState('本地状态已清理，请重新开始。', 'warning', { resetView: true })
    return
  }

  try {
    await showConfirmDialog({
      title: '放弃本次学习',
      message: '放弃后，本次学习不会进入有效学习记录，也不会参与模型训练。确定放弃吗？',
      confirmButtonText: '放弃',
      confirmButtonColor: '#c63d4b',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }

  loading.value = true
  try {
    await abandonSession(sessionId, { reason: 'user_requested' })
    clearLocalActiveSessionState('本次学习已放弃，不会进入有效学习记录。', 'info', { resetView: true })
    await refreshRecords()
  } catch (error) {
    if (error?.status === 404) {
      clearLocalActiveSessionState('本地状态已清理，请重新开始。', 'warning', { resetView: true })
      return
    }
    if (error?.status === 409) {
      await syncActiveSessionWithBackend('abandon-conflict', { silentValid: true })
      return
    }
    setError(error)
  } finally {
    loading.value = false
  }
}

async function handleRepairLocalState() {
  try {
    await showConfirmDialog({
      title: '修复本地异常状态',
      message: '仅在页面状态异常时使用。此操作只清除本机缓存，不修改服务器数据；正常退出请使用“放弃本次学习”。',
      confirmButtonText: '清除本地缓存',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }

  clearLocalActiveSessionState('本地状态已清理，请重新开始。', 'info', { resetView: true })
}

async function refreshRecords() {
  if (!user.value?.id) return
  clearError()
  recordsLoading.value = true
  try {
    const result = await listSessions({ userId: user.value.id })
    records.value = result.items || []
    total.value = result.total || 0
  } catch (error) {
    setError(error)
  } finally {
    recordsLoading.value = false
  }
}

function openEditRecord(record) {
  if (record.status !== 'completed') {
    setError(new Error('进行中的学习会话不能在历史记录里修改。'))
    return
  }
  clearError()
  clearNotice()
  editingRecordId.value = record.id
  fillEditForm(record)
  go('edit')
}

async function handleEditSubmit() {
  clearError()
  const validationError = validateEditForm()
  if (validationError) {
    setError(new Error(validationError))
    return
  }

  loading.value = true
  try {
    await updateSession(editingRecordId.value, {
      location: editForm.location,
      task_type: editForm.task_type,
      goal_clarity: editForm.goal_clarity,
      light_level: editForm.light_level,
      noise_level: editForm.noise_level,
      fatigue_level: editForm.fatigue_level,
      mood_stress: editForm.mood_stress,
      phone_distraction: editForm.phone_distraction,
      efficiency_score: editForm.efficiency_score,
    })
    resetEditForm()
    editingRecordId.value = null
    setNotice('学习记录已更新。', 'success')
    showToast('学习记录已更新')
    await refreshRecords()
    go('history')
  } catch (error) {
    setError(error)
  } finally {
    loading.value = false
  }
}

function cancelEditRecord() {
  resetEditForm()
  editingRecordId.value = null
  go('history', { replace: true, skipStack: true })
}

async function handleDeleteRecord(record) {
  if (activeSession.value?.id === record.id) {
    setError(new Error('当前学习会话正在进行，不能从历史记录中删除。'))
    return
  }

  clearError()
  try {
    await showConfirmDialog({
      title: '删除记录',
      message: '这条记录会从历史列表移除，并备份到已删除记录表。',
      confirmButtonText: '删除',
      confirmButtonColor: '#c63d4b',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }

  deletingRecordId.value = record.id
  try {
    await deleteSession(record.id)
    showToast('记录已删除并备份')
    await refreshRecords()
  } catch (error) {
    setError(error)
  } finally {
    deletingRecordId.value = null
  }
}
</script>

<template>
  <van-config-provider theme="light">
    <main class="app-shell">
      <van-nav-bar title="学习效率记录" fixed placeholder safe-area-inset-top>
        <template #left>
          <button v-if="showBackButton" class="nav-link app-back-button" type="button" @click="handleAppBack">
            <span aria-hidden="true">‹</span>
            返回
          </button>
        </template>
        <template #right>
          <button v-if="isLoggedIn" class="nav-link" type="button" @click="handleLogout">退出</button>
        </template>
      </van-nav-bar>

      <section v-if="errorMessage" class="status-banner error" role="alert">
        {{ errorMessage }}
      </section>
      <section v-if="noticeMessage" :class="['status-banner', noticeTone]" role="status">
        {{ noticeMessage }}
      </section>

      <section v-if="view === 'login'" class="screen login-screen">
        <div class="page-title">
          <p class="eyebrow">Mobile Study Log</p>
          <h1>学习效率记录</h1>
          <p>输入昵称即可进入 MVP，不使用密码或复杂认证。</p>
        </div>

        <van-form @submit="handleLogin">
          <van-cell-group inset>
            <van-field
              v-model="loginForm.nickname"
              name="nickname"
              label="昵称"
              placeholder="例如 student_a"
              :rules="[{ required: true, message: '请填写昵称' }]"
              clearable
            />
            <van-field v-model="loginForm.grade" label="年级" placeholder="可选，例如 2024" clearable />
            <van-field v-model="loginForm.major" label="专业" placeholder="可选，例如 物联网工程" clearable />
          </van-cell-group>

          <div class="action-block">
            <van-button round block type="primary" native-type="submit" :loading="loading">进入系统</van-button>
          </div>
        </van-form>
      </section>

      <section v-else-if="view === 'home'" class="screen">
        <div class="summary-band">
          <p class="eyebrow">当前用户</p>
          <h1>{{ user?.nickname }}</h1>
          <div class="status-row">
            <span>当前状态</span>
            <strong :class="hasActiveSession ? 'accent' : ''">{{ currentStatus }}</strong>
          </div>
        </div>

        <div class="home-actions">
          <van-button v-if="sessionRestoring" round block type="primary" loading disabled>
            正在校验学习状态
          </van-button>
          <template v-else-if="!hasActiveSession">
            <van-button round block type="primary" :loading="loading" @click="handleStart">
              开始学习
            </van-button>
          </template>
          <van-button v-else round block type="primary" @click="continueActiveStudy">继续当前学习</van-button>
          <van-button round block plain type="primary" @click="go('history')">查看历史记录</van-button>
          <van-button round block plain type="primary" @click="go('dashboard')">分析看板</van-button>
        </div>

        <section class="guide-panel" aria-labelledby="guide-title">
          <div class="guide-header">
            <p class="eyebrow">采集前请看</p>
            <h2 id="guide-title">使用指南与数据说明</h2>
          </div>
          <ul class="guide-list">
            <li>使用你自己选择的昵称登录即可，不要填写真实姓名、手机号或学号。</li>
            <li>多次参与请尽量始终使用同一个昵称，方便按用户归档学习记录。</li>
            <li>点击开始学习后尽量保持网页在前台，不要锁屏或划掉浏览器进程。</li>
            <li>运动检测不可用时仍可正常提交学习记录，不会影响自报告保存。</li>
            <li>学习结束后请如实填写地点、任务类型、疲劳、手机干扰和效率评分。</li>
            <li>数据仅用于本课程项目的学习效率分析，按昵称保存，不公开个人身份信息。</li>
          </ul>
        </section>
      </section>

      <section v-else-if="view === 'study'" class="screen study-screen">
        <div class="timer-panel">
          <p class="eyebrow">学习中</p>
          <div class="timer-text">{{ elapsedText }}</div>
          <p class="muted">开始时间：{{ formatDate(activeStartTime) }}</p>
        </div>

        <section class="motion-panel" aria-live="polite">
          <div class="motion-header">
            <div>
              <p class="eyebrow">运动检测状态</p>
              <strong>{{ motionStatusLabel }}</strong>
            </div>
            <span :class="['motion-indicator', motionStatusClass]"></span>
          </div>
          <p class="muted">{{ motionMessage }}</p>
          <p class="motion-note">
            建议保持本页面在前台打开，不要锁屏或划掉浏览器进程；纯网页无法保证后台仍持续采集传感器。
          </p>
          <van-button
            v-if="motionRequiresPermission"
            class="motion-enable"
            size="small"
            type="primary"
            @click="handleMotionPermission"
          >
            启用运动检测
          </van-button>
          <dl class="motion-metrics">
            <div>
              <dt>有效样本</dt>
              <dd>{{ motionSampleCount }}</dd>
            </div>
            <div>
              <dt>页面状态</dt>
              <dd :class="foregroundStatusClass">{{ foregroundStatusLabel }}</dd>
            </div>
            <div>
              <dt>亮屏辅助</dt>
              <dd :class="wakeLockStatusClass">{{ wakeLockStatusLabel }}</dd>
            </div>
            <div>
              <dt>后台暂停</dt>
              <dd>{{ backgroundPauseCount }} 次 / {{ backgroundPauseText }}</dd>
            </div>
          </dl>
          <section v-if="backgroundWarning" class="collection-warning" role="status">
            {{ backgroundWarning }}
          </section>
          <dl v-if="motionFeatures" class="motion-metrics motion-feature-metrics">
            <div>
              <dt>移动次数</dt>
              <dd>{{ motionFeatures.move_count }}</dd>
            </div>
            <div>
              <dt>晃动次数</dt>
              <dd>{{ motionFeatures.shake_count }}</dd>
            </div>
            <div>
              <dt>静止占比</dt>
              <dd>{{ Math.round(motionFeatures.still_ratio * 100) }}%</dd>
            </div>
          </dl>
        </section>

        <div class="home-actions">
          <van-button round block type="danger" @click="openEndForm">结束学习并填写表单</van-button>
          <van-button round block plain type="primary" @click="go('history')">查看历史记录</van-button>
          <van-button round block plain type="danger" :loading="loading" @click="handleAbandonStudy">
            放弃本次学习
          </van-button>
          <button class="local-repair-link" type="button" @click="handleRepairLocalState">
            修复本地异常状态/清除本地缓存
          </button>
        </div>
      </section>

      <section v-else-if="view === 'end'" class="screen form-screen">
        <div class="section-title">
          <h2>结束学习表单</h2>
          <p>请按本次学习真实情况填写，提交后会保存为历史记录。</p>
        </div>

        <section :class="['status-banner', isMotionListening ? 'info' : 'warning']">
          {{ motionMessage }}
        </section>

        <van-form @submit="handleEndSubmit">
          <van-cell-group inset>
            <label class="select-field">
              <span>学习地点</span>
              <select v-model="endForm.location" required>
                <option value="" disabled>请选择</option>
                <option v-for="item in locationOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
              </select>
            </label>
            <label class="select-field">
              <span>任务类型</span>
              <select v-model="endForm.task_type" required>
                <option value="" disabled>请选择</option>
                <option v-for="item in taskTypeOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
              </select>
            </label>
          </van-cell-group>

          <div class="scale-list">
            <div
              v-for="field in scaleFields"
              :key="field.key"
              :class="[
                'scale-item',
                field.key === 'efficiency_score' ? 'strong' : '',
                activeScaleHelp === scaleHelpId('end', field.key) ? 'help-open' : '',
              ]"
            >
              <div class="scale-label-wrap">
                <button
                  class="scale-help-trigger"
                  type="button"
                  :aria-label="`${field.label}评分说明`"
                  :aria-expanded="activeScaleHelp === scaleHelpId('end', field.key)"
                  @click="toggleScaleHelp(scaleHelpId('end', field.key))"
                >
                  ?
                </button>
                <span>{{ field.label }}</span>
                <transition name="help-pop">
                  <div v-if="activeScaleHelp === scaleHelpId('end', field.key)" class="scale-help-popover" role="tooltip">
                    <strong>{{ field.label }}评分说明</strong>
                    <ul>
                      <li v-for="item in field.descriptions" :key="item">{{ item }}</li>
                    </ul>
                  </div>
                </transition>
              </div>
              <van-stepper v-model="endForm[field.key]" min="1" max="5" integer />
            </div>
          </div>

          <div class="action-block sticky-actions">
            <van-button round block type="primary" native-type="submit" :loading="loading">提交学习记录</van-button>
            <van-button round block plain type="default" @click="handleAppBack">返回学习中</van-button>
          </div>
        </van-form>
      </section>

      <section v-else-if="view === 'history'" class="screen history-screen">
        <div class="section-title with-action">
          <div>
            <h2>历史记录</h2>
            <p>共 {{ total }} 条记录，按开始时间倒序展示。</p>
          </div>
          <van-button size="small" plain type="primary" :loading="recordsLoading" @click="refreshRecords">刷新</van-button>
        </div>

        <van-loading v-if="recordsLoading" class="center-loading" />
        <van-empty v-else-if="records.length === 0" description="暂无学习记录，先开始一次学习。" />
        <div v-else class="record-list">
          <article v-for="record in records" :key="record.id" class="record-item">
            <div class="record-main">
              <strong>{{ formatDate(record.start_time) }}</strong>
              <div class="record-actions">
                <span :class="['label-pill', recordStatusClass(record)]">
                  {{ recordStatusText(record) }}
                </span>
                <van-button
                  class="record-action-button"
                  icon="edit"
                  plain
                  type="primary"
                  size="small"
                  title="修改记录"
                  aria-label="修改记录"
                  @click="openEditRecord(record)"
                >
                  编辑
                </van-button>
                <van-button
                  class="record-action-button"
                  icon="delete-o"
                  plain
                  type="danger"
                  size="small"
                  title="删除记录"
                  aria-label="删除记录"
                  :loading="deletingRecordId === record.id"
                  @click="handleDeleteRecord(record)"
                />
              </div>
            </div>
            <dl>
              <div>
                <dt>时长</dt>
                <dd>{{ record.duration_minutes ? `${record.duration_minutes} 分钟` : '-' }}</dd>
              </div>
              <div>
                <dt>任务</dt>
                <dd>{{ optionLabel(taskTypeOptions, record.task_type) }}</dd>
              </div>
              <div>
                <dt>评分</dt>
                <dd>{{ record.efficiency_score || '-' }}</dd>
              </div>
            </dl>
          </article>
        </div>
      </section>

      <section v-else-if="view === 'dashboard'" class="screen dashboard-screen">
        <div class="section-title with-action">
          <div>
            <h2>分析看板</h2>
            <p>仅统计已完成且未放弃的学习记录；mock/demo 模型结果只用于流程演示。</p>
          </div>
          <van-button size="small" plain type="primary" :loading="dashboardLoading" @click="refreshDashboard">刷新</van-button>
        </div>

        <van-loading v-if="dashboardLoading && !dashboardReady" class="center-loading" />
        <van-empty v-else-if="!dashboardReady || analyticsOverview?.total_sessions === 0" description="暂无可分析的已完成记录。" />
        <div v-else class="dashboard-stack">
          <section class="stats-grid" aria-label="总览统计">
            <article class="stat-tile">
              <span>总学习次数</span>
              <strong>{{ analyticsOverview.total_sessions }}</strong>
            </article>
            <article class="stat-tile">
              <span>总学习时长</span>
              <strong>{{ analyticsOverview.total_duration_minutes }}</strong>
              <small>分钟</small>
            </article>
            <article class="stat-tile">
              <span>平均效率评分</span>
              <strong>{{ analyticsOverview.avg_efficiency_score || '-' }}</strong>
            </article>
            <article class="stat-tile">
              <span>高效学习占比</span>
              <strong>{{ formatPercent(analyticsOverview.high_efficiency_ratio) }}</strong>
            </article>
          </section>

          <section class="dashboard-panel">
            <div class="panel-heading">
              <div>
                <h3>预测下一次学习效率</h3>
                <p>填写计划的学习环境，模型将根据历史数据预测预期效率。</p>
              </div>
            </div>

            <van-form @submit="handlePredictNext">
              <van-cell-group inset style="margin-bottom: 12px;">
                <label class="select-field">
                  <span>学习地点</span>
                  <select v-model="predictNextForm.location" required>
                    <option value="" disabled>请选择</option>
                    <option v-for="item in locationOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
                  </select>
                </label>
                <label class="select-field">
                  <span>任务类型</span>
                  <select v-model="predictNextForm.task_type" required>
                    <option value="" disabled>请选择</option>
                    <option v-for="item in taskTypeOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
                  </select>
                </label>
                <van-field
                  v-model.number="predictNextForm.duration_minutes"
                  label="目标时长"
                  type="digit"
                  placeholder="分钟"
                  :rules="[{ required: true, message: '请输入目标时长' }]"
                />
              </van-cell-group>

              <div class="status-banner info" style="margin: 0 16px 12px; font-size: 13px;">
                时段自动识别为「{{ timePeriodMap[autoTimePeriod] }}」
              </div>

              <div class="scale-list">
                <div
                  v-for="field in scaleFields.filter(f => f.key !== 'efficiency_score')"
                  :key="field.key"
                  :class="['scale-item', activeScaleHelp === scaleHelpId('predictNext', field.key) ? 'help-open' : '']"
                >
                  <div class="scale-label-wrap">
                    <button
                      class="scale-help-trigger"
                      type="button"
                      :aria-label="`${field.label}评分说明`"
                      :aria-expanded="activeScaleHelp === scaleHelpId('predictNext', field.key)"
                      @click="toggleScaleHelp(scaleHelpId('predictNext', field.key))"
                    >
                      ?
                    </button>
                    <span>{{ field.label }}</span>
                    <transition name="help-pop">
                      <div v-if="activeScaleHelp === scaleHelpId('predictNext', field.key)" class="scale-help-popover" role="tooltip">
                        <strong>{{ field.label }}评分说明</strong>
                        <ul>
                          <li v-for="item in field.descriptions" :key="item">{{ item }}</li>
                        </ul>
                      </div>
                    </transition>
                  </div>
                  <van-stepper v-model="predictNextForm[field.key]" min="1" max="5" integer />
                </div>
              </div>

              <div class="action-block">
                <van-button round block type="primary" native-type="submit" :loading="predictingNext">预测效率</van-button>
              </div>
            </van-form>

            <section v-if="predictNextResult" class="prediction-box" style="margin-top: 12px;">
              <div>
                <span>预期效率等级</span>
                <strong :class="['prediction-label', predictNextResult.predicted_label]">
                  {{ labelMap[predictNextResult.predicted_label] }}
                </strong>
              </div>
              <div>
                <span>置信度</span>
                <strong>{{ formatPercent(predictNextResult.confidence) }}</strong>
              </div>
              <p>{{ predictNextResult.suggestion }}</p>
            </section>

            <section v-if="predictNextResult?.feature_suggestions?.length" style="margin-top: 12px;">
              <h4 style="margin-bottom: 8px; font-size: 14px;">优化建议：调整以下参数可提升预测等级</h4>
              <div class="suggestion-list">
                <article v-for="item in predictNextResult.feature_suggestions" :key="item.field" class="suggestion-item active">
                  <strong>{{ item.field_label }}</strong>
                  <span>{{ item.current_value }} → {{ item.suggested_value }}</span>
                  <p>预测等级将从 {{ item.impact }}</p>
                </article>
              </div>
            </section>

            <div v-if="predictNextResult" class="action-block" style="margin-top: 12px;">
              <van-button round block type="primary" :loading="loading" @click="handleStartWithPrediction">
                用此参数开始学习
              </van-button>
            </div>
          </section>

          <section class="dashboard-panel">
            <div class="panel-heading">
              <div>
                <h3>学习趋势</h3>
                <p>按日期聚合学习时长和平均效率评分。</p>
              </div>
            </div>
            <div class="trend-list">
              <div v-for="item in analyticsTrend" :key="item.date" class="trend-row">
                <span class="trend-date">{{ item.date.slice(5) }}</span>
                <div class="trend-bars">
                  <div class="trend-bar duration">
                    <i :style="{ width: barPercent(item.duration_minutes, maxTrendDuration) }"></i>
                    <span>{{ item.duration_minutes }} 分钟</span>
                  </div>
                  <div class="trend-bar score">
                    <i :style="{ width: barPercent(item.avg_efficiency_score, maxTrendScore) }"></i>
                    <span>评分 {{ item.avg_efficiency_score || '-' }}</span>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <section class="dashboard-panel">
            <div class="panel-heading">
              <div>
                <h3>时段效率对比</h3>
                <p>比较不同开始时段的学习时长与效率。</p>
              </div>
            </div>
            <div class="period-grid">
              <article v-for="item in analyticsFactors.time_periods" :key="item.time_period" class="period-item">
                <div class="period-top">
                  <strong>{{ timePeriodText(item.time_period) }}</strong>
                  <span>{{ item.session_count }} 次</span>
                </div>
                <div class="period-meter">
                  <i :style="{ width: barPercent(item.duration_minutes, maxPeriodDuration) }"></i>
                </div>
                <dl>
                  <div>
                    <dt>时长</dt>
                    <dd>{{ item.duration_minutes }} 分钟</dd>
                  </div>
                  <div>
                    <dt>均分</dt>
                    <dd>{{ item.avg_efficiency_score || '-' }}</dd>
                  </div>
                  <div>
                    <dt>高效占比</dt>
                    <dd>{{ formatPercent(item.high_efficiency_ratio) }}</dd>
                  </div>
                </dl>
              </article>
            </div>
          </section>

          <section class="dashboard-panel">
            <div class="panel-heading">
              <div>
                <h3>特征重要性</h3>
                <p v-if="analyticsFactors.model_snapshot.available">
                  模型版本：{{ analyticsFactors.model_snapshot.model_version }} · 数据来源：{{ analyticsFactors.model_snapshot.data_source }}
                </p>
                <p v-else>尚未训练模型，可用 mock 数据先验证答辩演示链路。</p>
              </div>
              <van-button size="small" plain type="primary" :loading="trainingModel" @click="handleTrainDemoModel">
                训练演示模型
              </van-button>
            </div>
            <section
              v-if="analyticsFactors.model_snapshot.available && !analyticsFactors.model_snapshot.valid_for_research_conclusion"
              class="status-banner warning dashboard-warning"
            >
              当前模型不可作为真实学习效率结论，只用于系统流程演示。
            </section>
            <div v-if="analyticsFactors.model_snapshot.available" class="model-metrics-grid">
              <div>
                <span>训练样本</span>
                <strong>{{ analyticsFactors.model_snapshot.sample_count || '-' }}</strong>
              </div>
              <div>
                <span>Accuracy</span>
                <strong>{{ analyticsFactors.model_snapshot.metrics?.accuracy ?? '-' }}</strong>
              </div>
              <div>
                <span>F1 Macro</span>
                <strong>{{ analyticsFactors.model_snapshot.metrics?.f1_macro ?? '-' }}</strong>
              </div>
              <div>
                <span>真实结论</span>
                <strong>{{ analyticsFactors.model_snapshot.valid_for_research_conclusion ? '可谨慎使用' : '不可使用' }}</strong>
              </div>
            </div>
            <div v-if="analyticsFactors.model_snapshot.feature_importance.length" class="feature-bars">
              <div
                v-for="item in analyticsFactors.model_snapshot.feature_importance"
                :key="item.feature_name"
                class="feature-row"
              >
                <span>{{ featureText(item.feature_name) }}</span>
                <div>
                  <i :style="{ width: barPercent(item.importance_score, maxFeatureImportance) }"></i>
                </div>
                <strong>{{ item.importance_score.toFixed(3) }}</strong>
              </div>
            </div>
            <p v-else class="empty-hint">暂无特征重要性。训练模型后这里会显示前 10 个特征。</p>
          </section>

          <section class="dashboard-panel">
            <div class="panel-heading">
              <div>
                <h3>运动次数与效率关系</h3>
                <p>横轴为移动次数，纵轴为效率评分；仅展示有运动特征的记录。</p>
              </div>
            </div>
            <div v-if="analyticsFactors.motion_efficiency_points.length" class="scatter-plot">
              <span class="axis-label y">效率评分</span>
              <span class="axis-label x">移动次数</span>
              <button
                v-for="point in analyticsFactors.motion_efficiency_points"
                :key="point.session_id"
                :class="['scatter-dot', point.efficiency_label]"
                :style="scatterStyle(point)"
                type="button"
                :title="`移动 ${point.move_count} 次，评分 ${point.efficiency_score}`"
                :aria-label="`移动 ${point.move_count} 次，评分 ${point.efficiency_score}`"
              />
            </div>
            <p v-else class="empty-hint">暂无带运动特征的已完成记录；缺失运动数据不会影响总览统计。</p>
          </section>

          <section class="dashboard-panel">
            <div class="panel-heading">
              <div>
                <h3>规则建议</h3>
                <p>基于疲劳、手机干扰、目标清晰度、噪声和深夜学习触发。</p>
              </div>
            </div>
            <div class="suggestion-list">
              <article v-for="item in topActiveSuggestions" :key="item.code" :class="['suggestion-item', item.active ? 'active' : '']">
                <strong>{{ item.title }}</strong>
                <span>{{ item.trigger_count }} 条触发</span>
                <p>{{ item.message }}</p>
              </article>
            </div>
          </section>
        </div>
      </section>

      <section v-else-if="view === 'edit'" class="screen form-screen">
        <div class="section-title">
          <h2>修改学习记录</h2>
          <p>开始时间：{{ formatDate(records.find((item) => item.id === editingRecordId)?.start_time) }}</p>
        </div>

        <van-form @submit="handleEditSubmit">
          <van-cell-group inset>
            <label class="select-field">
              <span>学习地点</span>
              <select v-model="editForm.location" required>
                <option value="" disabled>请选择</option>
                <option v-for="item in locationOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
              </select>
            </label>
            <label class="select-field">
              <span>任务类型</span>
              <select v-model="editForm.task_type" required>
                <option value="" disabled>请选择</option>
                <option v-for="item in taskTypeOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
              </select>
            </label>
          </van-cell-group>

          <div class="scale-list">
            <div
              v-for="field in scaleFields"
              :key="field.key"
              :class="[
                'scale-item',
                field.key === 'efficiency_score' ? 'strong' : '',
                activeScaleHelp === scaleHelpId('edit', field.key) ? 'help-open' : '',
              ]"
            >
              <div class="scale-label-wrap">
                <button
                  class="scale-help-trigger"
                  type="button"
                  :aria-label="`${field.label}评分说明`"
                  :aria-expanded="activeScaleHelp === scaleHelpId('edit', field.key)"
                  @click="toggleScaleHelp(scaleHelpId('edit', field.key))"
                >
                  ?
                </button>
                <span>{{ field.label }}</span>
                <transition name="help-pop">
                  <div v-if="activeScaleHelp === scaleHelpId('edit', field.key)" class="scale-help-popover" role="tooltip">
                    <strong>{{ field.label }}评分说明</strong>
                    <ul>
                      <li v-for="item in field.descriptions" :key="item">{{ item }}</li>
                    </ul>
                  </div>
                </transition>
              </div>
              <van-stepper v-model="editForm[field.key]" min="1" max="5" integer />
            </div>
          </div>

          <div class="action-block sticky-actions">
            <van-button round block type="primary" native-type="submit" :loading="loading">保存修改</van-button>
            <van-button round block plain type="default" @click="cancelEditRecord">取消</van-button>
          </div>
        </van-form>
      </section>
    </main>
  </van-config-provider>
</template>
