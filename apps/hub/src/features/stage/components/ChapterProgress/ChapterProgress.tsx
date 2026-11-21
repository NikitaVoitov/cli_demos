import { Circle, CircleCheck, CircleDot, CirclePause, CircleX } from 'lucide-react'
import { gatesOf } from '@/lib/gates'
import { cn } from '@/lib/utils'
import { usePlaybackStore } from '@/store/usePlaybackStore'
import type { DemoEntry } from '@/types/content.types'
import { isBeyondGate, stepStates, type StepState } from '../../utils/timeline'

const STATE_STYLE: Record<StepState, string> = {
  done: 'bg-success/15 text-success',
  current: 'bg-primary font-semibold text-primary-foreground',
  gate: 'bg-gate/20 font-semibold text-gate',
  declined: 'bg-muted font-semibold text-muted-foreground',
  upcoming: 'bg-foreground/5 text-subtle-foreground',
}

const STATE_TEXT: Record<StepState, string> = {
  done: 'completed',
  current: 'current step',
  gate: 'waiting for your approval',
  declined: 'declined',
  upcoming: 'not reached yet',
}

const STATE_ICON = { done: CircleCheck, current: CircleDot, gate: CirclePause, declined: CircleX, upcoming: Circle }

export function ChapterProgress({ entry }: { entry: DemoEntry }) {
  const { time, status, decision, gateIndex, controller } = usePlaybackStore()
  const gateT = gatesOf(entry.scenario)[gateIndex]?.t
  const states = stepStates(entry.chapters, { time, status, decision, gateT })

  return (
    <nav aria-label="Demo chapters" className="mt-3">
      <ol className="flex h-7">
        {entry.chapters.map((chapter, i) => {
          const state = states[i]
          const Icon = STATE_ICON[state]
          const blocked = isBeyondGate(chapter.t, decision, gateT)
          const first = i === 0
          const last = i === entry.chapters.length - 1
          const active = state === 'current' || state === 'gate'
          return (
            <li
              key={chapter.id}
              className={cn('flex min-w-0 flex-1', active && 'max-sm:flex-[3]', !first && '-ml-1.5')}
            >
              <button
                type="button"
                aria-current={active ? 'step' : undefined}
                aria-disabled={blocked || undefined}
                title={blocked ? 'Approve the step to continue' : undefined}
                onClick={() => {
                  if (blocked || !controller) return
                  controller.seek(chapter.t)
                }}
                className={cn(
                  'flex w-full min-w-0 items-center justify-center gap-1.5 text-[13px] whitespace-nowrap transition-colors',
                  'focus-visible:outline-offset-[-2px]',
                  blocked ? 'cursor-not-allowed' : 'hover:brightness-125',
                  STATE_STYLE[state],
                  first
                    ? 'rounded-l-md pr-3 pl-2.5 [clip-path:polygon(0_0,calc(100%-9px)_0,100%_50%,calc(100%-9px)_100%,0_100%)]'
                    : last
                      ? 'rounded-r-md pr-2.5 pl-4 [clip-path:polygon(0_0,100%_0,100%_100%,0_100%,9px_50%)]'
                      : 'pr-3 pl-4 [clip-path:polygon(0_0,calc(100%-9px)_0,100%_50%,calc(100%-9px)_100%,0_100%,9px_50%)]',
                )}
              >
                <Icon aria-hidden className="size-3.5 shrink-0" />
                <span className={cn('truncate', !active && 'max-sm:sr-only')}>{chapter.label}</span>
                <span className="sr-only">, {STATE_TEXT[state]}</span>
              </button>
            </li>
          )
        })}
      </ol>
    </nav>
  )
}
