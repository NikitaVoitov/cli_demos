// Checks the n8n canvas pane against the workflow-canvas fixture, by DOM state rather than wall-clock timing:
// the canvas loads, each chapter shows the right nodes running or done, info icons appear as steps start and open
// their note on hover, the gate and Decline behave, and the highlights survive zoom.
//
//   DEMO_SCENARIOS=tests/fixtures/scenarios npm run build && npx vite preview --port 4173 &
//   node scripts/check-workflow-pane.mjs http://localhost:4173 [screenshot-dir]
import { chromium } from '@playwright/test'

const base = process.argv[2] ?? 'http://localhost:4173'
const shots = process.argv[3]
const failures = []
const check = (ok, message) => {
  console.log(`${ok ? '✓' : '✗'} ${message}`)
  if (!ok) failures.push(message)
}

const browser = await chromium.launch()
const page = await (await browser.newContext({ viewport: { width: 1440, height: 900 } })).newPage()
page.on('pageerror', (error) => failures.push(`page error: ${error.message}`))

async function canvas() {
  await page.locator('iframe[title^="n8n workflow"]').waitFor({ timeout: 30_000 })
  const frame = page.frameLocator('iframe[title^="n8n workflow"]')
  await frame.locator('.vue-flow__node[data-id="n-slack"]').waitFor({ timeout: 30_000 })
  return page.frames().find((f) => f.url().includes('/n8n-preview/workflows/demo'))
}

/** What the canvas renders for each node: pulsing, a glow ring, or nothing; an info icon; an open note card. */
const nodeStates = (frame) =>
  frame.evaluate(() => {
    const out = {}
    for (const wrapper of document.querySelectorAll('.vue-flow__node')) {
      const box = wrapper.querySelector('[data-test-id="canvas-default-node"], [data-test-id="canvas-trigger-node"]')
      if (!box) continue
      const style = getComputedStyle(box)
      const card = getComputedStyle(wrapper, '::after')
      const tip = getComputedStyle(wrapper.querySelector('[data-test-id="canvas-node"]'), '::after')
      out[wrapper.dataset.id] = {
        state: style.animationName === 'demo-pulse' ? 'running' : style.boxShadow !== 'none' ? 'done' : 'idle',
        info: getComputedStyle(wrapper, '::before').content === '"i"',
        note: card.display !== 'none' && card.content !== 'none' ? JSON.parse(card.content) : undefined,
        pointer: tip.display !== 'none' && tip.content !== 'none',
      }
    }
    return out
  })
const openNotes = (states) => Object.entries(states).filter(([, s]) => s.note).map(([id]) => id)
const chapter = (label) => page.locator('nav[aria-label="Demo chapters"] button', { hasText: label })
const settle = () => page.waitForTimeout(600)
const badge = (text) => page.locator('span', { hasText: new RegExp(`^${text}$`) })

// 1. The canvas loads with the workflow and nothing lit or annotated.
await page.goto(base)
let frame = await canvas()
await settle()
let states = await nodeStates(frame)
check(Object.keys(states).length === 5, `canvas shows the 5 workflow nodes (got ${Object.keys(states).length})`)
check(Object.values(states).every((s) => s.state === 'idle' && !s.info && !s.note), 'before the run nothing is lit and no info icon shows')

// 2. Play from the approval chapter until the gate stops the player.
await chapter('Approval').click()
await page.locator('.ap-playback-button').click()
await page.getByRole('button', { name: 'Approve' }).waitFor({ timeout: 90_000 })
states = await nodeStates(frame)
check(Object.values(states).every((s) => s.state === 'idle'), 'at the gate the workflow has not run')

// 3. Approve, then seek into the containment chapter: the trigger runs.
await page.getByRole('button', { name: 'Approve' }).click()
await page.locator('.ap-playback-button').click()
await chapter('Containment').click()
await settle()
states = await nodeStates(frame)
check(states['n-trigger']?.state === 'running', 'at the containment chapter the trigger is running')
check(states['n-slack']?.state === 'idle', 'later nodes are still idle')
check(await badge('Running: Start containment').isVisible(), 'the pane header names the running node')

// 4. Zoom the canvas twice: the highlight stays and note cards get the new scale.
const zoomBefore = await frame.evaluate(() => document.documentElement.style.getPropertyValue('--demo-zoom'))
await frame.click('[data-test-id="zoom-in-button"]')
await frame.click('[data-test-id="zoom-in-button"]')
await page.waitForTimeout(500)
states = await nodeStates(frame)
const zoomAfter = await frame.evaluate(() => document.documentElement.style.getPropertyValue('--demo-zoom'))
check(states['n-trigger']?.state === 'running', 'the running highlight survives zooming in')
check(Number(zoomAfter) > Number(zoomBefore), `note scale follows the zoom (${zoomBefore} → ${zoomAfter})`)
await frame.click('[data-test-id="zoom-to-fit"]')

// 5. The verify chapter: every node is done and notes wait for a hover.
await chapter('Verify').click()
await settle()
await page.mouse.move(5, 5)
states = await nodeStates(frame)
const path = ['n-trigger', 'n-purge', 'n-block', 'n-merge', 'n-slack']
check(path.every((id) => states[id]?.state === 'done'), 'every node is done after containment')
check(['n-purge', 'n-block', 'n-slack'].every((id) => states[id]?.info), 'every note has an info icon on its node')
check(openNotes(states).length === 0, `no note opens on its own (open: ${openNotes(states).join() || 'none'})`)

// 6. Hovering a node opens its note, with a pointer to that node; moving away closes it.
const nodeCenter = async (id) => {
  const r = await frame.locator(`.vue-flow__node[data-id="${id}"]`).boundingBox()
  return { x: r.x + r.width / 2, y: r.y + r.height / 2 }
}
const ret = await nodeCenter('n-slack')
await page.mouse.move(ret.x, ret.y)
await page.waitForTimeout(300)
states = await nodeStates(frame)
check(openNotes(states).join() === 'n-slack', `hovering Notify analyst in Slack opens its note (open: ${openNotes(states).join() || 'none'})`)
check(states['n-slack']?.note === 'Tells the analyst containment is done', 'the note text matches content.yaml')
check(states['n-slack']?.pointer, 'the open card points at its node')
if (shots) await page.screenshot({ path: `${shots}/workflow-pane-hover.png` })
const purge = await nodeCenter('n-purge')
await page.mouse.move(purge.x, purge.y)
await page.waitForTimeout(300)
states = await nodeStates(frame)
check(openNotes(states).join() === 'n-purge', 'hovering another node swaps the note')
await page.mouse.move(5, 5)
await page.waitForTimeout(300)
states = await nodeStates(frame)
check(openNotes(states).length === 0, 'moving away closes the note')

// 7. A fresh visit declined at the gate: nothing runs and the header says so.
await page.goto(base)
frame = await canvas()
await chapter('Approval').click()
await page.locator('.ap-playback-button').click()
await page.getByRole('button', { name: 'Decline' }).click({ timeout: 90_000 })
await settle()
states = await nodeStates(frame)
check(Object.values(states).every((s) => s.state === 'idle'), 'after Decline no node runs')
check(await badge('Never ran').isVisible(), 'the pane header says the workflow never ran')

await browser.close()
if (failures.length) {
  console.error(`\n${failures.length} check(s) failed`)
  process.exit(1)
}
console.log('\nall workflow pane checks passed')
