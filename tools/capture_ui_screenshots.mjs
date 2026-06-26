import { spawn } from 'node:child_process'
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const SCRIPT_DIR = dirname(fileURLToPath(import.meta.url))
const REPO_ROOT = process.env.REPO_ROOT || resolve(SCRIPT_DIR, '..')
const OUT_DIR = resolve(REPO_ROOT, 'deliverables', 'figures')
const BASE_URL = process.env.FRONTEND_URL || 'http://127.0.0.1:5173/'
const API_URL = process.env.API_URL || 'http://127.0.0.1:8000/api'
const DEVTOOLS_PORT = Number(process.env.DEVTOOLS_PORT || 9224)
const CHROME_CANDIDATES = [
  process.env.CHROME_EXE,
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
  'C:\\Users\\win\\.cache\\puppeteer\\chrome\\win64-146.0.7680.153\\chrome-win64\\chrome.exe',
  '/mnt/c/Program Files/Google/Chrome/Application/chrome.exe',
  '/mnt/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  '/mnt/c/Users/win/.cache/puppeteer/chrome/win64-146.0.7680.153/chrome-win64/chrome.exe',
].filter(Boolean)

const USER = {
  id: 1,
  nickname: 'demo_student',
  grade: '2024',
  major: '物联网工程',
}

const sleep = (ms) => new Promise((resolveSleep) => setTimeout(resolveSleep, ms))

function findChrome() {
  for (const candidate of CHROME_CANDIDATES) {
    try {
      readFileSync(candidate)
      return candidate
    } catch {
      // Try next known browser path.
    }
  }
  throw new Error('No Chrome or Edge executable found for automated screenshots.')
}

function windowsHostCandidates() {
  const hosts = ['127.0.0.1']
  try {
    const resolv = readFileSync('/etc/resolv.conf', 'utf8')
    const match = resolv.match(/^nameserver\s+(.+)$/m)
    if (match?.[1] && !hosts.includes(match[1])) hosts.push(match[1])
  } catch {
    // Best-effort host discovery.
  }
  return hosts
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options)
  if (!response.ok) {
    const text = await response.text()
    throw new Error(`HTTP ${response.status} for ${url}: ${text}`)
  }
  return response.json()
}

async function waitForDevTools() {
  let lastError = null
  for (let i = 0; i < 60; i += 1) {
    for (const host of windowsHostCandidates()) {
      try {
        const version = await fetchJson(`http://${host}:${DEVTOOLS_PORT}/json/version`)
        return { host, version }
      } catch (error) {
        lastError = error
      }
    }
    await sleep(500)
  }
  throw lastError || new Error('Chrome DevTools endpoint did not become available.')
}

function normalizeWsUrl(wsUrl, host) {
  const url = new URL(wsUrl)
  url.hostname = host
  return url.toString()
}

async function createTarget(host, url) {
  const target = await fetchJson(
    `http://${host}:${DEVTOOLS_PORT}/json/new?${encodeURIComponent(url)}`,
    { method: 'PUT' },
  )
  return { ...target, webSocketDebuggerUrl: normalizeWsUrl(target.webSocketDebuggerUrl, host) }
}

function connect(wsUrl) {
  return new Promise((resolveConnect, rejectConnect) => {
    const ws = new WebSocket(wsUrl)
    let nextId = 1
    const pending = new Map()

    ws.addEventListener('open', () => {
      resolveConnect({
        send(method, params = {}) {
          const id = nextId
          nextId += 1
          ws.send(JSON.stringify({ id, method, params }))
          return new Promise((resolveSend, rejectSend) => {
            pending.set(id, { resolve: resolveSend, reject: rejectSend })
          })
        },
        close() {
          ws.close()
        },
      })
    })

    ws.addEventListener('message', (event) => {
      const message = JSON.parse(event.data)
      if (!message.id) return
      const handler = pending.get(message.id)
      if (!handler) return
      pending.delete(message.id)
      if (message.error) {
        handler.reject(new Error(`${message.error.message}: ${message.error.data || ''}`))
      } else {
        handler.resolve(message.result)
      }
    })

    ws.addEventListener('error', (error) => rejectConnect(error))
  })
}

async function evaluate(cdp, expression, awaitPromise = true) {
  const result = await cdp.send('Runtime.evaluate', {
    expression,
    awaitPromise,
    returnByValue: true,
  })
  if (result.exceptionDetails) {
    throw new Error(result.exceptionDetails.text || 'Runtime.evaluate failed')
  }
  return result.result?.value
}

async function waitForText(cdp, pattern, timeoutMs = 12000) {
  const started = Date.now()
  while (Date.now() - started < timeoutMs) {
    const text = await evaluate(cdp, 'document.body ? document.body.innerText : ""')
    if (pattern.test(text || '')) return text
    await sleep(350)
  }
  throw new Error(`Timed out waiting for page text matching ${pattern}`)
}

async function setUserAndReload(cdp, activeSession = null) {
  const activeExpression = activeSession
    ? `localStorage.setItem('study-efficiency:active-session', ${JSON.stringify(JSON.stringify(activeSession))});`
    : "localStorage.removeItem('study-efficiency:active-session');"
  await evaluate(
    cdp,
    `
      localStorage.setItem('study-efficiency:user', ${JSON.stringify(JSON.stringify(USER))});
      ${activeExpression}
      location.reload();
    `,
    false,
  )
  await sleep(1800)
}

async function clickButtonContaining(cdp, text) {
  await evaluate(
    cdp,
    `
      (() => {
        const button = [...document.querySelectorAll('button')].find((item) =>
          (item.innerText || item.textContent || '').includes(${JSON.stringify(text)})
        );
        if (!button) throw new Error('button not found: ${text}');
        button.click();
      })()
    `,
  )
}

async function screenshot(cdp, filename) {
  await cdp.send('Page.bringToFront')
  await sleep(350)
  const result = await cdp.send('Page.captureScreenshot', {
    format: 'png',
    fromSurface: true,
    captureBeyondViewport: false,
  })
  const output = resolve(OUT_DIR, filename)
  writeFileSync(output, Buffer.from(result.data, 'base64'))
  return output
}

async function ensureActiveSession() {
  const list = await fetchJson(`${API_URL}/sessions/list?user_id=${USER.id}&limit=100`)
  const existing = (list.items || []).find((item) => item.status === 'in_progress' && !item.end_time)
  if (existing) {
    const detail = await fetchJson(`${API_URL}/sessions/${existing.id}`)
    return detail
  }
  const start = new Date(Date.now() - 46 * 60 * 1000).toISOString()
  return fetchJson(`${API_URL}/sessions/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: USER.id, start_time: start }),
  })
}

async function ensureLatestPrediction() {
  const list = await fetchJson(`${API_URL}/sessions/list?user_id=${USER.id}&limit=100`)
  const completed = (list.items || []).find((item) => item.status === 'completed' && item.efficiency_score)
  if (!completed?.id) return null
  try {
    return await fetchJson(`${API_URL}/model/predict`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: completed.id }),
    })
  } catch (error) {
    console.warn(`Prediction setup skipped: ${error.message}`)
    return null
  }
}

async function main() {
  mkdirSync(OUT_DIR, { recursive: true })
  const chrome = findChrome()
  const profileDir = `C:\\Users\\win\\AppData\\Local\\Temp\\study-efficiency-capture-${Date.now()}`
  const chromeProcess = spawn(
    chrome,
    [
      '--headless=new',
      '--disable-gpu',
      '--no-first-run',
      '--no-default-browser-check',
      '--hide-scrollbars',
      `--remote-debugging-port=${DEVTOOLS_PORT}`,
      `--user-data-dir=${profileDir}`,
      '--window-size=390,844',
      'about:blank',
    ],
    { stdio: 'ignore' },
  )

  try {
    const { host } = await waitForDevTools()
    const target = await createTarget(host, 'about:blank')
    const cdp = await connect(target.webSocketDebuggerUrl)

    await cdp.send('Page.enable')
    await cdp.send('Runtime.enable')
    await cdp.send('Emulation.setDeviceMetricsOverride', {
      width: 390,
      height: 844,
      deviceScaleFactor: 2,
      mobile: true,
      screenWidth: 390,
      screenHeight: 844,
    })
    await cdp.send('Emulation.setUserAgentOverride', {
      userAgent:
        'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
    })

    await cdp.send('Page.navigate', { url: BASE_URL })
    await sleep(1600)
    await setUserAndReload(cdp)
    await waitForText(cdp, /当前用户|开始学习/)
    await screenshot(cdp, 'ui-1-home.png')

    await ensureLatestPrediction()
    await clickButtonContaining(cdp, '分析看板')
    await waitForText(cdp, /分析看板|总学习次数|特征重要性/)
    await sleep(1200)
    await screenshot(cdp, 'ui-4-dashboard.png')

    const activeSession = await ensureActiveSession()
    await setUserAndReload(cdp, activeSession)
    await waitForText(cdp, /学习中|运动检测状态/)
    await screenshot(cdp, 'ui-2-study.png')

    await clickButtonContaining(cdp, '结束学习并填写表单')
    await waitForText(cdp, /结束学习表单|学习地点|任务类型/)
    await evaluate(
      cdp,
      `
        (() => {
          const selects = document.querySelectorAll('select');
          if (selects[0]) {
            selects[0].value = 'library';
            selects[0].dispatchEvent(new Event('change', { bubbles: true }));
          }
          if (selects[1]) {
            selects[1].value = 'coding';
            selects[1].dispatchEvent(new Event('change', { bubbles: true }));
          }
        })()
      `,
    )
    await sleep(500)
    await screenshot(cdp, 'ui-3-end-form.png')
    cdp.close()

    console.log(JSON.stringify({
      outDir: OUT_DIR,
      screenshots: [
        'ui-1-home.png',
        'ui-2-study.png',
        'ui-3-end-form.png',
        'ui-4-dashboard.png',
      ],
    }, null, 2))
  } finally {
    chromeProcess.kill()
  }
}

main().catch((error) => {
  console.error(error)
  process.exit(1)
})
