// Logs in to Splunk Web once and saves a Playwright storage state for capture.
// Usage (from apps/hub so @playwright/test resolves): node ../../scripts/splunk_web_login.mjs
// Reads SPLUNK_WEB_USER and SPLUNK_WEB_PASSWORD from .env and the base URL from
// .captures/ce01/secrets/web_base. Prints no credentials or hostnames.
// CAPTURE_STACK=<name> uses .captures/ce01/stacks/<name>/secrets instead, and SPLUNK_WEB_USER_<NAME> and
// SPLUNK_WEB_PASSWORD_<NAME> from .env when they are set.
import { readFileSync, writeFileSync, chmodSync } from 'node:fs'
import { createRequire } from 'node:module'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const require = createRequire(resolve(root, 'apps/hub/package.json'))
const { chromium } = require('@playwright/test')

const env = Object.fromEntries(
  readFileSync(resolve(root, '.env'), 'utf8')
    .split('\n')
    .filter((l) => l.includes('='))
    .map((l) => [l.slice(0, l.indexOf('=')), l.slice(l.indexOf('=') + 1).trim().replace(/^['"]|['"]$/g, '')]),
)
const stack = process.env.CAPTURE_STACK || ''
const secrets = resolve(root, stack ? `.captures/ce01/stacks/${stack}/secrets` : '.captures/ce01/secrets')
const suffix = stack ? `_${stack.toUpperCase()}` : ''
const user = env[`SPLUNK_WEB_USER${suffix}`] || env.SPLUNK_WEB_USER
const password = env[`SPLUNK_WEB_PASSWORD${suffix}`] || env.SPLUNK_WEB_PASSWORD
const base = readFileSync(resolve(secrets, 'web_base'), 'utf8').trim()
const out = resolve(secrets, 'web-state.json')

const browser = await chromium.launch()
const context = await browser.newContext({ ignoreHTTPSErrors: true })
const page = await context.newPage()
await page.goto(`${base}/en-US/account/login`, { waitUntil: 'domcontentloaded' })
await page.locator('input[name="username"]').fill(user)
await page.locator('input[name="password"]').fill(password)
await Promise.all([page.waitForURL((u) => !u.pathname.includes('/account/login'), { timeout: 60000 }), page.keyboard.press('Enter')])
await page.goto(`${base}/en-US/app/search/search`, { waitUntil: 'domcontentloaded' })
const loggedIn = !page.url().includes('/account/login')
await context.storageState({ path: out })
chmodSync(out, 0o600)
console.log(loggedIn ? 'logged in; storage state saved' : 'login failed')
await browser.close()
process.exit(loggedIn ? 0 : 1)
