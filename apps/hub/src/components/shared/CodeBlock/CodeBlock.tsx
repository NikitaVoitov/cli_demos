import { useState, type ReactNode } from 'react'
import { CopyButton } from '@/components/shared/CopyButton'
import { cn } from '@/lib/utils'

interface CodeBlockProps {
  code: string
  copyLabel: string
  copyVisibleLabel?: string
  /** Shown before the code, e.g. "$ " for shell commands; never copied. */
  prefix?: string
  accent?: 'shell' | 'mcp' | 'browser' | 'file'
  /** Collapse long blocks to this many lines with a "Show all" toggle. */
  maxLines?: number
  children?: ReactNode
}

const accentClass = {
  shell: 'border-l-success',
  mcp: 'border-l-primary',
  browser: 'border-l-info',
  file: 'border-l-artifact',
}

export function CodeBlock({ code, copyLabel, copyVisibleLabel, prefix, accent, maxLines, children }: CodeBlockProps) {
  const lines = code.split('\n')
  const collapsible = maxLines !== undefined && lines.length > maxLines
  const [expanded, setExpanded] = useState(false)
  const shown = collapsible && !expanded ? lines.slice(0, maxLines).join('\n') : code

  return (
    <div
      className={cn(
        'flex items-start gap-3 rounded-md border border-border bg-terminal px-3 py-2.5',
        accent && 'border-l-2',
        accent && accentClass[accent],
      )}
    >
      <div className="min-w-0 flex-1">
        <pre
          className={cn(
            'overflow-x-auto font-mono text-[13px] leading-5 text-terminal-foreground',
            collapsible && expanded && 'max-h-[26rem] overflow-y-auto',
          )}
        >
          <code>
            {prefix && (
              <span aria-hidden className="select-none text-subtle-foreground">
                {prefix}
              </span>
            )}
            {children ?? shown}
          </code>
        </pre>
        {collapsible && (
          <button
            type="button"
            aria-expanded={expanded}
            onClick={() => setExpanded((value) => !value)}
            className="mt-1.5 text-xs font-semibold text-accent-pink underline-offset-2 hover:underline"
          >
            {expanded ? 'Show fewer lines' : `Show all ${lines.length} lines`}
          </button>
        )}
      </div>
      <CopyButton text={code} label={copyLabel} visibleLabel={copyVisibleLabel} />
    </div>
  )
}
