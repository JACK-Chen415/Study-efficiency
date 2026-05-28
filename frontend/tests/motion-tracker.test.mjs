import assert from 'node:assert/strict'
import {
  createMotionAccumulator,
  useMotionTracker,
} from '../src/composables/useMotionTracker.js'
import { uploadMotion } from '../src/api/motion.js'

function testAccumulator() {
  const accumulator = createMotionAccumulator()
  assert.equal(accumulator.addEvent({ acceleration: { x: 0.1, y: 0, z: 0 } }), true)
  assert.equal(accumulator.addEvent({ acceleration: { x: 1.3, y: 0, z: 0 } }), true)
  assert.equal(accumulator.addEvent({ acceleration: { x: 4, y: 0, z: 0 } }), true)
  assert.equal(accumulator.addEvent({ acceleration: { x: null, y: null, z: null } }), false)
  assert.deepEqual(accumulator.features(), {
    move_count: 2,
    shake_count: 1,
    still_ratio: 0.3333,
    avg_acceleration: 1.8,
    max_acceleration: 4,
  })
}

function testUnsupportedDeviceFallback() {
  globalThis.window = {
    DeviceMotionEvent: undefined,
    isSecureContext: true,
    clearTimeout() {},
    removeEventListener() {},
  }
  const tracker = useMotionTracker()
  tracker.beginSession()
  assert.equal(tracker.status.value, 'unavailable')
  assert.equal(tracker.message.value, '运动检测不可用，本次仍可正常记录学习。')
}

async function testPermissionAndEventCollection() {
  let eventHandler = null
  globalThis.window = {
    DeviceMotionEvent: { requestPermission: async () => 'granted' },
    isSecureContext: true,
    addEventListener(type, handler) {
      if (type === 'devicemotion') eventHandler = handler
    },
    removeEventListener() {},
    setTimeout() {
      return 1
    },
    clearTimeout() {},
  }

  const tracker = useMotionTracker()
  tracker.beginSession()
  assert.equal(tracker.requiresPermission.value, true)
  await tracker.requestPermission()
  assert.equal(tracker.isListening.value, true)
  eventHandler({ acceleration: { x: 4, y: 0, z: 0 } })
  assert.equal(tracker.sampleCount.value, 1)
  assert.deepEqual(tracker.finishSession(), {
    move_count: 1,
    shake_count: 1,
    still_ratio: 0,
    avg_acceleration: 4,
    max_acceleration: 4,
  })
}


async function testMotionUploadPayload() {
  let sentUrl = null
  let sentPayload = null
  globalThis.fetch = async (url, options) => {
    sentUrl = url
    sentPayload = JSON.parse(options.body)
    return new Response(JSON.stringify({ id: 1, ...sentPayload }), {
      status: 201,
      headers: { 'Content-Type': 'application/json' },
    })
  }
  const payload = {
    session_id: 12,
    move_count: 2,
    shake_count: 1,
    still_ratio: 0.3333,
    avg_acceleration: 1.8,
    max_acceleration: 4,
  }
  const result = await uploadMotion(payload)
  assert.equal(sentUrl, '/api/motion/upload')
  assert.deepEqual(sentPayload, payload)
  assert.equal(result.session_id, payload.session_id)
  delete globalThis.fetch
}

function testNoSamplesDoesNotCreateFeatures() {
  globalThis.window = {
    DeviceMotionEvent: function DeviceMotionEvent() {},
    isSecureContext: true,
    addEventListener() {},
    removeEventListener() {},
    setTimeout() {
      return 1
    },
    clearTimeout() {},
  }
  const tracker = useMotionTracker()
  tracker.beginSession()
  assert.equal(tracker.finishSession(), null)
  assert.equal(tracker.message.value, '未采集到有效运动数据。')
}

testAccumulator()
testUnsupportedDeviceFallback()
await testPermissionAndEventCollection()
await testMotionUploadPayload()
testNoSamplesDoesNotCreateFeatures()
delete globalThis.window
console.log('Motion tracker tests passed')
