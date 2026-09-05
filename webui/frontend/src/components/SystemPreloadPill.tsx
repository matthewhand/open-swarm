import { useState, useId } from 'react'
import { ChevronDown } from 'lucide-react'
import { renderSafeMarkdown } from '../lib/markdown'

export interface SystemPreloadPillProps {
  text: string
  defaultExpanded?: boolean
  className?: string
  label?: string
}

export function SystemPreloadPill({
  text,
  defaultExpanded = false,
  className = '',
  label = 'Message from System',
}: SystemPreloadPillProps) {
  const [expanded, setExpanded] = useState(defaultExpanded)
  const contentId = useId()

  return (
    <div
      className={`os-system-preload flex flex-col items-start w-full my-2 ${className}`}
      data-testid="system-preload-container"
    >
      <button
        type="button"
        className="inline-flex items-center gap-1.5 rounded-full border border-base-content/20 bg-base-200/80 hover:bg-base-200 px-2.5 py-1 text-xs font-medium text-base-content/75 transition-colors focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-primary cursor-pointer select-none"
        data-testid="system-preload-pill"
        aria-expanded={expanded}
        aria-controls={contentId}
        aria-label={label}
        onClick={() => setExpanded((prev) => !prev)}
      >
        <span
          className="flex h-4 w-4 items-center justify-center rounded-full bg-base-300 text-[10px] font-bold text-base-content/80 shrink-0"
          aria-hidden="true"
        >
          S
        </span>
        <span>{label}</span>
        <ChevronDown
          className={`h-3.5 w-3.5 opacity-60 transition-transform duration-150 shrink-0 ${
            expanded ? 'rotate-180' : ''
          }`}
          aria-hidden="true"
        />
      </button>
      {expanded && (
        <div
          id={contentId}
          data-testid="system-preload-content"
          role="region"
          aria-label={label}
          className="mt-2 w-full max-w-xl rounded-lg border border-base-content/15 bg-base-200/40 p-3 text-xs text-base-content/80 shadow-xs whitespace-pre-wrap leading-relaxed"
        >
          <div
            className="os-system-preload-md chat-md break-words [&_p]:my-1 [&_p:first-child]:mt-0 [&_p:last-child]:mb-0 [&_ul]:my-1 [&_ul]:list-disc [&_ul]:pl-5 [&_strong]:font-semibold"
            dangerouslySetInnerHTML={{ __html: renderSafeMarkdown(text) }}
          />
        </div>
      )}
    </div>
  )
}
