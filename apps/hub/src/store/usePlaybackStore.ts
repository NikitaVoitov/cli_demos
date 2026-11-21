import { create } from 'zustand'

export type PlaybackStatus = 'loading' | 'idle' | 'playing' | 'paused' | 'gate' | 'declined' | 'ended'
export type GateDecision = 'pending' | 'approved' | 'declined'

/** Imperative handle the stage registers so siblings (gate bar, progress) can drive the player. */
export interface PlayerController {
  play: () => void
  pause: () => void
  seek: (time: number) => void
}

const CAPTIONS_KEY = 'demo-hub:captions'

interface PlaybackState {
  status: PlaybackStatus
  decision: GateDecision
  /** Which approval the demo waits at next, and how many it has; one for a demo with a single gate. */
  gateIndex: number
  gateCount: number
  time: number
  controller: PlayerController | null
  /** Narration captions over the terminal; the visitor's choice survives demo switches and reloads. */
  captionsOn: boolean
  /** True when the visitor muted the player's speaker; captions follow this and hide while muted. */
  muted: boolean
  toggleCaptions: () => void
  setMuted: (muted: boolean) => void
  setStatus: (status: PlaybackStatus) => void
  setTime: (time: number) => void
  setController: (controller: PlayerController | null) => void
  approve: () => void
  decline: () => void
  replay: () => void
  reset: (gateCount?: number) => void
}

export const usePlaybackStore = create<PlaybackState>((set, get) => ({
  status: 'loading',
  decision: 'pending',
  gateIndex: 0,
  gateCount: 0,
  time: 0,
  controller: null,
  captionsOn: localStorage.getItem(CAPTIONS_KEY) !== 'off',
  muted: false,
  toggleCaptions: () => {
    const captionsOn = !get().captionsOn
    localStorage.setItem(CAPTIONS_KEY, captionsOn ? 'on' : 'off')
    set({ captionsOn })
  },
  setMuted: (muted) => set({ muted }),
  setStatus: (status) => set({ status }),
  setTime: (time) => set({ time }),
  setController: (controller) => set({ controller }),
  approve: () => {
    // Each approval opens the way to the next gate; after the last one nothing stops the demo.
    const gateIndex = get().gateIndex + 1
    set({ gateIndex, decision: gateIndex >= get().gateCount ? 'approved' : 'pending', status: 'playing' })
    get().controller?.play()
  },
  decline: () => {
    get().controller?.pause()
    set({ decision: 'declined', status: 'declined' })
  },
  replay: () => {
    const { controller } = get()
    controller?.pause()
    controller?.seek(0)
    set({ decision: 'pending', gateIndex: 0, status: 'idle', time: 0 })
  },
  reset: (gateCount = 0) =>
    set({ status: 'loading', decision: 'pending', gateIndex: 0, gateCount, time: 0, controller: null, muted: false }),
}))
