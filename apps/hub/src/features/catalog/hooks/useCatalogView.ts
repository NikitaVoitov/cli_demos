import { useMemo } from 'react'
import { CATALOG } from '@/lib/content'
import { useCatalogStore } from '@/store/useCatalogStore'
import { activeFilterCount, categoryCounts, facetCounts, filterCatalog } from '../utils/filter'

export function useCatalogView() {
  const category = useCatalogStore((state) => state.category)
  const facets = useCatalogStore((state) => state.facets)

  return useMemo(() => {
    const filters = { category, facets }
    return {
      results: filterCatalog(CATALOG, filters),
      total: CATALOG.length,
      activeFilters: activeFilterCount(filters),
      facetCounts: facetCounts(CATALOG, filters),
      categoryCounts: categoryCounts(CATALOG, filters),
      // Category pills list only categories that have at least one demo in the catalog.
      categories: [...new Set(CATALOG.map((entry) => entry.content.taxonomy.category))],
    }
  }, [category, facets])
}
