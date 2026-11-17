import { CircleSlash, Pause, RotateCcw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { usePlaybackStore } from '@/store/usePlaybackStore'
import type { DemoEntry } from '@/types/content.types'

export function ApprovalBar({ entry }: { entry: DemoEntry }) {
  const status = usePlaybackStore((state) => state.status)
  const approve = usePlaybackStore((state) => state.approve)
  const decline = usePlaybackStore((state) => state.decline)
  const replay = usePlaybackStore((state) => state.replay)
  const gate = entry.scenario.gate
  const copy = entry.content.gate
  if (!gate || !copy) return null

  return (
    <div aria-live="polite">
      {status === 'gate' && (
        <section
          aria-labelledby="gate-title"
          className="mt-3 flex flex-wrap items-center gap-4 rounded-lg border border-gate/40 border-l-4 border-l-gate bg-gate/8 px-4 py-3"
        >
          <span aria-hidden className="grid size-7 shrink-0 place-items-center rounded-full bg-gate text-primary-foreground">
            <Pause className="size-4" fill="currentColor" />
          </span>
          <div className="min-w-0 flex-1">
            <h2 id="gate-title" className="text-body-sm font-semibold text-gate">
              {copy.title}
            </h2>
            <p className="mt-0.5 text-[13px] leading-5 text-muted-foreground">
              splunkctl blocked{' '}
              <code className="rounded-sm border border-border-strong bg-terminal px-1.5 py-px font-mono text-[12px] text-foreground [overflow-wrap:anywhere]">
                {gate.command}
              </code>{' '}
              with{' '}
              <code className="rounded-sm border border-border-strong bg-terminal px-1.5 py-px font-mono text-[12px] text-foreground">
                CONFIRMATION_REQUIRED
              </code>
              . {copy.body}
            </p>
          </div>
          <div className="flex w-full shrink-0 gap-2 sm:w-auto">
            <Button className="flex-1 sm:flex-none" onClick={approve}>
              {copy.approve}
            </Button>
            <Button variant="outline" className="flex-1 sm:flex-none" onClick={decline}>
              {copy.decline}
            </Button>
          </div>
        </section>
      )}

      {status === 'declined' && (
        <section
          aria-labelledby="declined-title"
          className="mt-3 flex flex-wrap items-center gap-4 rounded-lg border border-border-strong border-l-4 border-l-muted-foreground bg-card px-4 py-3"
        >
          <CircleSlash aria-hidden className="size-6 shrink-0 text-muted-foreground" />
          <div className="min-w-0 flex-1">
            <h2 id="declined-title" className="text-body-sm font-semibold">
              {copy.declinedTitle}
            </h2>
            <p className="mt-0.5 text-[13px] leading-5 text-muted-foreground">{copy.declinedBody}</p>
          </div>
          <Button variant="outline" className="w-full sm:w-auto" onClick={replay}>
            <RotateCcw aria-hidden />
            Replay
          </Button>
        </section>
      )}
    </div>
  )
}
