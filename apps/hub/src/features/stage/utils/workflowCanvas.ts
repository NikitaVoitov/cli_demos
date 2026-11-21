import type { DemoWorkflow, WorkflowStep } from '@/types/content.types'

/** Where the hub serves the static n8n canvas; must match `basePath` in recorder/n8n-preview.yaml. */
export const N8N_PREVIEW_BASE = '/n8n-preview/'
/** n8n's read-only demo page, forced dark, with node details disabled. */
export const N8N_CANVAS_URL = `${N8N_PREVIEW_BASE}workflows/demo?theme=dark&canOpenNDV=false`

export interface CanvasNote {
  nodeId: string
  text: string
}

export interface CanvasState {
  done: Map<string, WorkflowStep['status']>
  running: string[]
  /** Notes whose step has started; each shows an info icon on its node and opens on hover. */
  notes: CanvasNote[]
}

export function canvasStateAt(workflow: DemoWorkflow, time: number): CanvasState {
  const done = new Map<string, WorkflowStep['status']>()
  const running: string[] = []
  const notes: CanvasNote[] = []
  for (const step of [...workflow.steps].sort((a, b) => a.from - b.from)) {
    if (step.from > time) break
    if (time >= step.until) done.set(step.nodeId, step.status)
    else running.push(step.nodeId)
    if (step.callout) notes.push({ nodeId: step.nodeId, text: step.callout })
  }
  return { done, running, notes }
}

/** SDS values the canvas styles use, read from the hub's own theme so the iframe never hard-codes a color. */
export interface CanvasTokens {
  primary: string
  primaryForeground: string
  accent: string
  success: string
  error: string
  card: string
  textSecondary: string
}

export function readCanvasTokens(root: Element = document.documentElement): CanvasTokens {
  const style = getComputedStyle(root)
  const token = (name: string) => style.getPropertyValue(name).trim()
  return {
    primary: token('--action-primary'),
    primaryForeground: token('--action-primary-foreground'),
    accent: token('--text-accent'),
    success: token('--status-success'),
    error: token('--status-error'),
    card: token('--surface-card'),
    textSecondary: token('--text-secondary'),
  }
}

const node = (id: string) => `.vue-flow__node[data-id="${id}"]`
const box = (id: string) => `${node(id)} :is([data-test-id="canvas-default-node"], [data-test-id="canvas-trigger-node"])`
// The pointer from a note card to its node; n8n draws nothing in this element's pseudo-elements.
const pointer = (id: string) => `${node(id)} [data-test-id="canvas-node"]::after`
// The canvas labels an edge "[source/outputs/main/0][target/inputs/main/0]".
const edge = ([from, to]: [string, string]) =>
  `.vue-flow__edge[data-id^="[${from}/"][data-id*="][${to}/"] path.vue-flow__edge-path`
const tint = (color: string, percent: number) => `color-mix(in oklab, ${color} ${percent}%, transparent)`
/** Lengths in screen pixels, whatever the canvas zoom (`--demo-zoom` is set by the pane). */
const px = (n: number) => `calc(${n}px / var(--demo-zoom, 1))`
const unzoom = 'scale(calc(1 / var(--demo-zoom, 1)))'
const NOTE_GAP = 10
const NOTE_MAX_WIDTH = 240

/** Styles that hold for the whole demo: SDS sticky notes, no credential warnings, and the animations. */
function baseRules(t: CanvasTokens) {
  return [
    `[data-test-id="node-issues"] { display: none !important; }`,
    `[data-test-id="sticky"] { background: ${t.card} !important; border: 1px solid ${tint(t.primary, 70)} !important; border-radius: 6px !important; }`,
    `[data-test-id="sticky"] :is(h1, h2, h3, h4) { color: ${t.accent} !important; }`,
    `[data-test-id="sticky"] :is(p, li) { color: ${t.textSecondary} !important; }`,
    `@keyframes demo-pulse { 0%, 100% { box-shadow: 0 0 0 2px ${t.primary}, 0 0 10px 2px ${tint(t.primary, 45)}; } 50% { box-shadow: 0 0 0 2px ${t.primary}, 0 0 26px 8px ${tint(t.primary, 70)}; } }`,
    `@keyframes demo-flow { to { stroke-dashoffset: -24; } }`,
    `@media (prefers-reduced-motion: reduce) { * { animation-duration: 0s !important; animation-iteration-count: 1 !important; } }`,
  ]
}

/** A note is an info icon on its node's corner; hovering the node shows the card with a pointer to the node. */
function noteRules(note: CanvasNote, t: CanvasTokens) {
  const { nodeId: id, text } = note
  return [
    `${node(id)}::before { content: "i"; position: absolute; top: 0; right: 0; width: 18px; height: 18px;
      transform: translate(50%, -50%) ${unzoom}; border-radius: 50%; background: ${t.primary}; color: ${t.primaryForeground};
      font: 800 12px/18px Inter, system-ui, sans-serif; text-align: center; box-shadow: 0 0 0 2px ${t.card}; z-index: 11; }`,
    `${node(id)}::after { content: ${JSON.stringify(text)}; display: none; position: absolute; left: 50%; bottom: calc(100% + ${px(NOTE_GAP)});
      transform: translateX(-50%) ${unzoom}; transform-origin: 50% 100%; width: max-content; max-width: ${NOTE_MAX_WIDTH}px;
      padding: 5px 9px; border-radius: 4px; background: ${t.card}; border: 1px solid ${tint(t.primary, 70)}; color: ${t.accent};
      font: 600 12px/1.35 Inter, system-ui, sans-serif; text-align: center; box-shadow: 0 6px 18px rgb(0 0 0 / 50%);
      pointer-events: none; z-index: 12; }`,
    `${pointer(id)} { content: ""; display: none; position: absolute; left: 50%; bottom: 100%; width: 0; height: 0;
      border-left: 7px solid transparent; border-right: 7px solid transparent; border-top: ${NOTE_GAP}px solid ${tint(t.primary, 70)};
      transform: translateX(-50%) ${unzoom}; transform-origin: 50% 100%; pointer-events: none; z-index: 12; }`,
    `${node(id)}:hover::after, ${node(id)}:hover [data-test-id="canvas-node"]::after { display: block; }`,
  ]
}

/** Where the hovered card sits: leaning away from a canvas edge, or below its node near the top (calloutPlacement). */
function placementRules(t: CanvasTokens) {
  const card = '.vue-flow__node:hover::after'
  const tip = '.vue-flow__node:hover [data-test-id="canvas-node"]::after'
  return [
    `:root[data-demo-callout~="start"] ${card} { left: 0; transform: ${unzoom}; transform-origin: 0 100%; }`,
    `:root[data-demo-callout~="end"] ${card} { left: auto; right: 0; transform: ${unzoom}; transform-origin: 100% 100%; }`,
    `:root[data-demo-callout~="below"] ${card} { bottom: auto; top: calc(100% + ${px(NOTE_GAP)}); }`,
    `:root[data-demo-callout="below"] ${card} { transform-origin: 50% 0; }`,
    `:root[data-demo-callout~="below"][data-demo-callout~="start"] ${card} { transform-origin: 0 0; }`,
    `:root[data-demo-callout~="below"][data-demo-callout~="end"] ${card} { transform-origin: 100% 0; }`,
    `:root[data-demo-callout~="below"] ${tip} { bottom: auto; top: 100%; border-top: 0; border-bottom: ${NOTE_GAP}px solid ${tint(t.primary, 70)}; transform-origin: 50% 0; }`,
  ]
}

/**
 * One stylesheet for one moment of the demo. Rules match n8n's node and edge attributes, so they keep applying
 * when the canvas pans, zooms, or re-renders.
 */
export function canvasCss(workflow: DemoWorkflow, state: CanvasState, t: CanvasTokens) {
  const rules = baseRules(t)
  for (const [id, status] of state.done) {
    const color = status === 'error' ? t.error : t.success
    rules.push(`${box(id)} { box-shadow: 0 0 0 2px ${color}, 0 0 14px 2px ${tint(color, 40)} !important; }`)
  }
  for (const id of state.running) rules.push(`${box(id)} { animation: demo-pulse 1.2s ease-in-out infinite !important; }`)
  for (const pair of workflow.edges) {
    const [from, to] = pair
    if (state.done.get(from) === 'success' && state.done.has(to)) {
      rules.push(`${edge(pair)} { stroke: ${t.success} !important; stroke-width: 2.5px !important; }`)
    } else if (state.done.get(from) === 'success' && state.running.includes(to)) {
      rules.push(`${edge(pair)} { stroke: ${t.primary} !important; stroke-width: 2.5px !important; stroke-dasharray: 8 4; animation: demo-flow 0.6s linear infinite; }`)
    }
  }
  for (const note of state.notes) rules.push(...noteRules(note, t))
  rules.push(...placementRules(t))
  return rules.join('\n')
}

/** The note whose node the pointer is over, if any. */
export function hoveredNote(doc: Document, state: CanvasState) {
  return state.notes.find((note) => doc.querySelector(node(note.nodeId))?.matches(':hover'))
}

/**
 * Cards are drawn by CSS, which can't see the canvas edges, so the pane measures the node and says which way the
 * card must lean to stay on screen: `start` or `end` near the left or right edge, `below` near the top.
 */
export function calloutPlacement(doc: Document, note: CanvasNote | undefined) {
  const wrapper = note && doc.querySelector(node(note.nodeId))
  if (!wrapper) return ''
  const r = wrapper.getBoundingClientRect()
  const width = Math.min(NOTE_MAX_WIDTH, note.text.length * 7 + 20)
  const height = 44 + NOTE_GAP
  const view = doc.documentElement.clientWidth
  const center = r.left + r.width / 2
  const lean = center + width / 2 > view - 8 ? 'end' : center - width / 2 < 8 ? 'start' : ''
  const below = r.top - height < 8 ? 'below' : ''
  return [lean, below].filter(Boolean).join(' ')
}

/** The canvas zoom, from the transform n8n's canvas library puts on its viewport. */
export function canvasZoom(doc: Document) {
  const transform = doc.querySelector<HTMLElement>('.vue-flow__transformationpane')?.style.transform ?? ''
  return Number(/scale\(([\d.]+)\)/.exec(transform)?.[1] ?? 1) || 1
}
