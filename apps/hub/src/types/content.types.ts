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
  /** `title` overrides the terminal pane's header, which defaults to "zsh — <client>". */
  terminal?: { cols: number; rows: number; title?: string }
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
  /**
   * Several approvals in one demo, such as approved notebook cells. Each `id` is a narration anchor (`chapter: <id>`)
   * and the key of its copy in content.yaml `gates`. Use `gate` for a demo with one approval.
   */
  gates?: { id: string; t: number; command: string; summary?: string }[]
  browser?: {
    mode: 'agent'
    showAt: string
    object: string
    screenshot: string
    /**
     * Screenshots shown before the result, each over its own stretch of the cast, such as the source data and an
     * intermediate result. `from` and `until` are chapter IDs or seconds on the published clock; `from` defaults to 0.
     */
    steps?: { id: string; screenshot: string; object: string; from?: string | number; until: string | number }[]
  }
  /**
   * `notebooks`: Jupyter notebooks the demo publishes; each shows in the transcript after the command that ran it.
   * `files`: text files shown in full in the transcript, attached by pipeline.transcript to the step that read, wrote,
   * or produced them (`read`/`write` regexes on a path, `shell` on a command).
   */
  artifacts?: {
    dashboard?: string
    source?: string
    transcript?: string
    notebooks?: string[]
    files?: { src: string; name?: string; tag?: string; read?: string; write?: string; shell?: string; nth?: number }[]
  }
  /**
   * An n8n workflow drawn on the real n8n canvas beside the terminal. `src` is the sanitized export from
   * `pipeline.workflow`. Each step lights one node, by name: running from `at`, done at `until` (default: the next
   * later step). Times are chapter IDs, gate IDs, or seconds on the published cast. With a `browser` block too, the
   * two share the pane: the canvas holds it from `show.from` until `show.until`, screenshots the rest of the time.
   */
  workflow?: {
    src: string
    show?: { from: string | number; until?: string | number }
    steps: { node: string; at: string | number; until?: string | number; callout?: string; status?: 'success' | 'error' }[]
  }
  /**
   * A second, time-synced pane beside the terminal with the notebook as the agent changes it: each cell running, then
   * its saved outputs. `pipeline.post` writes `cast` and its frame index (`cast` with .json) from the take's jpterm trace.
   */
  notebookPane?: { notebook: string; cast: string; cols?: number }
  narration?: Narration
}

/** Spoken lines on the cast clock; `pipeline/narrate.py` turns them into `audio` and `captions`. */
export interface Narration {
  audio: string
  captions: string
  voice?: { id?: string; name?: string; model?: string }
  lines: { id: string; text: string; t?: number; chapter?: string; offset?: number }[]
}

/** One narration line as synthesized: when it starts and ends on the cast clock, and its caption text. */
export interface Caption {
  id: string
  start: number
  end: number
  text: string
}

export interface GateCopy {
  title: string
  body: string
  approve: string
  decline: string
  declinedTitle: string
  declinedBody: string
}

export interface Content {
  title: string
  summary: string
  taxonomy: { category: string; personas?: string[]; technologies: string[]; splunk: string[] }
  chapters?: Record<string, string>
  gate?: GateCopy
  /** Copy for each scenario `gates` entry, by its ID. */
  gates?: Record<string, GateCopy>
  /** `title` names the app in the screenshot pane; it defaults to Splunk Web. */
  browser?: {
    waiting: string
    alt: string
    title?: string
    /** Pane title and alt text for each scenario `browser.steps` entry, by its ID. */
    steps?: Record<string, { title?: string; alt: string }>
  }
  /** Copy for the n8n canvas pane: its header, the canvas's accessible description, and callouts by ID. */
  workflow?: { title?: string; object?: string; alt: string; callouts?: Record<string, string> }
  /** Labels for the architecture diagram; the browser boxes appear only for demos with a browser pane. */
  /** `agent` names the recorded client in the notebook flow diagram (default Cursor CLI). */
  flow?: { mcp?: string; agent?: string; kind?: 'sdk' | 'jira' | 'cdtsm' | 'notebook' | 'phishing' | 'saia' | 'dac' }
  display: { hidden: boolean; featured: boolean; order: number }
}

export type TranscriptEntry =
  | { kind: 'user' | 'agent'; t: number; text: string }
  | { kind: 'shell'; t: number; command: string; result?: string; blocked?: boolean; by?: 'user' }
  | { kind: 'mcp'; t: number; tool: string; args?: Record<string, unknown>; result?: string }
  | { kind: 'browser'; t: number; command: string; result?: string }
  | {
      kind: 'file'
      t: number
      name: string
      tag?: string
      artifact?: 'dashboard' | 'source' | 'workflow' | 'notebook' | 'file'
      /** For `file`: the published file's name in artifacts/, and whether the agent read, wrote, or ran the step. */
      src?: string
      via?: 'read' | 'write' | 'shell'
    }
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

/** The subset of an n8n workflow export the hub reads; the canvas gets the whole object. */
export interface N8nWorkflow {
  name: string
  nodes: { id: string; name: string; type: string }[]
  connections: Record<string, Record<string, ({ node: string }[] | null)[]>>
}

export interface WorkflowStep {
  nodeId: string
  node: string
  from: number
  until: number
  status: 'success' | 'error'
  callout?: string
}

export interface DemoWorkflow {
  json: N8nWorkflow
  title: string
  object: string
  alt: string
  /** Connections as pairs of node IDs, which is how the canvas labels its edges. */
  edges: [string, string][]
  steps: WorkflowStep[]
  /** When the canvas holds the side pane, on the published clock; the whole cast unless the demo has screenshots too. */
  show: { from: number; until: number }
}

/** One notebook state in the notebook pane's cast: when it shows, the cell it changed, and the line to scroll to. */
export interface NotebookFrame {
  t: number
  focus: number
  cell: string | null
  running: boolean
}

export interface NotebookPane {
  title: string
  castUrl: string
  rows: number
  cols: number
  frames: NotebookFrame[]
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
  /** The terminal pane's header. */
  terminalTitle: string
  chapters: Chapter[]
  castUrl?: string
  /** Narration track for the player's audioUrl, with one caption per spoken line. */
  narrationUrl?: string
  captions?: Caption[]
  screenshotUrl?: string
  /** Resolved `browser.steps`: when each one shows on the published clock, and its image. */
  browserSteps?: { id: string; url: string; object: string; from: number; until: number; title?: string; alt: string }[]
  /** Resolved `workflow`: the n8n export to draw and when each node runs on the published clock. */
  workflow?: DemoWorkflow
  dashboardJson?: string
  /** The script the agent wrote, for demos whose output is code rather than a dashboard. */
  sourceCode?: string
  /** `artifacts.notebooks` as raw .ipynb JSON, by file name (the transcript entry's `name`). */
  notebooks?: Record<string, string>
  /** `artifacts.files` as text, by file name in artifacts/ (the transcript entry's `src`). */
  files?: Record<string, string>
  notebookPane?: NotebookPane
  transcript?: Transcript
  howItWorksHtml?: string
  /** `sequence.mmd` beside scenario.yaml: a Mermaid sequence diagram of the agentic workflow, end to end. */
  sequence?: string
}
