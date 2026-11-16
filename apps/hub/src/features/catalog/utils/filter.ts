import { FACET_GROUPS, type FacetGroupId } from '@/constants/taxonomy'
import type { DemoEntry } from '@/types/content.types'

export type FacetSelection = Record<FacetGroupId, string[]>

export interface CatalogFilters {
  category: string | null
  facets: FacetSelection
}

export const EMPTY_FACETS: FacetSelection = { persona: [], agent: [], splunk: [], technologies: [] }

interface MatchOptions {
  ignoreCategory?: boolean
  ignoreGroup?: FacetGroupId
}

/** Values within a group are ORed; groups and the category are ANDed. */
export function matches(entry: DemoEntry, filters: CatalogFilters, options: MatchOptions = {}) {
  if (!options.ignoreCategory && filters.category && entry.content.taxonomy.category !== filters.category) return false
  return FACET_GROUPS.every(({ id }) => {
    if (id === options.ignoreGroup) return true
    const selected = filters.facets[id]
    return selected.length === 0 || selected.some((value) => entry.facets[id].includes(value))
  })
}

export function filterCatalog(entries: DemoEntry[], filters: CatalogFilters) {
  return entries.filter((entry) => matches(entry, filters))
}

/** A group's counts ignore that group's own selection, so selecting one value never hides its alternatives. */
export function facetCounts(entries: DemoEntry[], filters: CatalogFilters) {
  const counts = {} as Record<FacetGroupId, Record<string, number>>
  for (const group of FACET_GROUPS) {
    const pool = entries.filter((entry) => matches(entry, filters, { ignoreGroup: group.id }))
    counts[group.id] = Object.fromEntries(
      group.values.map((value) => [value, pool.filter((entry) => entry.facets[group.id].includes(value)).length]),
    )
  }
  return counts
}

export function categoryCounts(entries: DemoEntry[], filters: CatalogFilters) {
  const pool = entries.filter((entry) => matches(entry, filters, { ignoreCategory: true }))
  const byCategory = new Map<string, number>()
  for (const entry of pool) {
    const category = entry.content.taxonomy.category
    byCategory.set(category, (byCategory.get(category) ?? 0) + 1)
  }
  return { all: pool.length, byCategory }
}

export function activeFilterCount(filters: CatalogFilters) {
  const facets = Object.values(filters.facets).reduce((sum, values) => sum + values.length, 0)
  return facets + (filters.category ? 1 : 0)
}
