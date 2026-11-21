import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import { contentPlugin } from './plugins/content.ts'
import { n8nPreviewPlugin } from './plugins/n8nPreview.ts'

// Tests point this at tests/fixtures/scenarios; everything else uses the real catalog.
const scenarios = path.resolve(import.meta.dirname, process.env.DEMO_SCENARIOS ?? '../../scenarios')

export default defineConfig({
  plugins: [contentPlugin(scenarios), n8nPreviewPlugin(scenarios), react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(import.meta.dirname, './src'),
      '@scenarios': scenarios,
    },
  },
  server: {
    port: 5173,
    fs: { allow: [import.meta.dirname, scenarios] },
  },
  build: {
    target: 'baseline-widely-available',
    sourcemap: false,
    assetsInlineLimit: 0,
    rolldownOptions: {
      output: {
        advancedChunks: {
          groups: [
            { name: 'react', test: /node_modules[\\/](react|react-dom|scheduler)[\\/]/ },
            { name: 'player', test: /node_modules[\\/]asciinema-player[\\/]/ },
          ],
        },
      },
    },
  },
})
