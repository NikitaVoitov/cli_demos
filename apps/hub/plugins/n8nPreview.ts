import { existsSync, readdirSync, readFileSync, rmSync } from 'node:fs'
import path from 'node:path'
import type { Connect, Plugin } from 'vite'
import { parse } from 'yaml'

const BASE = '/n8n-preview/'

/**
 * The static n8n canvas (scripts/n8n_preview_snapshot.py) is plain files in public/n8n-preview/. In production,
 * Workers static assets serve `workflows/demo.html` at `/n8n-preview/workflows/demo`; the dev and preview servers
 * get the same mapping here, and the extensionless API responses get a JSON content type.
 */
function serveSnapshot(): Connect.NextHandleFunction {
  return (req, res, next) => {
    const url = req.url ?? ''
    if (!url.startsWith(BASE)) return next()
    const pathname = url.split('?')[0]
    if (pathname === `${BASE}workflows/demo`) req.url = `${BASE}workflows/demo.html`
    else if (pathname.startsWith(`${BASE}rest/`)) res.setHeader('Content-Type', 'application/json')
    next()
  }
}

/** Fails the build when a scenario draws a workflow the snapshot can't render. Returns whether any scenario does. */
function checkSnapshot(scenariosDir: string, publicDir: string) {
  const manifestFile = path.join(publicDir, 'n8n-preview/manifest.json')
  const rebuild = 'run `.captures/venv/bin/python scripts/n8n_preview_snapshot.py`'
  let used = false
  for (const dir of readdirSync(scenariosDir)) {
    const scenarioFile = path.join(scenariosDir, dir, 'scenario.yaml')
    if (!existsSync(scenarioFile)) continue
    const workflow = parse(readFileSync(scenarioFile, 'utf8'))?.workflow
    if (!workflow) continue
    used = true
    if (!existsSync(manifestFile)) throw new Error(`${dir} draws an n8n workflow but public/n8n-preview is missing; ${rebuild}`)
    const manifest = JSON.parse(readFileSync(manifestFile, 'utf8')) as { nodeTypes: string[] }
    const nodes = JSON.parse(readFileSync(path.join(scenariosDir, dir, workflow.src), 'utf8')).nodes as { type: string }[]
    const missing = [...new Set(nodes.map((n) => n.type))].filter((type) => !manifest.nodeTypes.includes(type))
    if (missing.length) throw new Error(`${dir} uses node types the n8n snapshot lacks (${missing.join(', ')}); ${rebuild}`)
  }
  return used
}

export function n8nPreviewPlugin(scenariosDir: string): Plugin {
  let publicDir = ''
  let outDir = ''
  let used = false
  return {
    name: 'n8n-preview',
    configResolved(config) {
      publicDir = config.publicDir
      outDir = path.resolve(config.root, config.build.outDir)
    },
    buildStart() {
      used = checkSnapshot(scenariosDir, publicDir)
    },
    // n8n's editor is published only once a demo draws a workflow.
    closeBundle() {
      if (!used) rmSync(path.join(outDir, 'n8n-preview'), { recursive: true, force: true })
    },
    configureServer(server) {
      server.middlewares.use(serveSnapshot())
    },
    configurePreviewServer(server) {
      server.middlewares.use(serveSnapshot())
    },
  }
}
