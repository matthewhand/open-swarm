import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Search } from 'lucide-react'
import { agentMarkIndex } from '../lib/hiddenAgents'
import {
  compareSessions,
  filterAgentSessions,
  type AgentSession,
} from '../lib/scaleOutSessions'

export interface SessionPickerProps {
  open: boolean
  agentName: string
  sessions: readonly AgentSession[]
  onClose: () => void
  onSelect: (session: AgentSession) => void
}

function shortcutLabel(index: number): string {
  return `⌃${index + 1}`
}

/**
 * Search-palette chrome, pre-filtered to one agent's running + finished
 * sessions. Not a new SPA page — overlay only; chat stays mounted.
 */
export default function SessionPicker({
  open,
  agentName,
  sessions,
  onClose,
  onSelect,
}: SessionPickerProps) {
  const [query, setQuery] = useState('')
  const [activeIdx, setActiveIdx] = useState(0)
  const inputRef = useRef<HTMLInputElement | null>(null)

  const visible = useMemo(
    () => filterAgentSessions([...sessions].sort(compareSessions), query),
    [query, sessions],
  )

  useEffect(() => {
    setActiveIdx(0)
  }, [query, open, sessions])

  useEffect(() => {
    if (!open) return
    setQuery('')
    requestAnimationFrame(() => inputRef.current?.focus())
  }, [open])

  const choose = useCallback(
    (row: AgentSession | undefined) => {
      if (!row) return
      onSelect(row)
      onClose()
    },
    [onClose, onSelect],
  )

  useEffect(() => {
    if (!open) return
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        onClose()
        return
      }
      if (event.key === 'ArrowDown') {
        event.preventDefault()
        setActiveIdx((i) => Math.min(i + 1, Math.max(0, visible.length - 1)))
        return
      }
      if (event.key === 'ArrowUp') {
        event.preventDefault()
        setActiveIdx((i) => Math.max(i - 1, 0))
        return
      }
      if (event.key === 'Enter') {
        event.preventDefault()
        choose(visible[activeIdx])
        return
      }
      if (event.ctrlKey && /^[1-9]$/.test(event.key)) {
        event.preventDefault()
        choose(visible[Number(event.key) - 1])
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose, choose, visible, activeIdx])

  if (!open) return null

  const label = `${agentName} sessions`

  return (
    <div
      className="os-search-overlay"
      data-testid="os-session-picker"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose()
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label={label}
        className="os-search-palette"
      >
        <div className="os-search-palette__field">
          <Search className="h-4 w-4 shrink-0 text-base-content/45" aria-hidden="true" />
          <input
            ref={inputRef}
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search"
            aria-label={`Filter ${agentName} sessions`}
            aria-controls="os-session-results"
            aria-activedescendant={
              visible[activeIdx] ? `os-session-row-${visible[activeIdx].id}` : undefined
            }
            role="combobox"
            aria-expanded="true"
            autoComplete="off"
            className="os-search-palette__input"
          />
        </div>

        <ul
          id="os-session-results"
          role="listbox"
          aria-label={label}
          className="os-search-palette__list"
        >
          {visible.length === 0 ? (
            <li className="os-search-empty">no sessions yet</li>
          ) : (
            visible.map((row, idx) => (
              <li
                key={row.id}
                id={`os-session-row-${row.id}`}
                role="option"
                aria-selected={idx === activeIdx}
                data-session-id={row.id}
                data-status={row.status}
                className={
                  idx === activeIdx ? 'os-search-row os-search-row--active' : 'os-search-row'
                }
                onMouseMove={() => setActiveIdx(idx)}
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => choose(row)}
              >
                <span
                  className="os-search-row__icon"
                  data-mark={String(agentMarkIndex(row.id))}
                  aria-hidden="true"
                />
                <span className="min-w-0 flex-1">
                  <span className="os-search-row__name">{row.title}</span>
                  <span className="os-search-row__desc">
                    {row.status === 'running' ? 'Running' : 'Finished'}
                    {row.snippet ? ` · ${row.snippet}` : ''}
                  </span>
                </span>
                {idx < 9 && <kbd className="os-search-shortcut">{shortcutLabel(idx)}</kbd>}
              </li>
            ))
          )}
        </ul>
      </div>
    </div>
  )
}
