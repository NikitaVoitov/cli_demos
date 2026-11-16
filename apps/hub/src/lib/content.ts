import { CATEGORIES, FACET_GROUPS, type FacetGroupId } from '@/constants/taxonomy'
import type { Content, DemoEntry, Scenario, Transcript } from '@/types/content.types'

const scenarios = import.meta.glob<Scenario>('@scenarios/*/scenario.yaml', { eager: true, import: 'default' })
const contents = import.meta.glob<Content>('@scenarios/*/content.yaml', { eager: true, import: 'default' })
const howItWorks = import.meta.glob<string>('@scenarios/*/how-it-works.md', { eager: true, import: 'default' })
const transcripts = import.meta.glob<Transcript>('@scenarios/*/artifacts/transcript.json', { eager: true, import: 'default' })
const rawJson = import.meta.glob<string>('@scenarios/*/artifacts/*.{json,py}', { eager: true, query: '?raw', import: 'default' })
const assetUrls = import.meta.glob<string>('@scenarios/*/artifacts/*.{cast,png}', { eager: true, query: '?url', import: 'default' })

function dirOf(path: string) {
  return path.slice(0, path.lastIndexOf('/'))
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
    screenshotUrl: assetUrls[artifact(scenario.browser?.screenshot) ?? ''],
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
