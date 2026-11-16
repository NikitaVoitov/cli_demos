import logoUrl from '@/assets/images/splunk-by-cisco-light.svg'
import { Button } from '@/components/ui/button'
import { APP_CONFIG } from '@/config/app.config'

export function SiteHeader() {
  return (
    <header className="flex h-16 items-center gap-4">
      <a href={APP_CONFIG.splunkHomeUrl} aria-label="Splunk homepage" className="shrink-0 rounded-sm">
        <img src={logoUrl} alt="" width={88} height={32} className="h-8 w-auto" />
      </a>
      <a
        href="#main"
        className="sr-only rounded-md bg-primary px-3 py-2 text-button text-primary-foreground focus:not-sr-only"
      >
        Skip to main content
      </a>
      <span aria-hidden className="h-6 w-px bg-border" />
      <span className="text-body-sm text-muted-foreground">{APP_CONFIG.productName}</span>
      <span className="flex-1" />
      <Button asChild variant="outline" size="pill">
        <a href={APP_CONFIG.getSplunkctlUrl}>Get splunkctl</a>
      </Button>
    </header>
  )
}
