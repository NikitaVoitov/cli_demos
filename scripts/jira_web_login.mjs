// One-time sign-in to the personal demo Jira site, saved for scripts/so07_screenshot.mjs.
// Usage (from the repo root): node scripts/jira_web_login.mjs
//
// Opens your real Google Chrome with its own profile (passkeys and Google sign-in work, and Google
// sees no automation). Playwright only attaches afterwards to read the cookies. Sign in as the
// demo-site account; the session is saved once Atlassian sets its session cookie.
import { spawn } from 'node:child_process'
import { mkdirSync, readFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const require = createRequire(resolve(root, 'apps/hub/package.json'))
const { chromium } = require('@playwright/test')

const env = Object.fromEntries(
  readFileSync(resolve(root, '.env'), 'utf8')
    .split('\n')
    .filter((line) => line.includes('='))
    .map((line) => [line.slice(0, line.indexOf('=')), line.slice(line.indexOf('=') + 1).trim().replace(/^['"]|['"]$/g, '')]),
)
const site = (env.JIRA_SITE ?? '').replace(/^https:\/\//, '').replace(/\/$/, '')
if (!site.endsWith('.atlassian.net') || site === 'splunk.atlassian.net') throw new Error('JIRA_SITE must be the personal demo site')

const secrets = resolve(root, '.captures/so07/secrets')
const profile = resolve(root, '.captures/so07/chrome-profile')
mkdirSync(secrets, { recursive: true })
mkdirSync(profile, { recursive: true })

const PORT = 9333
const chrome = spawn(
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  [`--remote-debugging-port=${PORT}`, `--user-data-dir=${profile}`, '--no-first-run', '--no-default-browser-check', `https://${site}/jira/projects`],
  { stdio: 'ignore' },
)
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

let browser
for (let i = 0; i < 30 && !browser; i++) {
  try {
    browser = await chromium.connectOverCDP(`http://127.0.0.1:${PORT}`)
  } catch {
    await sleep(500)
  }
}
if (!browser) {
  chrome.kill()
  throw new Error('Could not attach to Chrome. Quit every Chrome window started by this script and retry.')
}

const context = browser.contexts()[0]
console.log(`Sign in to ${site} in the Chrome window (up to 5 minutes)...`)

// Signed in = Atlassian has set a session cookie that applies to the demo site.
const signedIn = async () =>
  (await context.cookies()).some((c) => /session\.token/.test(c.name) && c.domain.replace(/^\./, '').endsWith('atlassian.net'))
const deadline = Date.now() + 300000
while (!(await signedIn())) {
  if (Date.now() > deadline) {
    chrome.kill()
    throw new Error('Timed out waiting for sign-in')
  }
  await sleep(1000)
}

// Give Jira a moment to finish its post-login redirects. Don't wait for "networkidle": Jira keeps
// polling in the background, so that state never arrives.
const page = context.pages().find((p) => new URL(p.url()).hostname === site) ?? context.pages()[0]
await page.waitForLoadState('load').catch(() => {})
await sleep(3000)
await context.storageState({ path: resolve(secrets, 'jira-state.json') })
console.log('saved .captures/so07/secrets/jira-state.json')
await browser.close()
chrome.kill()
