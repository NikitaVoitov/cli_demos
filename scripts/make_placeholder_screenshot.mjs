// Render a labeled stand-in for dashboard.png until the real post-deploy Splunk Web screenshot exists.
//   node scripts/make_placeholder_screenshot.mjs   (uses apps/hub's Playwright)
import { createRequire } from 'node:module'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)))
const require = createRequire(path.join(root, 'apps/hub/package.json'))
const { chromium } = require('@playwright/test')

const line = [40, 38, 42, 35, 39, 36, 30, 37, 12, 33, 36, 31, 38, 22, 36, 34, 26, 37, 33, 39, 35]
  .map((y, i) => `${i * 10},${y}`)
  .join(' ')
const bars = [52, 48, 36, 34, 31, 27, 24, 16, 12, 9]
  .map((h, i) => `<rect x="${i * 20 + 3}" y="${60 - h}" width="14" height="${h}" fill="#1d6fa5"/>`)
  .join('')

const html = `<!doctype html><html><body style="margin:0;font-family:Inter,-apple-system,sans-serif">
<div style="width:600px;height:508px;background:#f3f4f6;color:#1f2430;padding:12px;box-sizing:border-box;display:grid;
  grid-template-columns:1fr 1fr;grid-template-rows:24px 104px 1fr;gap:10px;position:relative">
  <h4 style="grid-column:1/-1;margin:0;font-size:15px">Checkout latency</h4>
  <div style="background:#fff;border-radius:4px;padding:10px;font-size:12px;color:#4b5263">p95 latency
    <div style="font-size:36px;font-weight:700;color:#2a2f3c;text-align:center;margin-top:12px">812 <small style="font-size:18px">ms</small></div></div>
  <div style="background:#fff;border-radius:4px;padding:10px;font-size:12px;color:#4b5263">5xx rate
    <div style="font-size:36px;font-weight:700;color:#2a2f3c;text-align:center;margin-top:12px">0.4<small style="font-size:18px">%</small></div></div>
  <div style="background:#fff;border-radius:4px;padding:10px;font-size:12px;color:#4b5263;position:relative">Latency over time
    <svg viewBox="0 0 200 60" preserveAspectRatio="none" style="position:absolute;inset:30px 10px 10px;width:calc(100% - 20px);height:calc(100% - 40px)">
    <polyline fill="none" stroke="#1d6fa5" stroke-width="1.4" points="${line}"/></svg></div>
  <div style="background:#fff;border-radius:4px;padding:10px;font-size:12px;color:#4b5263;position:relative">Latency by region
    <svg viewBox="0 0 200 60" preserveAspectRatio="none" style="position:absolute;inset:30px 10px 10px;width:calc(100% - 20px);height:calc(100% - 40px)">${bars}</svg></div>
  <div style="position:absolute;left:12px;bottom:12px;background:#1f2430;color:#ffd58f;font-size:12px;font-weight:600;
    padding:4px 8px;border-radius:4px">Placeholder · real Splunk Web screenshot pending</div>
</div></body></html>`

const browser = await chromium.launch()
// Same aspect as the Splunk Web pane at 1440 px (~455x386); capture the real screenshot at this viewport too.
const page = await browser.newPage({ viewport: { width: 600, height: 508 }, deviceScaleFactor: 2 })
await page.setContent(html)
const out = path.join(root, 'scenarios/ce-01-dashboard/artifacts/dashboard.png')
await page.screenshot({ path: out })
await browser.close()
console.log(`wrote ${out}`)
