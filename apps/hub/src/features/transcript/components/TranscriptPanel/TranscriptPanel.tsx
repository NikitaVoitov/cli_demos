import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion'
import { cn } from '@/lib/utils'
import type { DemoEntry } from '@/types/content.types'
import { formatClock } from '@/utils/formatters/time'
import { TranscriptEntry } from '../TranscriptEntry/TranscriptEntry'

export function TranscriptPanel({ entry }: { entry: DemoEntry }) {
  const transcript = entry.transcript
  if (!transcript) return <p className="text-body-sm text-muted-foreground">No transcript yet.</p>

  const labelOf = (id: string) => entry.chapters.find((chapter) => chapter.id === id)
  const defaultOpen = transcript.chapters.map((chapter) => chapter.id).filter((id) => id !== 'deploy')

  return (
    <div>
      <h2 className="sr-only">Transcript</h2>
      {transcript.placeholder && (
        <p className="mb-3 text-[13px] text-subtle-foreground">
          This transcript is a placeholder written from the mockups. It will be rewritten from the real recorded run.
        </p>
      )}
      <Accordion type="multiple" defaultValue={defaultOpen} className="flex flex-col gap-2.5">
        {transcript.chapters.map((chapter, i) => {
          const meta = labelOf(chapter.id)
          return (
            <AccordionItem key={chapter.id} value={chapter.id} className="rounded-lg border border-border bg-card/60 not-last:border-b">
              <AccordionTrigger className="items-center justify-start gap-3 rounded-lg px-3.5 py-3 hover:no-underline **:data-[slot=accordion-trigger-icon]:ml-0">
                <span
                  aria-hidden
                  className={cn(
                    'grid size-5 shrink-0 place-items-center rounded-full text-[11px]',
                    chapter.gate ? 'bg-gate/20 text-gate' : 'bg-muted text-muted-foreground',
                  )}
                >
                  {i + 1}
                </span>
                <span className="text-[14px] font-semibold">{meta?.label ?? chapter.id}</span>
                <span className="truncate text-[12px] font-normal text-subtle-foreground">{chapter.summary}</span>
                <span className="ml-auto font-mono text-[12px] font-normal text-subtle-foreground">
                  {formatClock(meta?.t ?? 0)}
                </span>
              </AccordionTrigger>
              <AccordionContent className="border-t border-border-subtle px-3.5 pb-0">
                <ul>
                  {chapter.entries.map((item, j) => (
                    <TranscriptEntry key={j} entry={item} demo={entry} />
                  ))}
                </ul>
              </AccordionContent>
            </AccordionItem>
          )
        })}
      </Accordion>
    </div>
  )
}
