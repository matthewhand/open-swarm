import { useId, useState, type ReactNode } from 'react'
import { ChevronDown } from 'lucide-react'
import { compactedCardCopyText } from '../lib/compactedCardMenu'
import { useCompactedCardMenu } from './CompactedCardContextMenu'

export interface CompactSummaryCardProps {
  title?: string
  body: string
  meta?: string
  nested?: ReactNode
  className?: string
  defaultExpanded?: boolean
  /** Extra original turns copied with the summary (full underlying text). */
  compacted?: Array<{ role: string; agent?: string; text: string }>
  onRemove?: () => void
  children?: ReactNode
}

/**
 * Compact / summary chip (#672 / REQ-37) with REQ-213 right-click menu.
 * Default stays expanded so the LLM summary text remains visible.
 */
export function CompactSummaryCard({
  title = 'Summary',
  body,
  meta,
  nested,
  className = '',
  defaultExpanded = true,
  compacted,
  onRemove,
  children,
}: CompactSummaryCardProps) {
  const [expanded, setExpanded] = useState(defaultExpanded)
  const [removed, setRemoved] = useState(false)
  const contentId = useId()
  const copyText = compactedCardCopyText({ text: body, compacted })
  const { onContextMenu, onKeyDown, menuNode } = useCompactedCardMenu({
    label: title,
    expanded,
    copyText,
    onToggleExpand: () => setExpanded((prev) => !prev),
    onRemove: () => {
      if (onRemove) onRemove()
      else setRemoved(true)
    },
  })

  if (removed) return null

  return (
    <div
      className={className}
      data-testid="chat-summary"
      onContextMenu={onContextMenu}
    >
      <button
        type="button"
        className="chat-summary__chip inline-flex items-center gap-1.5 rounded-full border border-base-content/20 bg-base-200/80 hover:bg-base-200 px-2.5 py-1 text-xs font-medium text-base-content/75 transition-colors focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-primary cursor-pointer select-none"
        data-testid="chat-summary-chip"
        aria-expanded={expanded}
        aria-controls={contentId}
        aria-label={title}
        onClick={() => setExpanded((prev) => !prev)}
        onKeyDown={onKeyDown}
      >
        <span>{title}</span>
        <ChevronDown
          className={`h-3.5 w-3.5 opacity-60 transition-transform duration-150 shrink-0 ${
            expanded ? 'rotate-180' : ''
          }`}
          aria-hidden="true"
        />
      </button>
      {expanded ? (
        <div id={contentId} data-testid="chat-summary-content">
          <div className="chat-summary__body whitespace-pre-wrap break-words">{body}</div>
          {meta ? <div className="chat-summary__meta">{meta}</div> : null}
          {children}
          {nested}
        </div>
      ) : null}
      {menuNode}
    </div>
  )
}
