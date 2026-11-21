import type { Content, GateCopy, Scenario } from '@/types/content.types'

export interface Gate {
  /** The narration anchor and the key into content.yaml `gates`. A demo with one `gate` uses the id `gate`. */
  id: string
  t: number
  command: string
}

/** The demo's approvals in the order they happen. `gate` is one approval; `gates` lists several. */
export function gatesOf(scenario: Scenario): Gate[] {
  const list: Gate[] = scenario.gates ?? (scenario.gate ? [{ id: 'gate', ...scenario.gate }] : [])
  return [...list].sort((a, b) => a.t - b.t)
}

export function gateCopy(content: Content, id: string): GateCopy | undefined {
  return content.gates?.[id] ?? (id === 'gate' ? content.gate : undefined)
}
