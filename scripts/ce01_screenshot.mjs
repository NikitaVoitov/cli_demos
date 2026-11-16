// Captures the deployed CE-01 dashboard for the Splunk Web pane (viewport only, no browser chrome).
// Usage (from apps/hub): node ../../scripts/ce01_screenshot.mjs [dashboard]
// Needs a fresh session from scripts/splunk_web_login.mjs. Prints no hostnames.
import { readFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const require = createRequire(resolve(root, 'apps/hub/package.json'))
const { chromium } = require('@playwright/test')

const name = process.argv[2] ?? 'demo_checkout_latency'
const base = readFileSync(resolve(root, '.captures/ce01/secrets/web_base'), 'utf8').trim()
const out = resolve(root, 'scenarios/ce-01-dashboard/artifacts/dashboard.png')

const browser = await chromium.launch()
const context = await browser.newContext({
  storageState: resolve(root, '.captures/ce01/secrets/web-state.json'),
  viewport: { width: 1440, height: 1220 },
  deviceScaleFactor: 1.5,
  ignoreHTTPSErrors: true,
  colorScheme: 'dark',
})
const page = await context.newPage()
await page.goto(`${base}/en-US/app/search/${name}`, { waitUntil: 'domcontentloaded' })
if (page.url().includes('/account/login')) throw new Error('Splunk Web session expired; rerun splunk_web_login.mjs')

const panels = page.locator('[aria-label^="Visualization "]')
await panels.first().waitFor({ timeout: 60000 })
await page.waitForFunction(
  () => !document.querySelector('[data-test="wait-spinner"], [data-test="viz-waiting"]'),
  null,
  { timeout: 60000 },
)
await page.waitForTimeout(4000)
const labels = await panels.evaluateAll((els) => els.map((e) => e.getAttribute('aria-label')))
await page.mouse.move(0, 0)
await page.screenshot({ path: out })
console.log(`saved ${out.replace(root + '/', '')} · ${labels.length} panels: ${labels.join(', ')}`)
await browser.close()
