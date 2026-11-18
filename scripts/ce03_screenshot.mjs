// Captures the CE-03 pane screenshots from Splunk Web (viewport only, no browser chrome).
//   chart: the CDTSM anomaly search on eu-west-1 p95 latency, as the AI Toolkit Anomaly Detection Chart.
//   alert: the demo_checkout_latency_anomaly alert the agent created.
// Usage (from the repo root): node scripts/ce03_screenshot.mjs chart|alert
// Needs a fresh session from scripts/splunk_web_login.mjs. Prints no hostnames, and shows the signed-in user under
// a placeholder name.
import { readFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const require = createRequire(resolve(root, 'apps/hub/package.json'))
const { chromium } = require('@playwright/test')

const mode = process.argv[2]
if (!['chart', 'alert'].includes(mode)) throw new Error('usage: node scripts/ce03_screenshot.mjs chart|alert')

const env = Object.fromEntries(
  readFileSync(resolve(root, '.env'), 'utf8')
    .split('\n')
    .filter((line) => line.includes('='))
    .map((line) => [line.slice(0, line.indexOf('=')), line.slice(line.indexOf('=') + 1).trim().replace(/^['"]|['"]$/g, '')]),
)
const base = readFileSync(resolve(root, '.captures/ce01/secrets/web_base'), 'utf8').trim()
const artifacts = resolve(root, 'scenarios/ce-03-cdtsm-anomaly-alert/artifacts')
const alert = 'demo_checkout_latency_anomaly'
const spl =
  'index=demo_checkout region="eu-west-1"\n| timechart span=5m perc95(latency_ms) AS p95\n' +
  '| apply CDTSM p95 mode=anomaly detection_window_earliest=-8h'

const browser = await chromium.launch()
const context = await browser.newContext({
  storageState: resolve(root, '.captures/ce01/secrets/web-state.json'),
  viewport: { width: 1100, height: 800 },
  deviceScaleFactor: 2,
  ignoreHTTPSErrors: true,
  colorScheme: 'dark',
})
const page = await context.newPage()

async function dismissCallout() {
  // A one-time "AI Assistant is now active" callout can cover the end of the SPL.
  const callout = page.getByText('is now active').first()
  if (await callout.isVisible().catch(() => false)) {
    await callout.evaluate((el) => {
      let box = el
      while (box.parentElement && !box.querySelector('button')) box = box.parentElement
      box.querySelector('button')?.click()
    })
    await page.waitForTimeout(800)
  }
}

let out
if (mode === 'chart') {
  const params = new URLSearchParams({
    q: spl,
    earliest: '-24h',
    latest: 'now',
    'display.page.search.tab': 'visualizations',
    'display.general.type': 'visualizations',
    'display.visualizations.type': 'custom',
    'display.visualizations.custom.type': 'Splunk_ML_Toolkit.AnomalyViz',
  })
  await page.goto(`${base}/en-US/app/search/search?${params}`, { waitUntil: 'domcontentloaded' })
  if (page.url().includes('/account/login')) throw new Error('Splunk Web session expired; rerun splunk_web_login.mjs')
  await page.getByText('Anomaly Region').first().waitFor({ timeout: 180000 })
  await page.waitForTimeout(4000)
  out = resolve(artifacts, 'cdtsm-anomaly.png')
} else {
  await page.goto(`${base}/en-US/app/search/alerts?search=${alert}`, { waitUntil: 'domcontentloaded' })
  if (page.url().includes('/account/login')) throw new Error('Splunk Web session expired; rerun splunk_web_login.mjs')
  await page.getByRole('link', { name: alert }).first().click()
  await page.getByText('Trigger Condition').first().waitFor({ timeout: 90000 })
  // The detail page only says "Cron Schedule"; the edit dialog shows the schedule and trigger themselves.
  await page.getByRole('button', { name: 'Edit' }).or(page.locator('a.dropdown-toggle', { hasText: 'Edit' })).first().click()
  await page.getByText('Edit Alert', { exact: true }).first().click()
  await page.getByText('Trigger Conditions').first().waitFor({ timeout: 30000 })
  await page.waitForTimeout(2000)
  out = resolve(artifacts, 'splunk-alert.png')
}

await dismissCallout()
// Mask the signed-in account everywhere it appears: the login name, the header's display name, and the owner.
await page.evaluate((user) => {
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT)
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    const text = node.nodeValue
    if (!text) continue
    if (text.trim() === user) node.nodeValue = text.replace(user, 'SRE')
    if (text.includes('Splunk Administrator')) node.nodeValue = node.nodeValue.replace('Splunk Administrator', 'SRE')
    if (text.includes(`Owned by ${user}`)) node.nodeValue = node.nodeValue.replace(`Owned by ${user}`, 'Owned by SRE')
  }
}, env.SPLUNK_WEB_USER)
await page.mouse.move(0, 0)
await page.screenshot({ path: out })
console.log(`saved ${out.replace(root + '/', '')} · ${mode}`)
await browser.close()
