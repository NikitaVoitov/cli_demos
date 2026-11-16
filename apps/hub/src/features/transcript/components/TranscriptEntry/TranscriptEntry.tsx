import { BookOpen, FileJson, Globe, Plug, Sparkles, Terminal, User, type LucideIcon } from 'lucide-react'
import { CodeBlock } from '@/components/shared/CodeBlock'
import { Tag } from '@/components/shared/Tag'
import { cn } from '@/lib/utils'
import type { DemoEntry, TranscriptEntry as Entry } from '@/types/content.types'
import { formatClock } from '@/utils/formatters/time'

const ACTORS: Record<Entry['kind'], { who: string; verb: string; Icon: LucideIcon; tone: string }> = {
  user: { who: 'You', verb: 'typed', Icon: User, tone: 'bg-muted text-foreground' },
  agent: { who: 'Agent', verb: 'said', Icon: Sparkles, tone: 'bg-foreground/10 text-foreground' },
  shell: { who: 'Shell', verb: 'Agent ran', Icon: Terminal, tone: 'bg-success/15 text-success' },
  mcp: { who: 'Splunk MCP', verb: 'Agent called', Icon: Plug, tone: 'bg-primary/20 text-accent-pink' },
  browser: { who: 'Browser', verb: 'Agent ran', Icon: Globe, tone: 'bg-info/15 text-info' },
  file: { who: 'Artifact', verb: 'Agent wrote', Icon: FileJson, tone: 'bg-artifact/15 text-artifact' },
  skill: { who: 'Skill', verb: 'Agent loaded', Icon: BookOpen, tone: 'bg-muted text-foreground' },
}

function Result({ label, text, blocked }: { label: string; text: string; blocked?: boolean }) {
  return (
    <div
      className={cn(
        'mt-1.5 rounded-md border border-dashed px-3 py-2',
        blocked ? 'border-gate/50 text-gate' : 'border-border text-muted-foreground',
      )}
    >
      <span className="mb-1 block text-[11px] font-semibold tracking-wide text-subtle-foreground uppercase">{label}</span>
      {/* Long tool output scrolls inside the tile instead of stretching it. */}
      <pre className="max-h-64 overflow-auto font-mono text-[12px] leading-5 whitespace-pre">{text}</pre>
    </div>
  )
}

/** Inline `code` and **bold** from the agent's markdown. */
function Inline({ text }: { text: string }) {
  return text.split(/(`[^`]+`|\*\*[^*]+\*\*)/g).map((part, i) =>
    part.startsWith('`') && part.endsWith('`') && part.length > 2 ? (
      <code key={i} className="rounded-sm bg-terminal px-1 font-mono text-[12.5px] text-foreground">
        {part.slice(1, -1)}
      </code>
    ) : part.startsWith('**') && part.endsWith('**') && part.length > 4 ? (
      <strong key={i}>{part.slice(2, -2)}</strong>
    ) : (
      part
    ),
  )
}

/** The agent writes markdown: fenced blocks, bullet lists, and paragraphs. */
function AgentText({ text }: { text: string }) {
  const blocks = text.split(/```[^\n]*\n([\s\S]*?)```/g)
  return (
    <div className="flex flex-col gap-2 pt-0.5 text-body-sm">
      {blocks.map((block, i) => {
        if (i % 2 === 1) return <CodeBlock key={i} code={block.trim()} copyLabel="Copy code" />
        return block
          .split(/\n{2,}/)
          .filter((para) => para.trim())
          .map((para, j) => {
            const lines = para.trim().split('\n')
            if (lines.every((line) => /^\s*[-*] /.test(line))) {
              return (
                <ul key={`${i}-${j}`} className="list-disc pl-5">
                  {lines.map((line, k) => (
                    <li key={k}>
                      <Inline text={line.replace(/^\s*[-*] /, '')} />
                    </li>
                  ))}
                </ul>
              )
            }
            return (
              <p key={`${i}-${j}`}>
                <Inline text={para.trim().replace(/\n/g, ' ')} />
              </p>
            )
          })
      })}
    </div>
  )
}

function Body({ entry, demo }: { entry: Entry; demo: DemoEntry }) {
  switch (entry.kind) {
    case 'user':
      return <p className="rounded-md border border-border bg-muted/50 px-3 py-2 text-body-sm">{entry.text}</p>
    case 'agent':
      return <AgentText text={entry.text} />
    case 'shell':
    case 'browser':
      return (
        <>
          <CodeBlock code={entry.command} prefix="$ " copyLabel="Copy command" accent={entry.kind} />
          {entry.result && (
            <Result
              label={entry.kind === 'shell' && entry.blocked ? 'Output · blocked' : 'Output'}
              text={entry.result}
              blocked={entry.kind === 'shell' && entry.blocked}
            />
          )}
        </>
      )
    case 'mcp': {
      // Arguments and results come from the client's session log; the terminal only shows the tool name.
      const json = JSON.stringify({ tool: entry.tool, arguments: entry.args ?? {} }, null, 2)
      return (
        <>
          <CodeBlock code={json} copyLabel="Copy JSON" copyVisibleLabel="JSON" accent="mcp">
            <span className="text-accent-pink">{entry.tool}</span>
          </CodeBlock>
          {entry.args && <Result label="Request" text={JSON.stringify(entry.args, null, 2)} />}
          {entry.result && <Result label="Response" text={entry.result} />}
        </>
      )
    }
    case 'skill':
      return <p className="pt-0.5 font-mono text-[13px]">{entry.name}</p>
    case 'file':
      return (
        <>
          <div className="mb-1.5 flex items-center gap-2 font-mono text-[13px]">
            {entry.name}
            {entry.tag && <Tag kind="splunk">{entry.tag}</Tag>}
          </div>
          {entry.artifact === 'dashboard' && demo.dashboardJson && (
            <CodeBlock code={demo.dashboardJson.trim()} copyLabel="Copy dashboard JSON" accent="file" maxLines={14} />
          )}
          {entry.artifact === 'source' && demo.sourceCode && (
            <CodeBlock code={demo.sourceCode.trim()} copyLabel="Copy script" accent="file" maxLines={40} />
          )}
        </>
      )
  }
}

export function TranscriptEntry({ entry, demo }: { entry: Entry; demo: DemoEntry }) {
  const base = ACTORS[entry.kind]
  const actor = entry.kind === 'shell' && entry.by === 'user' ? { ...base, verb: 'You ran' } : base
  return (
    <li className="grid gap-2 border-b border-border-subtle py-3 last:border-b-0 md:grid-cols-[170px_minmax(0,1fr)] md:gap-4">
      <div className="flex items-start gap-2.5">
        <span aria-hidden className={cn('grid size-6 shrink-0 place-items-center rounded-md', actor.tone)}>
          <actor.Icon className="size-3.5" />
        </span>
        <div className="text-[13px] leading-4">
          <span className="font-semibold">{actor.who}</span>
          <span className="block text-[12px] text-subtle-foreground">
            {actor.verb} · <time className="font-mono">{formatClock(entry.t)}</time>
          </span>
        </div>
      </div>
      <div className="min-w-0">
        <Body entry={entry} demo={demo} />
      </div>
    </li>
  )
}
