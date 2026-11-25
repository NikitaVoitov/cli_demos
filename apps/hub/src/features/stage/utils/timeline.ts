import type { GateDecision, PlaybackStatus } from '@/store/usePlaybackStore'
import type { Chapter, NotebookFrame } from '@/types/content.types'

export type StepState = 'done' | 'current' | 'gate' | 'declined' | 'upcoming'

/** Seconds of tolerance so a seek to a chapter's own timestamp counts as being in that chapter. */
const EPSILON = 0.05

export function chapterIndexAt(chapters: Chapter[], time: number) {
  let index = 0
  chapters.forEach((chapter, i) => {
    if (chapter.t <= time + EPSILON) index = i
  })
  return index
}

interface TimelineState {
  time: number
  status: PlaybackStatus
  decision: GateDecision
  gateT?: number
}

export function stepStates(chapters: Chapter[], { time, status, decision, gateT }: TimelineState): StepState[] {
  if (status === 'ended') return chapters.map(() => 'done')
  const gateIndex = gateT === undefined ? -1 : chapterIndexAt(chapters, gateT)

  if (gateIndex >= 0 && (decision === 'declined' || status === 'gate')) {
    return chapters.map((_, i) => (i < gateIndex ? 'done' : i === gateIndex ? (decision === 'declined' ? 'declined' : 'gate') : 'upcoming'))
  }
  const current = chapterIndexAt(chapters, time)
  return chapters.map((_, i) => (i < current ? 'done' : i === current ? 'current' : 'upcoming'))
}

/** Nothing after an unapproved gate can be reached, whether by chapter click or the seek bar. */
export function isBeyondGate(time: number, decision: GateDecision, gateT?: number) {
  return gateT !== undefined && decision !== 'approved' && time > gateT + EPSILON
}

/** The notebook pane's state on screen at `time`: the last frame that has started. */
export function frameAt(frames: NotebookFrame[], time: number) {
  let index = 0
  for (let i = 0; i < frames.length; i += 1) if (frames[i].t <= time + 0.05) index = i
  return index
}
