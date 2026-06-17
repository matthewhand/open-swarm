import { useState } from 'react'
import { Copy, Check, Download } from 'lucide-react'

/** A filename-safe slug for a snippet label, e.g. "cli_agents config" -> "cli_agents-config.json". */
export function toFilename(label: string): string {
  const slug = label.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '')
  return `${slug || 'config'}.json`
}

/** A config snippet block with Copy + Download, used across the Builder panels.
 *  Keyboard-focusable + labelled for a11y. */
export function ConfigSnippet({ json, label }: { json: string; label: string }) {
  const [copied, setCopied] = useState(false)

  const copy = async () => {
    try {
      await navigator.clipboard?.writeText(json)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      /* clipboard unavailable (insecure context) */
    }
  }

  const download = () => {
    const blob = new Blob([json], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = toFilename(label)
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="mt-3">
      <div className="mb-1 flex items-center justify-between gap-2">
        <span className="text-xs font-semibold uppercase tracking-wide text-base-content/70">{label}</span>
        <div className="flex gap-1">
          <button type="button" className="btn btn-xs gap-1" onClick={download} aria-label={`Download ${label}`}>
            <Download className="h-3.5 w-3.5" /> Download
          </button>
          <button type="button" className="btn btn-xs gap-1" onClick={copy} aria-label={`Copy ${label}`}>
            {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
            {copied ? 'Copied' : 'Copy'}
          </button>
        </div>
      </div>
      <pre
        tabIndex={0}
        role="region"
        aria-label={`${label} snippet`}
        className="max-h-64 overflow-auto rounded-lg bg-base-300 p-3 text-xs focus:outline focus:outline-2 focus:outline-primary"
      >
        <code>{json}</code>
      </pre>
    </div>
  )
}
