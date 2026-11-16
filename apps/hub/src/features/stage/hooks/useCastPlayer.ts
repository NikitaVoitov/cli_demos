import { useEffect, type RefObject } from 'react'
import type { Player } from 'asciinema-player'
import { usePlaybackStore } from '@/store/usePlaybackStore'
import type { DemoEntry } from '@/types/content.types'
import { isBeyondGate } from '../utils/timeline'

/** The player has no time-update event, so the stage polls its clock. */
const POLL_MS = 100

export function useCastPlayer(entry: DemoEntry, containerRef: RefObject<HTMLDivElement | null>) {
  useEffect(() => {
    const el = containerRef.current
    if (!el || !entry.castUrl) return
    const store = usePlaybackStore.getState
    const gateT = entry.scenario.gate?.t
    let player: Player | undefined
    let interval: number | undefined
    let disposed = false

    store().reset()

    Promise.all([import('asciinema-player'), import('asciinema-player/dist/bundle/asciinema-player.css')]).then(
      ([AsciinemaPlayer]) => {
        if (disposed) return
        player = AsciinemaPlayer.create({ url: entry.castUrl! }, el, {
          // Fit inside the pane in both directions so the bottom rows and the control bar are never clipped.
          fit: 'both',
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
          if (status === 'ended') usePlaybackStore.setState({ decision: 'pending' })
          if (status !== 'declined') setStatus('playing')
        })
        p.addEventListener('pause', () => {
          if (store().status === 'playing') store().setStatus('paused')
        })
        p.addEventListener('ended', () => store().setStatus('ended'))

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
          const { decision, status, setStatus, setTime } = store()

          if (gateT !== undefined && decision !== 'approved') {
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
      store().setController(null)
    }
  }, [entry, containerRef])
}
