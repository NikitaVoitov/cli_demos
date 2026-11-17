import { CATEGORIES, FACET_GROUPS, type FacetGroupId } from '@/constants/taxonomy'
import type { Caption, Content, DemoEntry, Scenario, Transcript } from '@/types/content.types'

const scenarios = import.meta.glob<Scenario>('@scenarios/*/scenario.yaml', { eager: true, import: 'default' })
const contents = import.meta.glob<Content>('@scenarios/*/content.yaml', { eager: true, import: 'default' })
const howItWorks = import.meta.glob<string>('@scenarios/*/how-it-works.md', { eager: true, import: 'default' })
const transcripts = import.meta.glob<Transcript>('@scenarios/*/artifacts/transcript.json', { eager: true, import: 'default' })
const rawJson = import.meta.glob<string>('@scenarios/*/artifacts/*.{json,py}', { eager: true, query: '?raw', import: 'default' })
const assetUrls = import.meta.glob<string>('@scenarios/*/artifacts/*.{cast,png,mp3}', { eager: true, query: '?url', import: 'default' })
const captionFiles = import.meta.glob<string>('@scenarios/*/artifacts/*.vtt', { eager: true, query: '?raw', import: 'default' })

function dirOf(path: string) {
  return path.slice(0, path.lastIndexOf('/'))
}

function seconds(stamp: string) {
  const [h, m, s] = stamp.split(':')
  return Number(h) * 3600 + Number(m) * 60 + Number(s)
}

/** Reads the WebVTT that pipeline/narrate.py writes: one cue per line, the cue id is the line id. */
function parseCaptions(vtt: string): Caption[] {
  return vtt
    .split(/\n{2,}/)
    .map((block) => block.trim().split('\n'))
    .filter((rows) => rows.length >= 3 && rows[1].includes('-->'))
    .map(([id, timing, ...text]) => {
      const [start, end] = timing.split('-->').map((stamp) => seconds(stamp.trim()))
      return { id, start, end, text: text.join(' ') }
    })
}

/** Narration audio is generated from scenario.yaml, so a line, anchor, or chapter edit without a rerun is stale. */
function loadCaptions(scenario: Scenario, vtt: string | undefined): Caption[] {
  const { narration } = scenario
  const rerun = `run \`python -m pipeline.narrate scenarios/${scenario.id}\``
  if (!narration) return []
  if (!vtt) throw new Error(`${scenario.id}: ${narration.captions} is missing; ${rerun}`)
  const anchors: Record<string, number> = Object.fromEntries((scenario.chapters ?? []).map((c) => [c.id, c.t]))
  if (scenario.gate) anchors.gate = scenario.gate.t
  const captions = parseCaptions(vtt)
  const byId = new Map(captions.map((caption) => [caption.id, caption]))
  for (const line of narration.lines) {
    const caption = byId.get(line.id)
    const start = line.t ?? anchors[line.chapter ?? ''] + (line.offset ?? 0)
    const text = line.text.split(/\s+/).join(' ').trim()
    if (!caption || caption.text !== text || Math.abs(caption.start - start) > 0.02) {
      throw new Error(`${scenario.id}: narration line "${line.id}" doesn't match ${narration.captions}; ${rerun}`)
    }
  }
  if (captions.length !== narration.lines.length) throw new Error(`${scenario.id}: ${narration.captions} has extra cues; ${rerun}`)
  return captions
}

function assertVocabulary(id: string, group: string, values: string[], allowed: readonly string[]) {
  for (const value of values) {
    if (!allowed.includes(value)) throw new Error(`${id}: "${value}" is not in the ${group} vocabulary`)
  }
}

function buildEntry(scenarioPath: string): DemoEntry {
  const dir = dirOf(scenarioPath)
  const scenario = scenarios[scenarioPath]
  const content = contents[`${dir}/content.yaml`]
  if (!content) throw new Error(`${scenario.id}: content.yaml is missing`)

  const facets: Record<FacetGroupId, string[]> = {
    persona: content.taxonomy.personas ?? [],
    agent: [scenario.client.label],
    splunk: content.taxonomy.splunk,
    technologies: content.taxonomy.technologies,
  }
  assertVocabulary(scenario.id, 'category', [content.taxonomy.category], CATEGORIES)
  for (const group of FACET_GROUPS) {
    assertVocabulary(scenario.id, group.label, facets[group.id], group.values)
    // Tags read in vocabulary order, whatever order content.yaml lists them in.
    facets[group.id] = [...facets[group.id]].sort((a, b) => group.values.indexOf(a) - group.values.indexOf(b))
  }

  const chapters = (scenario.chapters ?? []).map((chapter) => {
    const label = content.chapters?.[chapter.id]
    if (!label) throw new Error(`${scenario.id}: chapter "${chapter.id}" has no label in content.yaml`)
    return { ...chapter, label }
  })

  const playable = scenario.source === 'captured' && Boolean(scenario.cast)
  const artifact = (relative?: string) => (relative ? `${dir}/${relative}` : undefined)

  return {
    id: scenario.id,
    scenario,
    content,
    facets,
    playable,
    split: Boolean(scenario.browser),
    chapters,
    castUrl: assetUrls[artifact(scenario.cast?.src) ?? ''],
    narrationUrl: assetUrls[artifact(scenario.narration?.audio) ?? ''],
    captions: loadCaptions(scenario, captionFiles[artifact(scenario.narration?.captions) ?? '']),
    screenshotUrl: assetUrls[artifact(scenario.browser?.screenshot) ?? ''],
    browserSteps: (scenario.browser?.steps ?? []).map((step) => {
      const at = (mark: string | number | undefined, fallback: number) => {
        if (mark === undefined) return fallback
        if (typeof mark === 'number') return mark
        const chapter = chapters.find((c) => c.id === mark)
        if (!chapter) throw new Error(`${scenario.id}: browser step "${step.id}" points at unknown chapter "${mark}"`)
        return chapter.t
      }
      const url = assetUrls[artifact(step.screenshot) ?? '']
      const copy = content.browser?.steps?.[step.id]
      if (!url) throw new Error(`${scenario.id}: browser step "${step.id}" screenshot ${step.screenshot} is missing`)
      if (!copy) throw new Error(`${scenario.id}: browser step "${step.id}" has no copy in content.yaml`)
      return { id: step.id, url, object: step.object, from: at(step.from, 0), until: at(step.until, 0), ...copy }
    }),
    dashboardJson: rawJson[artifact(scenario.artifacts?.dashboard) ?? ''],
    sourceCode: rawJson[artifact(scenario.artifacts?.source) ?? ''],
    transcript: transcripts[artifact(scenario.artifacts?.transcript) ?? ''],
    howItWorksHtml: howItWorks[`${dir}/how-it-works.md`],
  }
}

export const CATALOG: DemoEntry[] = Object.keys(scenarios)
  .map(buildEntry)
  .filter((entry) => !entry.content.display.hidden)
  .sort((a, b) => a.content.display.order - b.content.display.order)

export const DEFAULT_DEMO_ID =
  CATALOG.find((entry) => entry.playable && entry.content.display.featured)?.id ?? CATALOG[0]?.id

export function getDemo(id: string | undefined) {
  return CATALOG.find((entry) => entry.id === id)
}
