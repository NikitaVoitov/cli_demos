// One-time GitHub sign-in for SO-05's pull request screenshot (scenarios/so-05-sigma-detection-as-code/fixtures/screenshots.mjs).
// Usage (from the repo root): node scripts/github_web_login.mjs
//
// Opens your real Google Chrome with its own profile, so passkeys and SSO work and GitHub sees no automation.
// Playwright only attaches afterwards to read the cookies. Sign in with the account that owns DAC_DEMO_REPO; the
// session is saved once GitHub sets its user_session cookie. Prints no names or tokens.
import { spawn } from 'node:child_process'
import { chmodSync, mkdirSync } from 'node:fs'
import { createRequire } from 'node:module'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const require = createRequire(resolve(root, 'apps/hub/package.json'))
const { chromium } = require('@playwright/test')

const secrets = resolve(root, '.captures/so05/secrets')
const profile = resolve(root, '.captures/so05/chrome-profile')
mkdirSync(secrets, { recursive: true })
mkdirSync(profile, { recursive: true })

const PORT = 9334
const chrome = spawn(
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  [`--remote-debugging-port=${PORT}`, `--user-data-dir=${profile}`, '--no-first-run', '--no-default-browser-check', 'https://github.com/login'],
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
console.log('Sign in to GitHub in the Chrome window (up to 5 minutes)...')
const signedIn = async () => (await context.cookies('https://github.com')).some((c) => c.name === 'user_session')
const deadline = Date.now() + 300000
while (!(await signedIn())) {
  if (Date.now() > deadline) {
    chrome.kill()
    throw new Error('Timed out waiting for sign-in')
  }
  await sleep(1000)
}
await sleep(3000)
const out = resolve(secrets, 'github-state.json')
await context.storageState({ path: out })
chmodSync(out, 0o600)
console.log('saved .captures/so05/secrets/github-state.json')
await browser.close()
chrome.kill()
