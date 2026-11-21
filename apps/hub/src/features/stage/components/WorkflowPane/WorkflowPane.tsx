import { useEffect, useMemo, useRef, useState } from 'react'
import { usePlaybackStore } from '@/store/usePlaybackStore'
import type { DemoEntry } from '@/types/content.types'
import { PaneFrame } from '../TerminalPane/TerminalPane'
import {
  calloutPlacement,
  canvasCss,
  canvasStateAt,
  canvasZoom,
  hoveredNote,
  N8N_CANVAS_URL,
  readCanvasTokens,
} from '../../utils/workflowCanvas'

/** n8n's editor is about 12 MB; past this, the pane says the canvas is unavailable instead of spinning. */
const READY_TIMEOUT_MS = 15_000
/** How often the pane follows the canvas zoom and which note the pointer is over. */
const POLL_MS = 150
const STYLE_ID = 'demo-canvas-state'

/**
 * The real n8n canvas, served as static files from the hub's own origin (scripts/n8n_preview_snapshot.py), with
 * the demo's workflow loaded through n8n's `openWorkflow` message. Highlights and notes are one stylesheet the
 * pane writes into the canvas as the player's clock moves; n8n itself never runs anything.
 */
export function WorkflowPane({ entry }: { entry: DemoEntry }) {
  const workflow = entry.workflow!
  const frameRef = useRef<HTMLIFrameElement>(null)
  const [phase, setPhase] = useState<'loading' | 'ready' | 'failed'>('loading')
  const time = usePlaybackStore((state) => state.time)
  const status = usePlaybackStore((state) => state.status)
  const decision = usePlaybackStore((state) => state.decision)

  // At the end every step is done, wherever the clock stopped.
  const state = useMemo(() => canvasStateAt(workflow, status === 'ended' ? Infinity : time), [workflow, time, status])
  const css = useMemo(() => canvasCss(workflow, state, readCanvasTokens()), [workflow, state])
  const runningNames = workflow.steps.filter((s) => state.running.includes(s.nodeId)).map((s) => s.node)

  useEffect(() => {
    const onMessage = (event: MessageEvent) => {
      const frame = frameRef.current
      if (!frame || event.source !== frame.contentWindow || typeof event.data !== 'string') return
      let message: { command?: string }
      try {
        message = JSON.parse(event.data)
      } catch {
        return
      }
      if (message.command !== 'n8nReady') return
      frame.contentWindow!.postMessage(
        JSON.stringify({ command: 'openWorkflow', workflow: workflow.json, canOpenNDV: false, suppressNotifications: true }),
        window.location.origin,
      )
      setPhase('ready')
    }
    window.addEventListener('message', onMessage)
    const timer = window.setTimeout(() => setPhase((p) => (p === 'loading' ? 'failed' : p)), READY_TIMEOUT_MS)
    return () => {
      window.removeEventListener('message', onMessage)
      window.clearTimeout(timer)
    }
  }, [workflow])

  useEffect(() => {
    const doc = frameRef.current?.contentDocument
    if (phase !== 'ready' || !doc) return
    let style = doc.getElementById(STYLE_ID)
    if (!style) {
      style = doc.createElement('style')
      style.id = STYLE_ID
      doc.head.append(style)
    }
    if (style.textContent !== css) style.textContent = css
  }, [phase, css])

  // Note cards keep their screen size at any zoom and lean away from whichever canvas edge their node is near.
  const stateRef = useRef(state)
  useEffect(() => {
    stateRef.current = state
  }, [state])
  useEffect(() => {
    if (phase !== 'ready') return
    const id = window.setInterval(() => {
      const doc = frameRef.current?.contentDocument
      if (!doc) return
      const root = doc.documentElement
      root.style.setProperty('--demo-zoom', String(canvasZoom(doc)))
      const placement = calloutPlacement(doc, hoveredNote(doc, stateRef.current))
      if (root.dataset.demoCallout !== placement) root.dataset.demoCallout = placement
    }, POLL_MS)
    return () => window.clearInterval(id)
  }, [phase])

  const declined = decision === 'declined'
  const now = declined ? 'Never ran' : runningNames.length ? `Running: ${runningNames.join(', ')}` : undefined

  return (
    <PaneFrame
      title={workflow.title}
      aside={
        <>
          {now && (
            <span className="shrink-0 rounded-sm bg-primary px-1.5 py-px text-[10px] font-semibold text-primary-foreground">
              {now}
            </span>
          )}
          <span className="truncate">{workflow.object}</span>
        </>
      }
      focused={runningNames.length > 0}
      className="min-[1100px]:h-[414px]"
    >
      <div className="relative aspect-[6/5] flex-1 overflow-hidden min-[1100px]:aspect-auto">
        <iframe
          ref={frameRef}
          src={N8N_CANVAS_URL}
          title={`${workflow.title} workflow: ${workflow.object}`}
          aria-describedby={`${entry.id}-workflow-alt`}
          className="absolute inset-0 size-full border-0"
        />
        <p id={`${entry.id}-workflow-alt`} className="sr-only">
          {workflow.alt}
        </p>
        <p role="status" className="sr-only">
          {now ?? ''}
        </p>
        {phase !== 'ready' && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-terminal px-4 text-center text-body-sm text-muted-foreground">
            {phase === 'loading' ? (
              <>
                <span aria-hidden className="size-6 animate-spin rounded-full border-[2.5px] border-border-strong border-t-foreground" />
                Loading the n8n workflow
              </>
            ) : (
              'The n8n workflow canvas did not load. The terminal and the Transcript tab show the full run.'
            )}
          </div>
        )}
      </div>
    </PaneFrame>
  )
}
