import type { DemoEntry } from '@/types/content.types'
import { PaneFrame } from '../TerminalPane/TerminalPane'

interface SplunkWebPaneProps {
  entry: DemoEntry
  published: boolean
  declined: boolean
}

export function SplunkWebPane({ entry, published, declined }: SplunkWebPaneProps) {
  const browser = entry.scenario.browser!
  const copy = entry.content.browser
  const showShot = published && entry.screenshotUrl

  return (
    <PaneFrame
      title="Splunk Web"
      aside={
        <>
          {showShot && (
            <span className="shrink-0 rounded-sm bg-primary px-1.5 py-px text-[10px] font-semibold text-primary-foreground">
              Now: Splunk Web
            </span>
          )}
          <span className="truncate">{browser.object}</span>
        </>
      }
      focused={published}
      className="min-[1100px]:h-[414px]"
    >
      <div className="relative flex-1 overflow-hidden">
        {showShot ? (
          // A stacked pane shows the whole screenshot; beside the terminal it fills the pane and crops the bottom.
          <img
            src={entry.screenshotUrl}
            alt={copy?.alt ?? 'The deployed dashboard in Splunk Web'}
            className="block h-auto w-full min-[1100px]:size-full min-[1100px]:object-cover min-[1100px]:object-top"
          />
        ) : (
          <div className="relative aspect-[6/5] p-3.5 min-[1100px]:absolute min-[1100px]:inset-0 min-[1100px]:aspect-auto">
            <div aria-hidden className="grid size-full grid-cols-2 grid-rows-[70px_1fr] gap-2.5">
              {Array.from({ length: 4 }, (_, i) => (
                <div key={i} className="rounded-md bg-muted" />
              ))}
            </div>
            <div role="status" className="absolute inset-0 flex flex-col items-center justify-center gap-3 px-4 text-center text-body-sm text-muted-foreground">
              {declined ? (
                'Nothing was published.'
              ) : (
                <>
                  <span aria-hidden className="size-6 animate-spin rounded-full border-[2.5px] border-border-strong border-t-foreground" />
                  {copy?.waiting ?? 'Waiting for the agent to publish the result'}
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </PaneFrame>
  )
}
