# Headless Splunk Demos Hub

Vite + React catalog for the captured agentic CLI demos in `../../scenarios`.

## Commands

```sh
npm install
npm run dev
npm run lint
npm run build
npm run deploy:dry
npm run deploy
```

`npm run deploy` builds the catalog and deploys `dist/` as a static-only Cloudflare Worker. The SPA fallback is configured in `wrangler.jsonc`; there are no runtime bindings or secrets.

Current Workers deployment: [headless-splunk-demos.liveq.workers.dev](https://headless-splunk-demos.liveq.workers.dev)
