import type { ComponentProps } from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { UserRound } from 'lucide-react'
import { AGENT_DOT } from '@/constants/taxonomy'
import { cn } from '@/lib/utils'

const tagVariants = cva('inline-flex items-center gap-1.5 rounded-sm px-2 py-1 text-tag whitespace-nowrap', {
  variants: {
    kind: {
      // Personas are people, not products: a round pill with an icon so they never read as a tool tag.
      persona: 'rounded-full bg-info/12 pr-2.5 pl-2 text-info',
      agent: 'bg-muted text-foreground',
      tech: 'bg-muted/60 text-muted-foreground',
      splunk: 'border border-primary/70 text-accent-pink',
      soon: 'border border-dashed border-border-strong text-muted-foreground',
      gate: 'bg-gate/15 text-gate',
      success: 'bg-success/15 text-success',
    },
  },
  defaultVariants: { kind: 'tech' },
})

type TagProps = ComponentProps<'span'> & VariantProps<typeof tagVariants>

export function Tag({ kind, className, children, ...props }: TagProps) {
  return (
    <span className={cn(tagVariants({ kind }), className)} {...props}>
      {kind === 'persona' && <UserRound aria-hidden className="size-3.5" />}
      {kind === 'agent' && typeof children === 'string' && (
        <span aria-hidden className="size-2 rounded-full" style={{ backgroundColor: AGENT_DOT[children] }} />
      )}
      {children}
    </span>
  )
}
