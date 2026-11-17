// Captures the SO-07 Jira pane (viewport only, no browser chrome).
// Usage (from the repo root):
//   node scripts/so07_screenshot.mjs alerts          the open alerts the agent starts from (artifacts/jira-alerts.png)
//   node scripts/so07_screenshot.mjs [issue-key]     the agent's follow-up ticket (artifacts/jira-ticket.png)
// Needs a session from scripts/jira_web_login.mjs. Without a key it takes the newest follow-up ticket.
// Prints no hostnames, and shows the demo account under a placeholder name.
import { execFileSync } from 'node:child_process'
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
const site = (env.JIRA_SITE ?? '').replace(/^https:\/\//, '').replace(/\/$/, '')
if (!site.endsWith('.atlassian.net') || site === 'splunk.atlassian.net') throw new Error('JIRA_SITE must be the personal demo site')
const artifacts = resolve(root, 'scenarios/so-07-jira-alert-investigation/artifacts')

const alerts = process.argv[2] === 'alerts'
const key = alerts
  ? null
  : process.argv[2] ??
    execFileSync(resolve(root, '.captures/venv/bin/python'), [resolve(root, 'scripts/so07_jira.py'), 'latest'], { encoding: 'utf8' }).trim()
const jql = 'project = SOC AND labels = alert AND statusCategory != Done ORDER BY created ASC'
const url = alerts
  ? `https://${site}/jira/software/c/projects/SOC/issues?jql=${encodeURIComponent(jql)}`
  : `https://${site}/browse/${key}`
const out = resolve(artifacts, alerts ? 'jira-alerts.png' : 'jira-ticket.png')

const browser = await chromium.launch()
const context = await browser.newContext({
  storageState: resolve(root, '.captures/so07/secrets/jira-state.json'),
  viewport: { width: 1440, height: 1220 },
  deviceScaleFactor: 1.5,
  colorScheme: 'dark',
})
const page = await context.newPage()
await page.goto(url, { waitUntil: 'domcontentloaded' })
if (new URL(page.url()).hostname !== site) throw new Error('Jira session expired; rerun jira_web_login.mjs')

// Jira keeps polling, so "networkidle" never arrives; wait for content, then let it settle.
const ready = alerts
  ? page.getByText('Abnormal user behavior', { exact: false }).first()
  : page.locator('[data-testid="issue.views.issue-base.foundation.summary.heading"]')
await ready.waitFor({ timeout: 60000 })
await page.waitForLoadState('load').catch(() => {})
await page.waitForTimeout(3000)
await page.evaluate(() => {
  for (const el of document.querySelectorAll('span, p, a, div')) {
    if (el.childNodes.length === 1 && el.childNodes[0].nodeType === 3 && el.textContent.trim() === 'Nik') {
      el.textContent = 'Ana'
    }
  }
})
await page.mouse.move(0, 0)
await page.screenshot({ path: out })
console.log(`saved ${out.replace(root + '/', '')} · ${alerts ? 'open alerts' : `${key}: ${await ready.innerText()}`}`)
await browser.close()
