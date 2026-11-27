import { useEffect, useId, useState } from 'react'

/**
 * A Mermaid sequence diagram, drawn in the browser. Mermaid is large, so it loads only when a demo has a diagram.
 * The source is authored in the repo (`sequence.mmd`), and `securityLevel: 'strict'` keeps its labels as plain text.
 */
export function SequenceDiagram({ source, title }: { source: string; title: string }) {
  const id = `seq-${useId().replace(/[^a-zA-Z0-9-]/g, '')}`
  const [svg, setSvg] = useState<string>()
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let cancelled = false
    void (async () => {
      try {
        const { default: mermaid } = await import('mermaid')
        mermaid.initialize({
          startOnLoad: false,
          securityLevel: 'strict',
          theme: 'redux-dark-color',
          look: 'neo',
          fontFamily: getComputedStyle(document.body).fontFamily,
          // Notes mark each phase; Mermaid's default yellow is too loud on the hub's dark surface.
          themeVariables: { noteBkgColor: '#26262e', noteTextColor: '#f2f2f5', noteBorderColor: '#f0008c' },
          sequence: { useMaxWidth: true, wrap: true, mirrorActors: true, showSequenceNumbers: true },
        })
        const { svg: drawn } = await mermaid.render(id, source)
        if (!cancelled) setSvg(drawn)
      } catch {
        if (!cancelled) setFailed(true)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [id, source])

  if (failed) {
    return (
      <pre className="overflow-x-auto rounded-md bg-terminal p-3 font-mono text-[12px] text-muted-foreground">{source}</pre>
    )
  }
  if (!svg) {
    return (
      <div role="status" className="flex h-40 items-center justify-center text-body-sm text-muted-foreground">
        Drawing the {title.toLowerCase()}…
      </div>
    )
  }
  // Rendered from repo-authored source with Mermaid's strict security level; never user input.
  return <div className="overflow-x-auto [&_svg]:mx-auto [&_svg]:h-auto" dangerouslySetInnerHTML={{ __html: svg }} />
}
