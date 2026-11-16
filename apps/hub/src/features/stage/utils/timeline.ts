import type { GateDecision, PlaybackStatus } from '@/store/usePlaybackStore'
import type { Chapter } from '@/types/content.types'

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
