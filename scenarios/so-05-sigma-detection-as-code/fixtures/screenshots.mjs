// SO-05 screenshots, taken right after a take (before the next reset), from the repo root:
//   node scenarios/so-05-sigma-detection-as-code/fixtures/screenshots.mjs github <pr> <failed-run> <green-run> <deploy-run>
//   node scenarios/so-05-sigma-detection-as-code/fixtures/screenshots.mjs es
// `github` shoots the validate run that failed on noise, CI's report on the pull request with the AI triage, the green
// validate run after tuning, and the deploy run (run IDs: `gh run list`). `es` shoots ES Content management and the
// detection's editor with its search. GitHub needs `node scripts/github_web_login.mjs` once; ES uses the Splunk Web
// session that scripts/splunk_web_login.mjs saves. The repo owner is rewritten in the page and avatars are hidden
// before each shot, because a screenshot can't be sanitized afterwards; a page that still shows the owner is refused.
import { readFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const root = resolve(here, '../../..')
const artifacts = resolve(here, '../artifacts')
const { chromium } = createRequire(resolve(root, 'apps/hub/package.json'))('@playwright/test')
const env = Object.fromEntries(
  readFileSync(resolve(root, '.env'), 'utf8')
    .split('\n')
    .filter((l) => l.includes('='))
    .map((l) => [l.slice(0, l.indexOf('=')), l.slice(l.indexOf('=') + 1).trim().replace(/^['"]|['"]$/g, '')]),
)
const repo = env.DAC_DEMO_REPO
const owner = repo.split('/')[0]
// Same as pipeline/sanitize.py: a same-length cut of this name.
const display = 'acme-soc-engineering'.repeat(3).slice(0, owner.length)
const [cmd, ...args] = process.argv.slice(2)
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

async function scrub(page) {
  await page.evaluate(
    ([from, to]) => {
      const fix = () => {
        const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT)
        for (let n = walker.nextNode(); n; n = walker.nextNode()) if (n.nodeValue.includes(from)) n.nodeValue = n.nodeValue.split(from).join(to)
        for (const el of document.querySelectorAll('[title],[aria-label]'))
          for (const a of ['title', 'aria-label']) if (el.getAttribute(a)?.includes(from)) el.setAttribute(a, el.getAttribute(a).split(from).join(to))
      }
      fix()
      // GitHub renders the sticky PR header only after scrolling, so keep scrubbing new nodes.
      new MutationObserver(fix).observe(document.body, { childList: true, subtree: true, characterData: true })
      const style = document.createElement('style')
      style.textContent =
        'img.avatar, img.avatar-user, img[src*="avatars.githubusercontent"], .AppHeader-user, [data-testid="github-avatar"] { visibility: hidden !important; }'
      document.head.appendChild(style)
    },
    [owner, display],
  )
}

async function shoot(page, name, fullPage = false) {
  await sleep(1500)
  if (await page.evaluate((from) => document.body.innerText.includes(from), owner))
    throw new Error(`repo owner still visible on the page; not writing ${name}`)
  await page.screenshot({ path: resolve(artifacts, name), fullPage })
  console.log(`wrote artifacts/${name}`)
}

// A validate or deploy run, the whole page: the job graph and the summary CI wrote below it. The hub's pane shows the
// top and scrolls the rest in fullscreen.
async function run(page, id, name) {
  await page.goto(`https://github.com/${repo}/actions/runs/${id}`, { waitUntil: 'domcontentloaded' })
  await page.getByText(/summary$/).first().waitFor({ timeout: 30000 })
  // The sidebar loads its job list after the page; wait until every job is listed there, not just in the graph.
  await page.waitForLoadState('networkidle').catch(() => {})
  await page.waitForFunction(() => document.querySelectorAll('a[href*="/job/"]').length >= 2, null, { timeout: 30000 }).catch(() => {})
  await sleep(2000)
  await scrub(page)
  await shoot(page, name, true)
}

const browser = await chromium.launch()
if (cmd === 'github' && args.length === 4) {
  const [pr, failed, green, deploy] = args
  const context = await browser.newContext({
    storageState: resolve(root, '.captures/so05/secrets/github-state.json'),
    viewport: { width: 1280, height: 900 },
    colorScheme: 'dark',
  })
  const page = await context.newPage()
  await run(page, failed, 'ci-run-1.png')
  await page.goto(`https://github.com/${repo}/pull/${pr}`, { waitUntil: 'domcontentloaded' })
  const report = page.locator('.timeline-comment, .TimelineItem').filter({ hasText: 'AI triage of the noise' }).first()
  await report.waitFor({ timeout: 30000 })
  await scrub(page)
  // Frame the noise table, the AI triage, and the verdict rather than the tests table above them.
  await report.locator('h2').filter({ hasText: 'Noise:' }).first().evaluate((el) => el.scrollIntoView({ block: 'start' }))
  await page.evaluate(() => window.scrollBy(0, -90))
  await shoot(page, 'pr-report.png')
  await run(page, green, 'ci-run-2.png')
  await run(page, deploy, 'deploy-run.png')
} else if (cmd === 'es') {
  const base = readFileSync(resolve(root, '.captures/ce01/secrets/web_base'), 'utf8').trim()
  const context = await browser.newContext({
    storageState: resolve(root, '.captures/ce01/secrets/web-state.json'),
    viewport: { width: 1280, height: 900 },
    ignoreHTTPSErrors: true,
  })
  const page = await context.newPage()
  await page.goto(`${base}/en-US/app/SplunkEnterpriseSecuritySuite/ess_content_management`, { waitUntil: 'domcontentloaded' })
  const search = page.locator('input[type="search"], input[placeholder*="earch" i], input[placeholder*="ilter" i]').first()
  await search.waitFor({ timeout: 60000 })
  await sleep(5000)
  await search.fill('comsvcs')
  await page.keyboard.press('Enter')
  await page.getByText('ACME SOC - Process Memory Dump Via Comsvcs DLL').first().waitFor({ timeout: 60000 })
  await sleep(3000)
  await page.screenshot({ path: resolve(artifacts, 'es-content.png') })
  console.log('wrote artifacts/es-content.png')
  const name = 'ACME SOC - Process Memory Dump Via Comsvcs DLL - Rule'
  await page.goto(
    `${base}/en-US/app/SplunkEnterpriseSecuritySuite/correlation_search_edit?search=${encodeURIComponent(name)}&app_name=DA-ESS-DaC-Demo`,
    { waitUntil: 'domcontentloaded' },
  )
  const spl = page.getByText('security_content_summariesonly').first()
  await spl.waitFor({ timeout: 90000 })
  // The editor is wider than the hub's pane: zoom out to Content management's scale and bring the search into view.
  await page.setViewportSize({ width: 1600, height: 1125 })
  await sleep(2000)
  await spl.evaluate((el) => el.scrollIntoView({ block: 'center' }))
  await sleep(1500)
  await page.screenshot({ path: resolve(artifacts, 'es-spl.png') })
  console.log('wrote artifacts/es-spl.png')
} else {
  console.error('usage: screenshots.mjs github <pr> <failed-run> <green-run> <deploy-run> | es')
  process.exitCode = 2
}
await browser.close()
