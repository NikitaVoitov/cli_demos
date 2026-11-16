import type { ReactNode } from 'react'
import { SiteHeader } from '@/components/shared/SiteHeader'

export function MainLayout({ children }: { children: ReactNode }) {
  return (
    <div className="relative min-h-dvh overflow-x-clip">
      {/* Decorative brand edge: kept to the page top so it never sits behind text or controls. */}
      <div aria-hidden className="pointer-events-none absolute inset-x-0 top-0 h-[3px] bg-linear-to-r from-primary to-gate" />
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 -top-32 mx-auto h-64 max-w-[1200px] rounded-[50%] bg-primary/20 blur-3xl"
      />
      <div className="relative mx-auto max-w-[1440px] px-5 pb-12 md:px-10">
        <SiteHeader />
        {children}
      </div>
    </div>
  )
}
