import { useRef } from 'react'
import { useMediaQuery } from '@/hooks/useMediaQuery'
import { cn } from '@/lib/utils'
import type { DemoEntry } from '@/types/content.types'
import { useCastPlayer } from '../../hooks/useCastPlayer'
import { CaptionOverlay, CaptionsToggle } from '../NarrationCaption/NarrationCaption'
import '../../styles/player-theme.css'

export function PaneFrame({
  title,
  aside,
  actions,
  focused,
  className,
  children,
}: {
  title: string
  aside?: React.ReactNode
  /** Controls on the right of a terminal-style header, which keeps its centered title. */
  actions?: React.ReactNode
  focused?: boolean
  className?: string
  children: React.ReactNode
}) {
  return (
    <div
      className={cn(
        'flex min-w-0 flex-col overflow-hidden rounded-lg border bg-terminal',
        focused ? 'border-primary shadow-[0_0_0_1px_var(--action-primary)]' : 'border-border',
        className,
      )}
    >
      <div className="relative flex h-7 shrink-0 items-center gap-1.5 bg-terminal-chrome px-3 text-[11px] text-muted-foreground">
        {aside === undefined && (
          <span aria-hidden className="flex gap-1.5">
            <span className="size-2.5 rounded-full bg-terminal-dot-close" />
            <span className="size-2.5 rounded-full bg-terminal-dot-min" />
            <span className="size-2.5 rounded-full bg-terminal-dot-max" />
          </span>
        )}
        <span className={cn(aside === undefined ? 'absolute inset-x-0 text-center' : 'font-semibold text-foreground')}>
          {title}
        </span>
        {aside && <span className="ml-auto flex min-w-0 items-center gap-2 truncate">{aside}</span>}
        {actions && <span className={cn('relative flex items-center gap-2', aside === undefined && 'ml-auto')}>{actions}</span>}
      </div>
      {children}
    </div>
  )
}

/** A small control for a pane header, such as fullscreen. */
export function HeaderButton({ label, onClick, children }: {
  label: string
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      type="button"
      title={label}
      aria-label={label}
      onClick={onClick}
      className="flex h-5 items-center gap-1 rounded-sm px-1.5 font-semibold text-subtle-foreground hover:bg-foreground/10"
    >
      {children}
    </button>
  )
}

export function TerminalPane({ entry, focused }: { entry: DemoEntry; focused: boolean }) {
  const containerRef = useRef<HTMLDivElement>(null)
  const wide = useMediaQuery('(min-width: 1100px)')
  useCastPlayer(entry, containerRef, wide ? 'both' : 'width')
  const { cols, rows } = entry.scenario.terminal ?? { cols: 88, rows: 28 }

  return (
    <PaneFrame title={entry.terminalTitle} focused={focused} actions={<CaptionsToggle entry={entry} />}>
      <div
        ref={containerRef}
        role="region"
        aria-label={`Terminal recording of ${entry.scenario.client.label}. The Transcript tab has the same session as text.`}
        // A full-width pane follows the recording's shape (a monospace cell is about 0.6 x 1.33 em, plus the
        // control bar), so the whole screen and the controls stay inside the frame.
        className={cn('w-full', wide && (entry.split ? 'h-[386px]' : 'max-h-[640px]'))}
        style={wide && !entry.split ? { aspectRatio: `${cols * 0.6} / ${rows * 1.33 + 3}` } : undefined}
      />
      <CaptionOverlay entry={entry} containerRef={containerRef} />
    </PaneFrame>
  )
}
