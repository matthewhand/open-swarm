import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Bot,
  FileText,
  Link2,
  MessageSquare,
  Plug,
  Search,
  Sparkles,
  Users,
  Workflow,
} from 'lucide-react'
import { fetchBlueprints } from '../lib/api'
import { agentMarkIndex } from '../lib/hiddenAgents'
import { agentLabel, supportFirstAgents } from '../lib/supportAgent'
import { dispatchToggleTheme } from '../lib/theme'

export const SEARCH_PALETTE_TABS = [
  'All',
  'Messages',
  'Bots',
  'Groups',
  'Files',
  'Links',
  'Routines',
  'Actions',
] as const

export type SearchPaletteTab = (typeof SEARCH_PALETTE_TABS)[number]

export const OPEN_SEARCH_EVENT = 'swarm:open-search'

export function openSearchPalette(): void {
  window.dispatchEvent(new CustomEvent(OPEN_SEARCH_EVENT))
}

interface PaletteRow {
  id: string
  tab: Exclude<SearchPaletteTab, 'All'>
  name: string
  description: string
  href?: string
  action?: () => void
}

export interface SearchPaletteProps {
  open: boolean
  onClose: () => void
}

function shortcutLabel(index: number): string {
  return `⌃${index + 1}`
}

export default function SearchPalette({ open, onClose }: SearchPaletteProps) {
  const [query, setQuery] = useState('')
  const [tab, setTab] = useState<SearchPaletteTab>('All')
  const [activeIdx, setActiveIdx] = useState(0)
  const inputRef = useRef<HTMLInputElement | null>(null)
  const dialogRef = useRef<HTMLDivElement | null>(null)
  const navigate = useNavigate()

  const blueprintsQuery = useQuery({
    queryKey: ['blueprints'],
    queryFn: fetchBlueprints,
    enabled: open,
    retry: 1,
  })
  const agents = supportFirstAgents(blueprintsQuery.data?.data ?? [])

  const rows = useMemo<PaletteRow[]>(() => {
    const botRows: PaletteRow[] = agents.map((agent) => ({
      id: `bot-${agent.id}`,
      tab: 'Bots',
      name: agentLabel(agent),
      description: agent.description || `${agentLabel(agent)} agent`,
      href: `/chat?blueprint=${encodeURIComponent(agent.id)}`,
    }))
    const actionRows: PaletteRow[] = [
      {
        id: 'action-theme',
        tab: 'Actions',
        name: 'Toggle theme',
        description: 'Switch light and dark chrome',
        action: () => dispatchToggleTheme(),
      },
      {
        id: 'action-blueprints',
        tab: 'Actions',
        name: 'Blueprints',
        description: 'Open the Django blueprint library',
        href: '/blueprint-library/',
      },
      {
        id: 'action-teams',
        tab: 'Actions',
        name: 'Teams',
        description: 'Launch or manage teams',
        href: '/teams/launch/',
      },
      {
        id: 'action-settings',
        tab: 'Actions',
        name: 'Settings',
        description: 'Operator settings',
        href: '/settings/',
      },
    ]
    return [...botRows, ...actionRows]
  }, [agents])

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase()
    return rows.filter((row) => {
      if (tab !== 'All' && row.tab !== tab) return false
      if (!q) return true
      return (
        row.name.toLowerCase().includes(q) ||
        row.description.toLowerCase().includes(q)
      )
    })
  }, [query, rows, tab])

  useEffect(() => {
    setActiveIdx(0)
  }, [query, tab, open])

  useEffect(() => {
    if (!open) return
    setQuery('')
    setTab('All')
    requestAnimationFrame(() => inputRef.current?.focus())
  }, [open])

  const choose = useCallback(
    (row: PaletteRow | undefined) => {
      if (!row) return
      onClose()
      if (row.action) {
        row.action()
        return
      }
      if (!row.href) return
      if (row.href.startsWith('/chat')) navigate(row.href)
      else window.location.assign(row.href)
    },
    [navigate, onClose],
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

  return (
    <div
      className="os-search-overlay"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose()
      }}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label="Search"
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
            aria-label="Search"
            aria-controls="os-search-results"
            aria-activedescendant={
              visible[activeIdx] ? `os-search-row-${visible[activeIdx].id}` : undefined
            }
            role="combobox"
            aria-expanded="true"
            autoComplete="off"
            className="os-search-palette__input"
          />
        </div>

        <div className="os-search-palette__tabs" role="tablist" aria-label="Search categories">
          {SEARCH_PALETTE_TABS.map((name) => {
            const selected = tab === name
            return (
              <button
                key={name}
                type="button"
                role="tab"
                aria-selected={selected}
                className={selected ? 'os-search-tab os-search-tab--active' : 'os-search-tab'}
                onClick={() => setTab(name)}
              >
                {name}
              </button>
            )
          })}
        </div>

        <ul
          id="os-search-results"
          role="listbox"
          aria-label="Search results"
          className="os-search-palette__list"
        >
          {visible.length === 0 ? (
            <li className="os-search-empty">No results</li>
          ) : (
            visible.map((row, idx) => (
              <li
                key={row.id}
                id={`os-search-row-${row.id}`}
                role="option"
                aria-selected={idx === activeIdx}
                className={
                  idx === activeIdx ? 'os-search-row os-search-row--active' : 'os-search-row'
                }
                onMouseMove={() => setActiveIdx(idx)}
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => choose(row)}
              >
                <RowIcon tab={row.tab} id={row.id} />
                <span className="min-w-0 flex-1">
                  <span className="os-search-row__name">{row.name}</span>
                  <span className="os-search-row__desc">{row.description}</span>
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

function RowIcon({ tab, id }: { tab: PaletteRow['tab']; id: string }) {
  if (tab === 'Bots') {
    const mark = agentMarkIndex(id.replace(/^bot-/, ''))
    return (
      <span className="os-search-row__icon" data-mark={String(mark)} aria-hidden="true">
        <Bot className="h-4 w-4" />
      </span>
    )
  }
  const Icon =
    tab === 'Messages'
      ? MessageSquare
      : tab === 'Groups'
        ? Users
        : tab === 'Files'
          ? FileText
          : tab === 'Links'
            ? Link2
            : tab === 'Routines'
              ? Workflow
              : tab === 'Actions'
                ? Sparkles
                : Plug
  return (
    <span className="os-search-row__icon" aria-hidden="true">
      <Icon className="h-4 w-4" />
    </span>
  )
}
