import { useEffect, type RefObject } from 'react'
import type { Player } from 'asciinema-player'
import { usePlaybackStore } from '@/store/usePlaybackStore'
import type { DemoEntry } from '@/types/content.types'
import { gatesOf } from '@/lib/gates'
import { isBeyondGate } from '../utils/timeline'

/** The player has no time-update event, so the stage polls its clock. */
const POLL_MS = 100

/**
 * Workers static assets answer Range requests with a full 200, and Safari can't seek audio without a 206, so the
 * track plays from a Blob URL. Without it the demo still plays, just silently.
 */
async function loadNarration(url: string | undefined) {
  if (!url) return undefined
  try {
    const response = await fetch(url)
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    return URL.createObjectURL(await response.blob())
  } catch (error) {
    console.warn('Narration unavailable, playing without sound:', error)
    return undefined
  }
}

export function useCastPlayer(
  entry: DemoEntry,
  containerRef: RefObject<HTMLDivElement | null>,
  fit: 'both' | 'width',
) {
  useEffect(() => {
    const el = containerRef.current
    if (!el || !entry.castUrl) return
    const store = usePlaybackStore.getState
    const gates = gatesOf(entry.scenario)
    let player: Player | undefined
    let interval: number | undefined
    let audioUrl: string | undefined
    let disposed = false

    store().reset(gates.length)

    Promise.all([
      import('asciinema-player'),
      import('asciinema-player/dist/bundle/asciinema-player.css'),
      loadNarration(entry.narrationUrl),
    ]).then(
      ([AsciinemaPlayer, , narration]) => {
        if (disposed) {
          if (narration) URL.revokeObjectURL(narration)
          return
        }
        audioUrl = narration
        player = AsciinemaPlayer.create({ url: entry.castUrl! }, el, {
          // The player keeps the audio on its own clock through play, pause, seek, and the gate pause, and adds a
          // speaker button to its control bar. Narrated demos never autoplay, so the visitor's Play click allows sound.
          audioUrl,
          // 'both' keeps the bottom rows and the control bar inside a fixed-height pane; 'width' lets a narrow
          // pane take the recording's own height instead of leaving empty space under the controls.
          fit,
          controls: true,
          preload: true,
          theme: 'demo',
          terminalFontFamily: "'SF Mono', ui-monospace, Menlo, Monaco, Consolas, monospace",
          markers: entry.chapters.map((chapter) => [chapter.t, chapter.label] as [number, string]),
          poster: 'npt:0:5',
        })
        const p = player

        p.addEventListener('play', () => {
          const { status, setStatus } = store()
          // Playing again after the end restarts the story, so the visitor decides at the gate again.
          if (status === 'ended') usePlaybackStore.setState({ decision: 'pending', gateIndex: 0 })
          if (status !== 'declined') setStatus('playing')
        })
        p.addEventListener('pause', () => {
          if (store().status === 'playing') store().setStatus('paused')
        })
        p.addEventListener('ended', () => store().setStatus('ended'))
        // The published types omit `muted`; the 3.18 player fires it with a boolean when the speaker button is used.
        ;(p as Player & { addEventListener(event: 'muted', handler: (muted: boolean) => void): void }).addEventListener(
          'muted',
          (muted) => store().setMuted(Boolean(muted)),
        )

        store().setController({
          play: () => void p.play(),
          pause: () => void p.pause(),
          seek: (time) => {
            void p.seek(time)
            if (store().status === 'ended') store().setStatus('paused')
          },
        })
        store().setStatus('idle')

        interval = window.setInterval(() => {
          const time = p.getCurrentTime()
          const { decision, status, gateIndex, setStatus, setTime } = store()
          // The next unapproved gate; after the last approval there is none.
          const gateT = decision === 'approved' ? undefined : gates[gateIndex]?.t

          if (gateT !== undefined) {
            const reachedGate = time >= gateT - 0.02
            if (reachedGate && decision === 'pending' && status !== 'gate') {
              void p.pause()
              void p.seek(gateT)
              setStatus('gate')
            } else if (isBeyondGate(time, decision, gateT)) {
              void p.pause()
              void p.seek(gateT)
            } else if (status === 'gate' && time < gateT - 0.3) {
              setStatus('paused')
            }
          }
          setTime(isBeyondGate(time, decision, gateT) ? gateT! : time)
        }, POLL_MS)
      },
    )

    return () => {
      disposed = true
      window.clearInterval(interval)
      player?.dispose()
      if (audioUrl) URL.revokeObjectURL(audioUrl)
      store().setController(null)
    }
  }, [entry, containerRef, fit])
}
