import { useMemo, type ComponentType } from 'react'
import { Download } from 'lucide-react'
import { CodeBlock } from '@/components/shared/CodeBlock'
import { CopyButton } from '@/components/shared/CopyButton'

interface Output {
  output_type: string
  text?: string | string[]
  data?: Record<string, string | string[]>
  ename?: string
  evalue?: string
}

interface Cell {
  id?: string
  cell_type: 'code' | 'markdown' | 'raw'
  source: string | string[]
  execution_count?: number | null
  outputs?: Output[]
}

const join = (value: string | string[] | undefined) => (Array.isArray(value) ? value.join('') : (value ?? ''))
// Charts print terminal colors; the transcript shows plain text.
// eslint-disable-next-line no-control-regex
const plain = (text: string) => text.replace(/\x1b\[[0-9;?]*[A-Za-z]/g, '')

function outputText(outputs: Output[] = []) {
  return plain(
    outputs
      .map((out) =>
        out.output_type === 'stream'
          ? join(out.text)
          : out.output_type === 'error'
            ? `${out.ename}: ${out.evalue}`
            : join(out.data?.['text/plain']),
      )
      .join('')
      .replace(/\s+$/, ''),
  )
}

/** An executed Jupyter notebook in the transcript: every cell's source and output, and the .ipynb to take away. */
export function NotebookView({
  name,
  json,
  Markdown,
}: {
  name: string
  json: string
  /** Renders a markdown cell; the transcript passes the renderer it uses for the agent's text. */
  Markdown: ComponentType<{ text: string }>
}) {
  const cells = useMemo(() => (JSON.parse(json) as { cells: Cell[] }).cells, [json])
  const href = useMemo(() => `data:application/x-ipynb+json;charset=utf-8,${encodeURIComponent(json)}`, [json])

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-2">
        <a
          href={href}
          download={name}
          className="inline-flex items-center gap-1.5 rounded-sm border border-border px-2 py-1 text-xs text-muted-foreground hover:border-border-strong hover:text-foreground"
        >
          <Download aria-hidden className="size-3.5" />
          Download {name}
        </a>
        <CopyButton text={json} label={`Copy ${name} as notebook JSON`} visibleLabel="Copy .ipynb" />
      </div>
      <ol className="flex flex-col gap-2">
        {cells.map((cell, i) => {
          const source = join(cell.source).trim()
          if (cell.cell_type !== 'code') {
            return (
              <li key={cell.id ?? i}>
                <div className="rounded-md border border-border px-3 py-2 text-muted-foreground">
                  <Markdown text={source} />
                </div>
              </li>
            )
          }
          const output = outputText(cell.outputs)
          return (
            <li key={cell.id ?? i} className="flex flex-col gap-1">
              <span className="font-mono text-[11px] text-subtle-foreground">
                In [{cell.execution_count ?? ' '}]{cell.id ? ` · ${cell.id}` : ''}
              </span>
              <CodeBlock code={source} copyLabel={`Copy cell ${cell.id ?? i + 1}`} accent="file" maxLines={12} />
              {output && (
                <pre className="max-h-72 overflow-auto rounded-md border border-dashed border-border px-3 py-2 font-mono text-[12px] leading-5 whitespace-pre text-muted-foreground">
                  {output}
                </pre>
              )}
            </li>
          )
        })}
      </ol>
    </div>
  )
}
