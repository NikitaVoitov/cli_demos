import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion'
import { FACET_GROUPS, PERSONAS } from '@/constants/taxonomy'
import { cn } from '@/lib/utils'
import { useCatalogStore } from '@/store/useCatalogStore'
import { useCatalogView } from '../../hooks/useCatalogView'

export function FacetGroups() {
  const facets = useCatalogStore((state) => state.facets)
  const toggleFacet = useCatalogStore((state) => state.toggleFacet)
  const { facetCounts } = useCatalogView()

  return (
    <Accordion type="multiple" className="rounded-lg border border-border">
      {FACET_GROUPS.map((group) => {
        const selected = facets[group.id]
        return (
          <AccordionItem key={group.id} value={group.id} className="border-border-subtle not-last:border-b">
            <AccordionTrigger className="items-center rounded-none px-3 py-2.5 text-[13px] font-semibold hover:no-underline">
              <span className="flex items-center gap-2">
                {group.label}
                {selected.length > 0 && (
                  <span className="rounded-full bg-primary px-1.5 py-0.5 text-[11px] leading-none text-primary-foreground">
                    {selected.length}
                    <span className="sr-only"> selected</span>
                  </span>
                )}
              </span>
            </AccordionTrigger>
            <AccordionContent className="px-3 pb-3">
              <div role="group" aria-label={group.label} className="flex flex-wrap gap-2">
                {group.values.map((value) => {
                  const isOn = selected.includes(value)
                  const count = facetCounts[group.id][value] ?? 0
                  return (
                    <button
                      key={value}
                      type="button"
                      aria-pressed={isOn}
                      title={group.id === 'persona' ? PERSONAS[value] : undefined}
                      disabled={count === 0 && !isOn}
                      onClick={() => toggleFacet(group.id, value)}
                      className={cn(
                        'inline-flex h-7 items-center gap-1.5 rounded-full border px-3 text-[13px] transition-colors',
                        isOn
                          ? 'border-primary bg-primary font-semibold text-primary-foreground'
                          : 'border-secondary-border text-foreground hover:bg-secondary-hover',
                        'disabled:cursor-not-allowed disabled:border-border disabled:text-subtle-foreground disabled:opacity-60',
                      )}
                    >
                      {value}
                      <span className={cn('text-[11px]', isOn ? 'text-primary-foreground/80' : 'text-subtle-foreground')}>
                        {count}
                        <span className="sr-only"> demos</span>
                      </span>
                    </button>
                  )
                })}
              </div>
            </AccordionContent>
          </AccordionItem>
        )
      })}
    </Accordion>
  )
}
