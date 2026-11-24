/** Shared vocabulary for categories and facets. Values outside these lists are a content error. */
export const CATEGORIES = [
  'Incident Investigation & Triage',
  'Security Operations',
  'Data Onboarding & Pipelines',
  'Content Authoring & Lifecycle',
  'Platform Operations & Governance',
  'Extend & Build',
] as const

export type FacetGroupId = 'persona' | 'agent' | 'splunk' | 'technologies'

/** Personas from the use case matrix (§2.2), short enough for a card; the full role is the tooltip. */
export const PERSONAS: Record<string, string> = {
  Admin: 'Splunk Platform Admin: indexes, apps, access, health, upgrades',
  'DevOps Engineer': 'Platform / DevOps Engineer: Git, CI/CD, Terraform, runbooks',
  'Data Engineer': 'Data / Pipeline Engineer: sources, collection, processing, routing',
  SRE: 'SRE / IT Ops: service reliability and on-call response',
  Analyst: 'Analyst / Power User: ad hoc searches, reports, dashboards',
  'SOC Analyst': 'SOC Analyst: triage, investigation, and response for security findings',
  'Detection Engineer': 'Detection Engineer / Threat Hunter: detection content, coverage, hunts',
  'Governance Approver': 'Security & Governance Approver: who may read or change Splunk, audit evidence',
  'App Developer': 'App Developer / Partner: Splunk apps, visualizations, integrations',
}

/**
 * Group order is the order tags read on a card and in the filter panel: who it's for, which agent,
 * which Splunk pieces, then third-party tools. Values within a group keep the order listed here.
 */
export const FACET_GROUPS: { id: FacetGroupId; label: string; values: string[] }[] = [
  { id: 'persona', label: 'Persona', values: Object.keys(PERSONAS) },
  { id: 'agent', label: 'Agent', values: ['Claude Code', 'Codex', 'Cursor', 'Gemini CLI', 'GitHub Copilot'] },
  {
    id: 'splunk',
    label: 'Splunk',
    values: [
      'splunkctl',
      'Splunk MCP',
      'Splunk Agent Skills',
      'Agentic Splunk SDK',
      'Splunk Dashboard Studio',
      'Splunk AI Toolkit',
      'CDTSM',
      'Machine Data Lake',
      'Splunk Cloud',
    ],
  },
  { id: 'technologies', label: 'Technologies', values: ['Python', 'Jupyter', 'pandas', 'Gemini', 'Playwright', 'Jira', 'n8n', 'Outlook', 'Kubernetes', 'Terraform', 'GitHub Actions', 'Slack', 'Azure'] },
]
