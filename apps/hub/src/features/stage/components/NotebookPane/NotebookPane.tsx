import { useEffect, useRef, useState } from 'react'
import type { Player } from 'asciinema-player'
import { Maximize2, Minimize2, Rows3, StretchHorizontal } from 'lucide-react'
import { cn } from '@/lib/utils'
import { usePlaybackStore } from '@/store/usePlaybackStore'
import type { NotebookPane as Pane } from '@/types/content.types'
import { frameAt } from '../../utils/timeline'
import { PaneFrame } from '../TerminalPane/TerminalPane'

function HeaderButton({ label, pressed, onClick, children }: {
  label: string
  pressed?: boolean
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      type="button"
      title={label}
      aria-label={label}
      aria-pressed={pressed}
      onClick={onClick}
      className={cn(
        'flex h-5 items-center gap-1 rounded-sm px-1.5 font-semibold hover:bg-foreground/10',
        pressed ? 'text-gate' : 'text-subtle-foreground',
      )}
    >
      {children}
    </button>
  )
}

/**
 * The notebook beside the terminal. Its cast holds one frame per notebook state, so this player never plays: it seeks
 * to the state the terminal's clock has reached and scrolls to the cell the agent is on. "Whole notebook" shrinks it
 * to fit the pane; fullscreen gives it the screen.
 */
export function NotebookPane({ pane }: { pane: Pane }) {
  const rootRef = useRef<HTMLDivElement>(null)
  const scrollRef = useRef<HTMLDivElement>(null)
  const playerRef = useRef<HTMLDivElement>(null)
  const player = useRef<Player | undefined>(undefined)
  const [ready, setReady] = useState(false)
  const [whole, setWhole] = useState(false)
  const [fullscreen, setFullscreen] = useState(false)
  const [wholeWidth, setWholeWidth] = useState<number>()
  const index = usePlaybackStore((state) => frameAt(pane.frames, state.time))
  const frame = pane.frames[index]

  useEffect(() => {
    const el = playerRef.current
    if (!el) return
    let disposed = false
    Promise.all([import('asciinema-player'), import('asciinema-player/dist/bundle/asciinema-player.css')]).then(
      ([AsciinemaPlayer]) => {
        if (disposed) return
        player.current = AsciinemaPlayer.create({ url: pane.castUrl }, el, {
          fit: 'width',
          controls: false,
          preload: true,
          theme: 'demo',
          terminalFontFamily: "'SF Mono', ui-monospace, Menlo, Monaco, Consolas, monospace",
        })
        setReady(true)
      },
    )
    return () => {
      disposed = true
      player.current?.dispose()
      player.current = undefined
      setReady(false)
    }
  }, [pane.castUrl])

  // Show the frame for the terminal's time, then bring its cell into view.
  useEffect(() => {
    const p = player.current
    if (!ready || !p) return
    void p.seek(frame.t + 0.001).then(() => {
      const scroller = scrollRef.current
      const term = playerRef.current
      if (!scroller || !term || whole) return
      const rowPx = term.getBoundingClientRect().height / pane.rows
      scroller.scrollTo({ top: frame.focus * rowPx, behavior: 'smooth' })
    })
  }, [ready, frame, whole, pane.rows])

  // "Whole notebook": the width at which every row fits the pane's height. The player keeps its shape at any width.
  useEffect(() => {
    const scroller = scrollRef.current
    const term = playerRef.current
    if (!scroller || !term) return
    const measure = () => {
      const { width, height } = term.getBoundingClientRect()
      if (!width || !height) return
      setWholeWidth(Math.min(scroller.clientWidth, (scroller.clientHeight * width) / height))
    }
    measure()
    const observer = new ResizeObserver(measure)
    observer.observe(scroller)
    observer.observe(term)
    return () => observer.disconnect()
  }, [])

  useEffect(() => {
    const onChange = () => setFullscreen(document.fullscreenElement === rootRef.current)
    document.addEventListener('fullscreenchange', onChange)
    return () => document.removeEventListener('fullscreenchange', onChange)
  }, [])

  const toggleFullscreen = () => {
    if (document.fullscreenElement) void document.exitFullscreen()
    else void rootRef.current?.requestFullscreen()
  }

  const actions = (
    <>
      <HeaderButton label={whole ? 'Follow the agent' : 'Show the whole notebook'} pressed={whole} onClick={() => setWhole(!whole)}>
        {whole ? <StretchHorizontal aria-hidden className="size-3.5" /> : <Rows3 aria-hidden className="size-3.5" />}
        {whole ? 'Follow' : 'Whole notebook'}
      </HeaderButton>
      <HeaderButton label={fullscreen ? 'Exit notebook fullscreen' : 'Notebook fullscreen'} onClick={toggleFullscreen}>
        {fullscreen ? <Minimize2 aria-hidden className="size-3.5" /> : <Maximize2 aria-hidden className="size-3.5" />}
      </HeaderButton>
    </>
  )

  return (
    <div ref={rootRef} className={cn('flex min-w-0 flex-col', fullscreen && 'h-full bg-background p-2')}>
      <PaneFrame title={pane.title} focused={frame.running} actions={actions} className={cn(fullscreen && 'flex-1')}>
        <div
          ref={scrollRef}
          role="region"
          aria-label={`The notebook ${pane.title}, in step with the terminal recording${frame.cell ? `: ${frame.running ? 'running' : 'ran'} cell ${frame.cell}` : ''}. The Transcript tab has the executed notebook.`}
          tabIndex={0}
          className={cn('relative overflow-x-hidden', whole ? 'overflow-y-hidden' : 'overflow-y-auto', fullscreen ? 'flex-1' : 'h-[386px]')}
        >
          {/* The terminal's clock drives this player, so it takes no input: no start overlay, no keys, no clicks. */}
          <div
            ref={playerRef}
            inert
            className="pointer-events-none mx-auto [&_.ap-overlay-start]:!hidden"
            style={{ width: whole && wholeWidth ? `${wholeWidth}px` : '100%' }}
          />
        </div>
      </PaneFrame>
    </div>
  )
}
