import { Captions, CaptionsOff } from 'lucide-react'
import { useEffect, useState, type RefObject } from 'react'
import { createPortal } from 'react-dom'
import { cn } from '@/lib/utils'
import { usePlaybackStore } from '@/store/usePlaybackStore'
import type { DemoEntry } from '@/types/content.types'

function isNarrated(entry: DemoEntry) {
  return Boolean(entry.narrationUrl && entry.captions?.length)
}

/** The player's own wrapper: the element its fullscreen button enlarges, created after the player mounts. */
function usePlayerWrapper(containerRef: RefObject<HTMLDivElement | null>) {
  const [wrapper, setWrapper] = useState<HTMLElement | null>(null)
  useEffect(() => {
    const container = containerRef.current
    if (!container) return
    const find = () => setWrapper(container.querySelector<HTMLElement>('.ap-wrapper'))
    find()
    const observer = new MutationObserver(find)
    observer.observe(container, { childList: true })
    return () => observer.disconnect()
  }, [containerRef])
  return wrapper
}

/**
 * The sentence being spoken, as a subtitle over the bottom of the terminal, clear of the player's control bar.
 * It renders inside the player's wrapper so it stays visible in fullscreen.
 */
export function CaptionOverlay({ entry, containerRef }: { entry: DemoEntry; containerRef: RefObject<HTMLDivElement | null> }) {
  const time = usePlaybackStore((state) => state.time)
  const status = usePlaybackStore((state) => state.status)
  const captionsOn = usePlaybackStore((state) => state.captionsOn)
  const muted = usePlaybackStore((state) => state.muted)
  const wrapper = usePlayerWrapper(containerRef)
  if (!wrapper || !isNarrated(entry) || !captionsOn || muted) return null

  // Before Play the clock sits on the poster frame, not where narration starts.
  const started = status !== 'idle' && status !== 'loading'
  const caption = started ? entry.captions!.find((c) => c.start <= time + 0.05 && time < c.end) : undefined
  if (!caption) return null

  return createPortal(
    <div aria-hidden className="demo-caption pointer-events-none absolute inset-x-10 bottom-14 z-10 flex justify-center">
      <p className="demo-caption-text max-w-[60ch] rounded-md bg-black/15 px-3 py-1.5 text-center text-[14px] leading-5 font-medium text-gate">
        {caption.text}
      </p>
    </div>,
    wrapper,
  )
}

/** Pane-header control: labels the voice as AI and turns the captions on or off. */
export function CaptionsToggle({ entry }: { entry: DemoEntry }) {
  const captionsOn = usePlaybackStore((state) => state.captionsOn)
  const muted = usePlaybackStore((state) => state.muted)
  const toggleCaptions = usePlaybackStore((state) => state.toggleCaptions)
  if (!isNarrated(entry)) return null
  const Icon = captionsOn ? Captions : CaptionsOff
  const showing = captionsOn && !muted

  return (
    <button
        type="button"
        aria-pressed={showing}
        onClick={toggleCaptions}
        title={muted ? 'Unmute to show captions' : captionsOn ? 'Hide captions' : 'Show captions'}
        className={cn(
          'flex h-5 items-center gap-1 rounded-sm px-1.5 font-semibold hover:bg-foreground/10',
          showing ? 'text-gate' : 'text-subtle-foreground',
        )}
      >
        <Icon aria-hidden className="size-3.5" />
        Captions
    </button>
  )
}
