import { cn } from '@/lib/utils'
import { useCatalogStore } from '@/store/useCatalogStore'
import { useCatalogView } from '../../hooks/useCatalogView'

function Pill({ label, count, active, onClick }: { label: string; count: number; active: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      className={cn(
        'inline-flex h-8 items-center gap-2 rounded-full border px-3 text-[13px] font-medium transition-colors',
        active
          ? 'border-primary bg-primary text-primary-foreground'
          : 'border-border text-muted-foreground hover:border-border-strong hover:text-foreground',
      )}
    >
      {label}
      <span
        className={cn(
          'rounded-full px-1.5 py-0.5 text-[11px] leading-none font-semibold',
          active ? 'bg-primary-foreground/15' : 'bg-muted',
        )}
      >
        {count}
        <span className="sr-only"> demos</span>
      </span>
    </button>
  )
}

export function CategoryPills() {
  const category = useCatalogStore((state) => state.category)
  const setCategory = useCatalogStore((state) => state.setCategory)
  const { categories, categoryCounts } = useCatalogView()

  return (
    <div role="group" aria-label="Category" className="flex flex-wrap items-center gap-2">
      <Pill label="All" count={categoryCounts.all} active={category === null} onClick={() => setCategory(null)} />
      {categories.map((name) => (
        <Pill
          key={name}
          label={name}
          count={categoryCounts.byCategory.get(name) ?? 0}
          active={category === name}
          onClick={() => setCategory(category === name ? null : name)}
        />
      ))}
    </div>
  )
}
