import { readFile } from 'node:fs/promises'
import { marked } from 'marked'
import type { Plugin } from 'vite'
import { parse } from 'yaml'

/** Scenario files are authored as YAML and Markdown and compiled to plain modules at build time. */
export function contentPlugin(contentDir: string): Plugin {
  return {
    name: 'demo-content',
    enforce: 'pre',
    configureServer(server) {
      // The scenarios live outside the app root, which Vite doesn't watch by default.
      server.watcher.add(contentDir)
      server.watcher.on('change', (file) => {
        if (!file.startsWith(contentDir)) return
        for (const mod of server.moduleGraph.getModulesByFile(file) ?? []) server.moduleGraph.invalidateModule(mod)
        server.ws.send({ type: 'full-reload' })
      })
    },
    async load(id) {
      if (id.includes('?')) return null
      if (id.endsWith('.yaml') || id.endsWith('.yml')) {
        const data = parse(await readFile(id, 'utf8'))
        return { code: `export default ${JSON.stringify(data)}`, map: null }
      }
      if (id.endsWith('.md')) {
        const html = await marked.parse(await readFile(id, 'utf8'))
        return { code: `export default ${JSON.stringify(html)}`, map: null }
      }
      return null
    },
  }
}
