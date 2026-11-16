import type { FacetGroupId } from '@/constants/taxonomy'

export type ChangeKind = 'Read' | 'Gated write' | 'Merge-gated'

export interface ScenarioChapter {
  id: string
  t: number
}

export interface Scenario {
  id: string
  useCase: string
  source: 'captured' | 'metadata'
  change: ChangeKind
  stack: string
  client: { name: string; label: string; version?: string }
  terminal?: { cols: number; rows: number }
  capture?: {
    status: 'placeholder' | 'captured'
    month: string
    splunkctl?: string
    /** Splunk SDK for Python version, for demos built on the Agentic SDK. */
    sdk?: string
    take?: string
    timeCompressed?: boolean
    rawDuration?: number
    notes?: string
  }
  cast?: { src: string; duration: number }
  chapters?: ScenarioChapter[]
  gate?: { t: number; command: string }
  browser?: { mode: 'agent'; showAt: string; object: string; screenshot: string }
  artifacts?: { dashboard?: string; source?: string; transcript?: string }
}

export interface Content {
  title: string
  summary: string
  taxonomy: { category: string; personas?: string[]; technologies: string[]; splunk: string[] }
  chapters?: Record<string, string>
  gate?: { title: string; body: string; approve: string; decline: string; declinedTitle: string; declinedBody: string }
  browser?: { waiting: string; alt: string }
  /** Labels for the architecture diagram; the browser boxes appear only for demos with a browser pane. */
  flow?: { mcp?: string; kind?: 'sdk' }
  display: { hidden: boolean; featured: boolean; order: number }
}

export type TranscriptEntry =
  | { kind: 'user' | 'agent'; t: number; text: string }
  | { kind: 'shell'; t: number; command: string; result?: string; blocked?: boolean; by?: 'user' }
  | { kind: 'mcp'; t: number; tool: string; args?: Record<string, unknown>; result?: string }
  | { kind: 'browser'; t: number; command: string; result?: string }
  | { kind: 'file'; t: number; name: string; tag?: string; artifact?: 'dashboard' | 'source' }
  | { kind: 'skill'; t: number; name: string }

export interface TranscriptChapter {
  id: string
  summary: string
  gate?: boolean
  entries: TranscriptEntry[]
}

export interface Transcript {
  placeholder?: boolean
  chapters: TranscriptChapter[]
}

export interface Chapter extends ScenarioChapter {
  label: string
}

/** One catalog record with everything the page needs, resolved at build time. */
export interface DemoEntry {
  id: string
  scenario: Scenario
  content: Content
  facets: Record<FacetGroupId, string[]>
  playable: boolean
  split: boolean
  chapters: Chapter[]
  castUrl?: string
  screenshotUrl?: string
  dashboardJson?: string
  /** The script the agent wrote, for demos whose output is code rather than a dashboard. */
  sourceCode?: string
  transcript?: Transcript
  howItWorksHtml?: string
}
