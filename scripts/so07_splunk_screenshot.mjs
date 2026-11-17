// Captures the AI Toolkit result for the SO-07 pane: Splunk Web running the demo_ip_decline_outliers saved search,
// with its `apply app:demo_ip_decline_model` SPL and the flagged rows (viewport only, no browser chrome).
// Usage (from the repo root): node scripts/so07_splunk_screenshot.mjs
// Needs a fresh session from scripts/splunk_web_login.mjs (every capture refreshes it). Prints no hostnames, and
// shows the signed-in user under a placeholder name.
import { readFileSync } from 'node:fs'
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
const saved = 'demo_ip_decline_outliers'
const base = readFileSync(resolve(root, '.captures/ce01/secrets/web_base'), 'utf8').trim()
const out = resolve(root, 'scenarios/so-07-jira-alert-investigation/artifacts/splunk-ml.png')

const browser = await chromium.launch()
const context = await browser.newContext({
  storageState: resolve(root, '.captures/ce01/secrets/web-state.json'),
  // Narrower than CE-01's 1440 px: the pane is small, and the SPL and three rows need to stay readable.
  viewport: { width: 1000, height: 850 },
  deviceScaleFactor: 2,
  ignoreHTTPSErrors: true,
  colorScheme: 'dark',
})
const page = await context.newPage()
await page.goto(`${base}/en-US/app/search/search?s=${encodeURIComponent(saved)}`, { waitUntil: 'domcontentloaded' })
if (page.url().includes('/account/login')) throw new Error('Splunk Web session expired; rerun splunk_web_login.mjs')

await page.getByText('203.0.113.178').first().waitFor({ timeout: 90000 })
await page.waitForTimeout(3000)
// A one-time "AI Assistant is now active" callout covers the end of the SPL, where IsOutlier is.
const callout = page.getByText('is now active').first()
if (await callout.isVisible().catch(() => false)) {
  await callout.evaluate((el) => {
    let box = el
    while (box.parentElement && !box.querySelector('button')) box = box.parentElement
    box.querySelector('button')?.click()
  })
  await page.waitForTimeout(800)
}
await page.evaluate((user) => {
  for (const el of document.querySelectorAll('span, a, div, button')) {
    if (el.childNodes.length === 1 && el.childNodes[0].nodeType === 3 && el.textContent.trim() === user) el.textContent = 'Analyst'
  }
}, env.SPLUNK_WEB_USER)
await page.mouse.move(0, 0)
await page.screenshot({ path: out })
console.log(`saved ${out.replace(root + '/', '')} · ${saved}`)
await browser.close()
