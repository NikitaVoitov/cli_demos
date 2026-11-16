import { Play } from 'lucide-react'
import { Tag } from '@/components/shared/Tag'
import { PERSONAS } from '@/constants/taxonomy'
import { cn } from '@/lib/utils'
import type { DemoEntry } from '@/types/content.types'

interface DemoCardProps {
  entry: DemoEntry
  selected: boolean
  onSelect: () => void
}

export function DemoCard({ entry, selected, onSelect }: DemoCardProps) {
  return (
    <button
      type="button"
      aria-current={selected ? 'true' : undefined}
      onClick={onSelect}
      className={cn(
        'flex w-full flex-col gap-2.5 rounded-lg border p-3.5 text-left transition-colors',
        selected
          ? 'border-primary bg-card shadow-[inset_3px_0_0_var(--action-primary)]'
          : 'border-border bg-card/60 hover:border-border-strong',
      )}
    >
      <span className="flex items-start justify-between gap-3">
        <span className="text-[16px] leading-5 font-semibold">{entry.content.title}</span>
        {selected && (
          <span className="mt-0.5 inline-flex shrink-0 items-center gap-1 text-[12px] font-semibold text-accent-pink">
            <Play aria-hidden className="size-3" fill="currentColor" />
            Selected
          </span>
        )}
      </span>
      {entry.facets.persona.length > 0 && (
        <span className="flex flex-wrap gap-1.5">
          <span className="sr-only">For </span>
          {entry.facets.persona.map((value) => (
            <Tag key={value} kind="persona" title={PERSONAS[value]}>
              {value}
            </Tag>
          ))}
        </span>
      )}
      {/* Agent first, then the Splunk pieces, then third-party tools, then status. */}
      <span className="flex flex-wrap gap-1.5">
        <Tag kind="agent">{entry.scenario.client.label}</Tag>
        {entry.facets.splunk.map((value) => (
          <Tag key={value} kind="splunk">
            {value}
          </Tag>
        ))}
        {entry.facets.technologies.map((value) => (
          <Tag key={value} kind="tech">
            {value}
          </Tag>
        ))}
        {!entry.playable && <Tag kind="soon">Coming soon</Tag>}
      </span>
    </button>
  )
}
