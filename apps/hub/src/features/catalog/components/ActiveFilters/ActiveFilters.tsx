import { X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { FACET_GROUPS } from '@/constants/taxonomy'
import { useCatalogStore } from '@/store/useCatalogStore'
import { useCatalogView } from '../../hooks/useCatalogView'

export function ActiveFilters() {
  const facets = useCatalogStore((state) => state.facets)
  const toggleFacet = useCatalogStore((state) => state.toggleFacet)
  const clearFilters = useCatalogStore((state) => state.clearFilters)
  const { activeFilters } = useCatalogView()
  const chips = FACET_GROUPS.flatMap((group) => facets[group.id].map((value) => ({ group: group.id, value })))

  if (activeFilters === 0) return null

  return (
    <div className="flex flex-wrap items-center gap-2">
      <ul aria-label="Active filters" className="contents">
        {chips.map(({ group, value }) => (
          <li key={`${group}:${value}`}>
            <button
              type="button"
              onClick={() => toggleFacet(group, value)}
              aria-label={`Remove filter ${value}`}
              className="inline-flex h-7 items-center gap-1.5 rounded-sm bg-muted px-2.5 text-[13px] text-foreground hover:bg-secondary-hover"
            >
              {value}
              <X aria-hidden className="size-3.5" />
            </button>
          </li>
        ))}
      </ul>
      <Button variant="link" size="sm" className="h-7 px-1" onClick={clearFilters}>
        Clear all
      </Button>
    </div>
  )
}
