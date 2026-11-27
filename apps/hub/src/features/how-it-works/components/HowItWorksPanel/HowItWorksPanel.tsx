import type { DemoEntry } from '@/types/content.types'
import {
  CdtsmFlowDiagram,
  DacFlowDiagram,
  FlowDiagram,
  JiraFlowDiagram,
  NotebookFlowDiagram,
  PhishingFlowDiagram,
  SaiaFlowDiagram,
  SdkFlowDiagram,
} from '../FlowDiagram/FlowDiagram'
import { SequenceDiagram } from '../SequenceDiagram/SequenceDiagram'

// Each column is a sub-tile: the intro reads as prose, the details sit beside it.
const proseClass = [
  'text-body-sm text-muted-foreground',
  '[&_h2]:mb-2 [&_h2]:text-[16px] [&_h2]:font-semibold [&_h2]:text-foreground',
  '[&_h3]:mb-2 [&_h3]:text-[14px] [&_h3]:font-semibold [&_h3]:text-foreground [&_ul+h3]:mt-5',
  '[&_p]:mb-3 [&_ul]:list-disc [&_ul]:pl-5 [&_li]:mb-1 [&_strong]:font-semibold [&_strong]:text-foreground',
  '[&_code]:rounded-sm [&_code]:bg-terminal [&_code]:px-1 [&_code]:font-mono [&_code]:text-[13px] [&_code]:whitespace-nowrap [&_code]:text-foreground',
  '[&_a]:text-link [&_a]:underline [&_a]:underline-offset-2',
].join(' ')

// The About markdown has two parts: the intro, then the "### " detail sections.
function splitAbout(html: string) {
  const at = html.indexOf('<h3')
  return at === -1 ? { intro: html, details: '' } : { intro: html.slice(0, at), details: html.slice(at) }
}

export function HowItWorksPanel({ entry }: { entry: DemoEntry }) {
  const { intro, details } = splitAbout(entry.howItWorksHtml ?? '')
  return (
    <div className="flex flex-col gap-4">
      <article className="rounded-lg border border-border bg-card/60 p-4">
        <div className="grid gap-6 md:grid-cols-2 md:gap-10">
          {/* Authored in the repo and compiled at build time; never user input. */}
          <div className={`${proseClass} max-w-[68ch]`} dangerouslySetInnerHTML={{ __html: intro }} />
          <div className={proseClass} dangerouslySetInnerHTML={{ __html: details }} />
        </div>
      </article>
      <section aria-labelledby="architecture-heading" className="rounded-lg border border-border bg-card/60 p-4">
        <h2 id="architecture-heading" className="mb-3 text-[16px] font-semibold">
          Architecture
        </h2>
        <div className="mx-auto max-w-[1000px]">
          {entry.content.flow?.kind === 'sdk' ? (
            <SdkFlowDiagram mcp={entry.content.flow.mcp} />
          ) : entry.content.flow?.kind === 'jira' ? (
            <JiraFlowDiagram mcp={entry.content.flow.mcp} />
          ) : entry.content.flow?.kind === 'cdtsm' ? (
            <CdtsmFlowDiagram mcp={entry.content.flow.mcp} />
          ) : entry.content.flow?.kind === 'notebook' ? (
            <NotebookFlowDiagram mcp={entry.content.flow.mcp} agent={entry.content.flow.agent} />
          ) : entry.content.flow?.kind === 'phishing' ? (
            <PhishingFlowDiagram />
          ) : entry.content.flow?.kind === 'saia' ? (
            <SaiaFlowDiagram />
          ) : entry.content.flow?.kind === 'dac' ? (
            <DacFlowDiagram mcp={entry.content.flow.mcp} agent={entry.content.flow.agent} />
          ) : (
            <FlowDiagram browser={entry.split} mcp={entry.content.flow?.mcp} />
          )}
        </div>
      </section>
      {entry.sequence && (
        <section aria-labelledby="agentic-workflow-heading" className="rounded-lg border border-border bg-card/60 p-4">
          <h2 id="agentic-workflow-heading" className="mb-3 text-[16px] font-semibold">
            Agentic workflow
          </h2>
          <SequenceDiagram source={entry.sequence} title="Agentic workflow" />
        </section>
      )}
    </div>
  )
}
