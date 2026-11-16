import { create } from 'zustand'
import type { FacetGroupId } from '@/constants/taxonomy'
import { EMPTY_FACETS, type CatalogFilters } from '@/features/catalog/utils/filter'
import { DEFAULT_DEMO_ID } from '@/lib/content'

interface CatalogState extends CatalogFilters {
  selectedId: string | undefined
  setCategory: (category: string | null) => void
  toggleFacet: (group: FacetGroupId, value: string) => void
  clearFilters: () => void
  select: (id: string) => void
}

export const useCatalogStore = create<CatalogState>((set) => ({
  category: null,
  facets: EMPTY_FACETS,
  selectedId: DEFAULT_DEMO_ID,
  setCategory: (category) => set({ category }),
  toggleFacet: (group, value) =>
    set((state) => {
      const current = state.facets[group]
      const next = current.includes(value) ? current.filter((v) => v !== value) : [...current, value]
      return { facets: { ...state.facets, [group]: next } }
    }),
  clearFilters: () => set({ facets: EMPTY_FACETS, category: null }),
  select: (id) => set({ selectedId: id }),
}))
