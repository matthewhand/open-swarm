import { useEffect, useMemo, useRef, useState } from 'react'
import { Search } from 'lucide-react'
import { filterSessions, type MemberSession } from '../lib/sessionPicker'

export interface SessionPickerProps {
  open: boolean
  title: string
  sessions: MemberSession[]
  onClose: () => void
  onSelect: (session: MemberSession) => void
}

/**
 * #394-style session picker: search-palette chrome (list, keyboard, filter),
 * pre-filtered to one team / remote / agent. Empty: “no sessions yet”.
 */
export default function SessionPicker({
  open,
  title,
  sessions,
  onClose,
  onSelect,
}: SessionPickerProps) {
  const [query, setQuery] = useState('')
  const [activeIdx, setActiveIdx] = useState(0)
  const inputRef = useRef<HTMLInputElement | null>(null)
  const visible = useMemo(() => filterSessions(sessions, query), [sessions, query])

  useEffect(() => {
    setActiveIdx(0)
  }, [query, open, sessions])

  useEffect(() => {
    if (!open) return
    setQuery('')
    requestAnimationFrame(() => inputRef.current?.focus())
  }, [open])

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
        const row = visible[activeIdx]
        if (row) onSelect(row)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose, onSelect, visible, activeIdx])

  if (!open) return null

  return (
    <div
      className="os-search-overlay"
      data-session-picker="true"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose()
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label={`${title} sessions`}
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
            aria-label="Filter sessions"
            aria-controls="os-session-picker-results"
            aria-activedescendant={
              visible[activeIdx] ? `os-session-row-${visible[activeIdx].id}` : undefined
            }
            role="combobox"
            aria-expanded="true"
            autoComplete="off"
            className="os-search-palette__input"
          />
        </div>
        <p className="os-session-picker__sub">{title}</p>
        <ul
          id="os-session-picker-results"
          role="listbox"
          aria-label="Sessions"
          className="os-search-palette__list"
        >
          {sessions.length === 0 ? (
            <li className="os-search-empty">no sessions yet</li>
          ) : visible.length === 0 ? (
            <li className="os-search-empty">No results</li>
          ) : (
            visible.map((row, idx) => (
              <li
                key={row.id}
                id={`os-session-row-${row.id}`}
                role="option"
                aria-selected={idx === activeIdx}
                data-session-id={row.id}
                data-session-status={row.status}
                className={
                  idx === activeIdx ? 'os-search-row os-search-row--active' : 'os-search-row'
                }
                onMouseMove={() => setActiveIdx(idx)}
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => onSelect(row)}
              >
                <span className="min-w-0 flex-1">
                  <span className="os-search-row__name">{row.title}</span>
                  <span className="os-search-row__desc">
                    {row.status === 'running' ? 'Running' : 'Finished'}
                    {row.snippet ? ` · ${row.snippet}` : ''}
                  </span>
                </span>
              </li>
            ))
          )}
        </ul>
      </div>
    </div>
  )
}
