import { Tag } from '@/components/shared/Tag'
import type { DemoEntry } from '@/types/content.types'

export function EvidenceLine({ entry }: { entry: DemoEntry }) {
  const { capture } = entry.scenario
  if (capture?.status !== 'placeholder') return null

  return (
    <p className="mt-2 flex flex-wrap items-center gap-2 text-[12px] text-subtle-foreground">
      <Tag kind="gate" title="This recording is a stand-in built from the mockups. It will be replaced by a real Cursor CLI run.">
        Placeholder recording
      </Tag>
    </p>
  )
}
