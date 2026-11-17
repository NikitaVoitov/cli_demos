import type { DemoEntry } from '@/types/content.types'
import { PaneFrame } from '../TerminalPane/TerminalPane'

interface SplunkWebPaneProps {
  entry: DemoEntry
  published: boolean
  /** A `browser.steps` screenshot to show instead of the waiting state, while its stretch of the cast plays. */
  step?: NonNullable<DemoEntry['browserSteps']>[number]
  declined: boolean
}

export function SplunkWebPane({ entry, published, step, declined }: SplunkWebPaneProps) {
  const browser = entry.scenario.browser!
  const copy = entry.content.browser
  const resultApp = copy?.title ?? 'Splunk Web'
  const shot = published && entry.screenshotUrl
    ? { src: entry.screenshotUrl, alt: copy?.alt ?? `The result in ${resultApp}`, object: browser.object, app: resultApp }
    : step
      ? { src: step.url, alt: step.alt, object: step.object, app: step.title ?? resultApp }
      : undefined
  const app = shot?.app ?? resultApp

  return (
    <PaneFrame
      title={app}
      aside={
        <>
          {shot && (
            <span className="shrink-0 rounded-sm bg-primary px-1.5 py-px text-[10px] font-semibold text-primary-foreground">
              Now: {app}
            </span>
          )}
          <span className="truncate">{shot?.object ?? browser.object}</span>
        </>
      }
      focused={published}
      className="min-[1100px]:h-[414px]"
    >
      <div className="relative flex-1 overflow-hidden">
        {shot ? (
          // A stacked pane shows the whole screenshot; beside the terminal it fills the pane and crops the bottom.
          <img
            src={shot.src}
            alt={shot.alt}
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
