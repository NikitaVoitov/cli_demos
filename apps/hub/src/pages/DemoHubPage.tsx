import { lazy, Suspense } from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { DemoDrawer } from '@/features/catalog'
import { EvidenceLine, Stage } from '@/features/stage'
import { MainLayout } from '@/layout/MainLayout'
import { getDemo } from '@/lib/content'
import { useCatalogStore } from '@/store/useCatalogStore'

const TranscriptPanel = lazy(() => import('@/features/transcript').then((m) => ({ default: m.TranscriptPanel })))
const HowItWorksPanel = lazy(() => import('@/features/how-it-works').then((m) => ({ default: m.HowItWorksPanel })))

const tabTrigger =
  'flex-none rounded-none px-0.5 pb-2 text-[14px] font-medium text-muted-foreground data-active:font-semibold data-active:text-foreground after:bg-primary'

export function DemoHubPage() {
  const entry = getDemo(useCatalogStore((state) => state.selectedId))

  return (
    <MainLayout>
      <main id="main" tabIndex={-1} className="outline-none">
        <div className="mt-1 mb-5 flex flex-wrap items-center gap-x-4 gap-y-2">
          <DemoDrawer />
          <h1 className="min-w-0 text-display">{entry?.content.title ?? 'Headless Splunk Demos'}</h1>
        </div>

        {entry && (
          <section aria-label={`${entry.content.title} demo`}>
            <Stage key={entry.id} entry={entry} />
            {entry.playable && (
              <Tabs defaultValue="how" className="mt-3 gap-0">
                <TabsList variant="line" className="h-auto gap-6 border-b border-border-subtle p-0">
                  <TabsTrigger value="how" className={tabTrigger}>
                    How it works
                  </TabsTrigger>
                  <TabsTrigger value="transcript" className={tabTrigger}>
                    Transcript
                  </TabsTrigger>
                </TabsList>
                <EvidenceLine entry={entry} />
                <Suspense fallback={<p className="mt-4 text-body-sm text-muted-foreground">Loading…</p>}>
                  <TabsContent value="how" className="mt-4">
                    <HowItWorksPanel entry={entry} />
                  </TabsContent>
                  <TabsContent value="transcript" className="mt-4">
                    <TranscriptPanel entry={entry} />
                  </TabsContent>
                </Suspense>
              </Tabs>
            )}
          </section>
        )}
      </main>
    </MainLayout>
  )
}
