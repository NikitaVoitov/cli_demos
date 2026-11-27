import { useEffect, useRef, useState } from 'react'
import { Maximize2, Minimize2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { DemoEntry } from '@/types/content.types'
import { HeaderButton, PaneFrame } from '../TerminalPane/TerminalPane'

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
  const rootRef = useRef<HTMLDivElement>(null)
  const [fullscreen, setFullscreen] = useState(false)

  useEffect(() => {
    const onChange = () => setFullscreen(document.fullscreenElement === rootRef.current)
    document.addEventListener('fullscreenchange', onChange)
    return () => document.removeEventListener('fullscreenchange', onChange)
  }, [])

  const toggleFullscreen = () => {
    if (document.fullscreenElement) void document.exitFullscreen()
    else void rootRef.current?.requestFullscreen()
  }

  return (
    <div ref={rootRef} className={cn('flex min-w-0 flex-col', fullscreen && 'h-full bg-background p-2')}>
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
        actions={
          shot && (
            <HeaderButton label={fullscreen ? 'Exit screenshot fullscreen' : 'Screenshot fullscreen'} onClick={toggleFullscreen}>
              {fullscreen ? <Minimize2 aria-hidden className="size-3.5" /> : <Maximize2 aria-hidden className="size-3.5" />}
            </HeaderButton>
          )
        }
        focused={published}
        className={fullscreen ? 'flex-1' : 'min-[1100px]:h-[414px]'}
      >
        <div className={cn('relative flex-1', fullscreen ? 'overflow-y-auto' : 'overflow-hidden')}>
          {shot ? (
            // The pane crops a screenshot to its top; fullscreen scrolls the whole page, such as a CI run's summary.
            <img
              src={shot.src}
              alt={shot.alt}
              className={cn(
                'block w-full',
                fullscreen
                  ? 'mx-auto h-auto max-w-[1600px]'
                  : 'aspect-[64/45] object-cover object-top min-[1100px]:aspect-auto min-[1100px]:size-full',
              )}
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
    </div>
  )
}
