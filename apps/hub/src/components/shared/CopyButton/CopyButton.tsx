import { useEffect, useState } from 'react'
import { Check, Copy } from 'lucide-react'
import { cn } from '@/lib/utils'

interface CopyButtonProps {
  text: string
  /** Accessible name describing the result, e.g. "Copy command". */
  label: string
  visibleLabel?: string
  className?: string
}

export function CopyButton({ text, label, visibleLabel = 'Copy', className }: CopyButtonProps) {
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    if (!copied) return
    const id = window.setTimeout(() => setCopied(false), 1600)
    return () => window.clearTimeout(id)
  }, [copied])

  async function copy() {
    await navigator.clipboard.writeText(text)
    setCopied(true)
  }

  return (
    <button
      type="button"
      onClick={copy}
      aria-label={label}
      className={cn(
        'inline-flex shrink-0 items-center gap-1.5 rounded-sm border border-border px-2 py-1 text-xs text-muted-foreground',
        'hover:border-border-strong hover:text-foreground',
        className,
      )}
    >
      {copied ? <Check aria-hidden className="size-3.5 text-success" /> : <Copy aria-hidden className="size-3.5" />}
      <span>{copied ? 'Copied' : visibleLabel}</span>
      <span className="sr-only" role="status">
        {copied ? 'Copied to clipboard' : ''}
      </span>
    </button>
  )
}
