import { computed, ref } from 'vue'

export const MOVE_THRESHOLD = 1.2
export const SHAKE_THRESHOLD = 3.5
export const STILL_THRESHOLD = 0.35

const STANDARD_GRAVITY = 9.80665
const NO_SAMPLE_DELAY = 5000
const UNAVAILABLE_MESSAGE = '运动检测不可用，本次仍可正常记录学习。'

function round(value) {
  return Number(value.toFixed(4))
}

function vectorMagnitude(vector) {
  if (!vector) return null
  const axes = [vector.x, vector.y, vector.z]
  if (!axes.every((axis) => typeof axis === 'number' && Number.isFinite(axis))) {
    return null
  }
  return Math.sqrt(axes[0] ** 2 + axes[1] ** 2 + axes[2] ** 2)
}

export function activityMagnitude(event) {
  const linearMagnitude = vectorMagnitude(event?.acceleration)
  if (linearMagnitude !== null) {
    return linearMagnitude
  }

  const includingGravity = vectorMagnitude(event?.accelerationIncludingGravity)
  if (includingGravity === null) {
    return null
  }

  return Math.abs(includingGravity - STANDARD_GRAVITY)
}

export function createMotionAccumulator() {
  let moveCount = 0
  let shakeCount = 0
  let stillCount = 0
  let sampleCount = 0
  let magnitudeTotal = 0
  let maximumMagnitude = 0

  function addEvent(event) {
    const magnitude = activityMagnitude(event)
    if (magnitude === null) {
      return false
    }

    sampleCount += 1
    magnitudeTotal += magnitude
    maximumMagnitude = Math.max(maximumMagnitude, magnitude)
    if (magnitude >= MOVE_THRESHOLD) moveCount += 1
    if (magnitude >= SHAKE_THRESHOLD) shakeCount += 1
    if (magnitude <= STILL_THRESHOLD) stillCount += 1
    return true
  }

  function features() {
    if (sampleCount === 0) return null
    return {
      move_count: moveCount,
      shake_count: shakeCount,
      still_ratio: round(stillCount / sampleCount),
      avg_acceleration: round(magnitudeTotal / sampleCount),
      max_acceleration: round(maximumMagnitude),
    }
  }

  function samples() {
    return sampleCount
  }

  return { addEvent, features, samples }
}

export function useMotionTracker() {
  const status = ref('idle')
  const message = ref('开始学习后可启用运动检测。')
  const sampleCount = ref(0)
  const aggregatedFeatures = ref(null)

  let accumulator = createMotionAccumulator()
  let listening = false
  let noSampleTimer = null

  const requiresPermission = computed(() => status.value === 'permission_required')
  const isListening = computed(() => status.value === 'listening')
  const hasFeatures = computed(() => sampleCount.value > 0 && aggregatedFeatures.value !== null)

  function clearSampleTimer() {
    if (noSampleTimer !== null && typeof window !== 'undefined') {
      window.clearTimeout(noSampleTimer)
    }
    noSampleTimer = null
  }

  function stopListening() {
    clearSampleTimer()
    if (listening && typeof window !== 'undefined') {
      window.removeEventListener('devicemotion', handleMotion)
    }
    listening = false
  }

  function markUnavailable() {
    stopListening()
    status.value = 'unavailable'
    message.value = UNAVAILABLE_MESSAGE
  }

  function resetSamples() {
    accumulator = createMotionAccumulator()
    sampleCount.value = 0
    aggregatedFeatures.value = null
  }

  function handleMotion(event) {
    try {
      if (!accumulator.addEvent(event)) return
      sampleCount.value = accumulator.samples()
      aggregatedFeatures.value = accumulator.features()
      message.value = `正在采集运动数据，已获得 ${sampleCount.value} 个有效样本。`
    } catch {
      markUnavailable()
    }
  }

  function startListening() {
    if (listening) return
    window.addEventListener('devicemotion', handleMotion)
    listening = true
    status.value = 'listening'
    message.value = '运动检测已启用，等待有效运动数据。'
    noSampleTimer = window.setTimeout(() => {
      if (sampleCount.value === 0 && listening) {
        message.value = '未采集到有效运动数据，学习记录仍可正常提交。'
      }
    }, NO_SAMPLE_DELAY)
  }

  function beginSession() {
    stopListening()
    resetSamples()

    if (typeof window === 'undefined' || typeof window.DeviceMotionEvent === 'undefined') {
      markUnavailable()
      return
    }
    if (window.isSecureContext === false) {
      markUnavailable()
      return
    }
    if (typeof window.DeviceMotionEvent.requestPermission === 'function') {
      status.value = 'permission_required'
      message.value = '需要授权后才能采集运动数据。'
      return
    }

    startListening()
  }

  async function requestPermission() {
    if (!requiresPermission.value) return
    try {
      const permission = await window.DeviceMotionEvent.requestPermission()
      if (permission !== 'granted') {
        markUnavailable()
        return
      }
      startListening()
    } catch {
      markUnavailable()
    }
  }

  function finishSession() {
    stopListening()
    if (!hasFeatures.value) {
      status.value = 'empty'
      message.value = '未采集到有效运动数据。'
      return null
    }
    status.value = 'collected'
    message.value = '运动特征已完成聚合。'
    return aggregatedFeatures.value
  }

  function cancelSession() {
    stopListening()
    resetSamples()
    status.value = 'idle'
    message.value = '开始学习后可启用运动检测。'
  }

  return {
    aggregatedFeatures,
    beginSession,
    cancelSession,
    finishSession,
    hasFeatures,
    isListening,
    message,
    requestPermission,
    requiresPermission,
    sampleCount,
    status,
  }
}

