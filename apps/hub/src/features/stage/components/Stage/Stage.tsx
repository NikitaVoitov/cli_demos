import { usePlaybackStore } from '@/store/usePlaybackStore'
import type { DemoEntry } from '@/types/content.types'
import { ApprovalBar } from '../ApprovalBar/ApprovalBar'
import { ChapterProgress } from '../ChapterProgress/ChapterProgress'
import { SplunkWebPane } from '../SplunkWebPane/SplunkWebPane'
import { PaneFrame, TerminalPane } from '../TerminalPane/TerminalPane'

function GateAnnouncer() {
  const status = usePlaybackStore((state) => state.status)
  const message =
    status === 'gate'
      ? 'Playback paused. The change is waiting for your approval.'
      : status === 'declined'
        ? 'Declined. No change was made.'
        : status === 'ended'
          ? 'The demo has finished.'
          : ''
  return (
    <p role="status" className="sr-only">
      {message}
    </p>
  )
}

export function Stage({ entry }: { entry: DemoEntry }) {
  const time = usePlaybackStore((state) => state.time)
  const status = usePlaybackStore((state) => state.status)
  const decision = usePlaybackStore((state) => state.decision)

  if (!entry.playable) {
    return (
      <PaneFrame title="zsh">
        <div className="flex h-[420px] flex-col items-center justify-center gap-2 p-8 text-center">
          <p className="text-h4">Recording coming soon</p>
          <p className="max-w-[52ch] text-body-sm text-muted-foreground">
            This demo is in the catalog so you can see what's planned. Nothing has been recorded yet. In the meantime, try
            the dashboard demo.
          </p>
        </div>
      </PaneFrame>
    )
  }

  const chapterTime = (id?: string) => entry.chapters.find((chapter) => chapter.id === id)?.t
  const showAt = chapterTime(entry.scenario.browser?.showAt) ?? Infinity
  const published = decision === 'approved' && (time >= showAt || status === 'ended')
  const step = published || status === 'ended' ? undefined : entry.browserSteps?.find((s) => time >= s.from && time < s.until)

  return (
    <>
      <GateAnnouncer />
      {entry.split ? (
        <div className="grid gap-3 min-[1100px]:grid-cols-2">
          <TerminalPane entry={entry} focused={!published} />
          <SplunkWebPane entry={entry} published={published} step={step} declined={decision === 'declined'} />
        </div>
      ) : (
        <TerminalPane entry={entry} focused={false} />
      )}
      <ApprovalBar entry={entry} />
      <ChapterProgress entry={entry} />
    </>
  )
}
