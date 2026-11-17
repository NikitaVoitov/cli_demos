import { useState } from 'react'
import { PanelLeftOpen } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Sheet, SheetContent, SheetDescription, SheetTitle, SheetTrigger } from '@/components/ui/sheet'
import { useCatalogStore } from '@/store/useCatalogStore'
import { useCatalogView } from '../../hooks/useCatalogView'
import { ActiveFilters } from '../ActiveFilters/ActiveFilters'
import { CategoryPills } from '../CategoryPills/CategoryPills'
import { DemoCard } from '../DemoCard/DemoCard'
import { FacetGroups } from '../FacetGroups/FacetGroups'

export function DemoDrawer() {
  const [open, setOpen] = useState(false)
  const selectedId = useCatalogStore((state) => state.selectedId)
  const select = useCatalogStore((state) => state.select)
  const { results, total, activeFilters } = useCatalogView()

  const triggerLabel = `Browse demos, ${results.length} of ${total} shown${
    activeFilters ? `, ${activeFilters} ${activeFilters === 1 ? 'filter' : 'filters'} active` : ''
  }`

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button variant="outline" size="sm" className="rounded-md border-border px-2.5" aria-label={triggerLabel}>
          <PanelLeftOpen aria-hidden />
          <span aria-hidden>Demos</span>
          <span aria-hidden className="rounded-full bg-muted px-1.5 py-0.5 text-[11px] leading-none">
            {results.length}
          </span>
          {activeFilters > 0 && (
            <span aria-hidden className="rounded-full bg-primary px-1.5 py-0.5 text-[11px] leading-none text-primary-foreground">
              {activeFilters} {activeFilters === 1 ? 'filter' : 'filters'}
            </span>
          )}
        </Button>
      </SheetTrigger>

      <SheetContent
        side="left"
        className="w-full gap-0 border-border-strong p-0 data-[side=left]:w-full data-[side=left]:sm:max-w-[420px]"
      >
        <div className="flex flex-col gap-3 border-b border-border-subtle p-4 pr-12">
          <SheetTitle className="text-[21px] leading-[23.1px] font-semibold">Demos</SheetTitle>
          <SheetDescription className="sr-only">Filter the demos, then pick one to watch.</SheetDescription>
        </div>

        {/* macOS hides the scrollbar until you scroll, so the bottom fade shows that more demos follow. */}
        <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto p-4 pb-12 [mask-image:linear-gradient(to_bottom,black_calc(100%-48px),transparent)]">
          <CategoryPills />
          <FacetGroups />
          <ActiveFilters />

          <section aria-labelledby="drawer-results" className="flex flex-col gap-2.5">
            <h3 id="drawer-results" className="text-tag tracking-wider text-muted-foreground uppercase">
              {results.length} {results.length === 1 ? 'demo' : 'demos'}
            </h3>
            <p role="status" className="sr-only">
              {results.length} {results.length === 1 ? 'demo matches' : 'demos match'}
            </p>
            <ul className="flex flex-col gap-2.5">
              {results.map((entry) => (
                <li key={entry.id}>
                  <DemoCard
                    entry={entry}
                    selected={entry.id === selectedId}
                    onSelect={() => {
                      select(entry.id)
                      setOpen(false)
                    }}
                  />
                </li>
              ))}
              {results.length === 0 && (
                <li className="rounded-lg border border-dashed border-border p-4 text-body-sm text-muted-foreground">
                  No demos match. Remove a filter or clear them all.
                </li>
              )}
            </ul>
          </section>
        </div>
      </SheetContent>
    </Sheet>
  )
}
