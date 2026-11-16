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

  return (
    <PaneFrame title="Splunk Web" aside={browser.object} focused={published} className="h-[414px]">
      <div className="relative flex-1 overflow-hidden">
        {published && entry.screenshotUrl ? (
          <>
            <span className="absolute top-2 right-2 z-10 rounded-sm bg-primary px-2 py-0.5 text-[11px] font-semibold text-primary-foreground">
              Now: Splunk Web
            </span>
            <img
              src={entry.screenshotUrl}
              alt={copy?.alt ?? 'The deployed dashboard in Splunk Web'}
              className="size-full object-cover object-top"
            />
          </>
        ) : (
          <div className="absolute inset-0 p-3.5">
            <div aria-hidden className="grid size-full grid-cols-2 grid-rows-[70px_1fr] gap-2.5">
              {Array.from({ length: 4 }, (_, i) => (
                <div key={i} className="rounded-md bg-muted" />
              ))}
            </div>
            <div role="status" className="absolute inset-0 flex flex-col items-center justify-center gap-3 text-body-sm text-muted-foreground">
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
