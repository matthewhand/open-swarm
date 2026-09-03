import { useCallback, useEffect, useMemo, useRef, useState, type MouseEvent as ReactMouseEvent } from 'react'
import { Link, useLocation, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ChevronDown, ChevronRight, Eye, EyeOff, LifeBuoy, ScanSearch, Settings, Shield, Users, X } from 'lucide-react'
import { fetchBlueprints, type Blueprint } from '../lib/api'
import {
  agentMarkIndex,
  hideAgentId,
  loadHiddenAgentIds,
  unhideAgentId,
} from '../lib/hiddenAgents'
import { isSupportAgent, roleTone, sortSupportFirst } from '../lib/supportAgents'

export interface AgentSidebarProps {
  /** Mobile drawer open. Desktop (lg+) is always visible. */
  open?: boolean
  onClose?: () => void
}

interface ContextMenuState {
  agentId: string
  agentName: string
  hidden: boolean
  x: number
  y: number
}

function agentLabel(agent: Blueprint): string {
  return agent.name || agent.id
}

export default function AgentSidebar({ open = false, onClose }: AgentSidebarProps) {
  const { pathname } = useLocation()
  const [searchParams] = useSearchParams()
  const selectedId = pathname.startsWith('/chat') ? (searchParams.get('blueprint') ?? '') : ''

  const [hiddenIds, setHiddenIds] = useState<string[]>(() => loadHiddenAgentIds())
  const [hiddenOpen, setHiddenOpen] = useState(false)
  const [filter, setFilter] = useState('')
  const [menu, setMenu] = useState<ContextMenuState | null>(null)
  const menuRef = useRef<HTMLDivElement | null>(null)

  const blueprintsQuery = useQuery({
    queryKey: ['blueprints'],
    queryFn: fetchBlueprints,
    retry: 1,
  })
  const agents = blueprintsQuery.data?.data ?? []

  const matchesFilter = useCallback(
    (agent: Blueprint) => {
      const q = filter.trim().toLowerCase()
      if (!q) return true
      return (
        agentLabel(agent).toLowerCase().includes(q) ||
        agent.id.toLowerCase().includes(q) ||
        (agent.description || '').toLowerCase().includes(q)
      )
    },
    [filter],
  )

  const visibleAgents = useMemo(
    () =>
      sortSupportFirst(
        agents.filter(
          (agent) =>
            (isSupportAgent(agent) || !hiddenIds.includes(agent.id)) && matchesFilter(agent),
        ),
      ),
    [agents, hiddenIds, matchesFilter],
  )
  const hiddenAgents = useMemo(
    () =>
      sortSupportFirst(
        agents.filter(
          (agent) =>
            !isSupportAgent(agent) && hiddenIds.includes(agent.id) && matchesFilter(agent),
        ),
      ),
    [agents, hiddenIds, matchesFilter],
  )

  const closeMenu = useCallback(() => setMenu(null), [])

  useEffect(() => {
    if (!menu) return
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') closeMenu()
    }
    const onPointer = (event: Event) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        closeMenu()
      }
    }
    window.addEventListener('keydown', onKey)
    window.addEventListener('mousedown', onPointer)
    return () => {
      window.removeEventListener('keydown', onKey)
      window.removeEventListener('mousedown', onPointer)
    }
  }, [menu, closeMenu])

  const openMenu = (event: ReactMouseEvent, agent: Blueprint, hidden: boolean) => {
    event.preventDefault()
    const pad = 8
    const width = 200
    const height = 44
    const x = Math.min(event.clientX, window.innerWidth - width - pad)
    const y = Math.min(event.clientY, window.innerHeight - height - pad)
    setMenu({
      agentId: agent.id,
      agentName: agentLabel(agent),
      hidden,
      x: Math.max(pad, x),
      y: Math.max(pad, y),
    })
  }

  const hideAgent = (id: string) => {
    setHiddenIds((current) => hideAgentId(id, current))
    closeMenu()
  }

  const unhideAgent = (id: string) => {
    setHiddenIds((current) => unhideAgentId(id, current))
    closeMenu()
  }

  const renderAgentLink = (agent: Blueprint, hidden: boolean) => {
    const name = agentLabel(agent)
    const active = selectedId === agent.id
    const tone = roleTone(agent)
    const pinned = isSupportAgent(agent)
    return (
      <Link
        to={`/chat?blueprint=${encodeURIComponent(agent.id)}`}
        className={`os-agent-row flex min-w-0 flex-1 items-start gap-2.5 rounded-lg px-2 py-2 text-left transition-colors ${
          tone ? `os-agent-row--${tone}` : ''
        } ${
          active
            ? 'bg-base-300/70 text-base-content'
            : 'text-base-content/90 hover:bg-base-300/40'
        }`}
        data-role={tone || undefined}
        aria-current={active ? 'page' : undefined}
        onClick={onClose}
        onContextMenu={(event) => {
          if (pinned) return
          openMenu(event, agent, hidden)
        }}
      >
        {tone === 'support' ? (
          <LifeBuoy className="os-agent-role-mark mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
        ) : tone === 'gate' ? (
          <Shield className="os-agent-role-mark mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
        ) : tone === 'skeptic' ? (
          <ScanSearch className="os-agent-role-mark mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
        ) : (
          <span
            className="os-agent-dot mt-1.5"
            data-mark={String(agentMarkIndex(agent.id))}
            aria-hidden="true"
          />
        )}
        <span className="min-w-0 flex-1">
          <span className="flex items-center gap-1.5">
            <span className="block truncate text-sm font-semibold leading-5">{name}</span>
            {tone ? (
              <span className={`os-role-pill os-role-pill--${tone}`}>{tone}</span>
            ) : null}
          </span>
          {agent.description ? (
            <span className="mt-0.5 block truncate text-xs text-base-content/45">
              {agent.description}
            </span>
          ) : null}
        </span>
      </Link>
    )
  }

  return (
    <>
      {/* Mobile overlay */}
      <button
        type="button"
        className={`fixed inset-0 z-30 bg-black/50 lg:hidden ${open ? '' : 'hidden'}`}
        aria-label="Close agents sidebar"
        onClick={onClose}
      />

      <aside
        className={`os-agent-sidebar fixed inset-y-0 left-0 z-40 flex w-64 shrink-0 flex-col pt-14 transition-transform duration-200 lg:static lg:z-0 lg:translate-x-0 lg:pt-0 ${
          open ? 'translate-x-0' : '-translate-x-full'
        }`}
        aria-label="Agents"
      >
        <div className="flex items-center justify-between gap-2 px-3 pb-2 pt-3 lg:pt-3">
          <p className="text-[0.7rem] font-semibold uppercase tracking-[0.08em] text-base-content/45">
            Agents
          </p>
          <button
            type="button"
            className="btn btn-ghost btn-xs btn-circle lg:hidden"
            aria-label="Close agents sidebar"
            onClick={onClose}
          >
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>

        <div className="px-3 pb-2">
          <label className="sr-only" htmlFor="os-agent-filter">
            Filter agents
          </label>
          <input
            id="os-agent-filter"
            type="search"
            className="input input-sm h-9 w-full rounded-full border border-base-300 bg-base-100/40 text-sm"
            placeholder="Search agents"
            value={filter}
            onChange={(event) => setFilter(event.target.value)}
          />
        </div>

        <nav className="min-h-0 flex-1 overflow-y-auto px-2 pb-3" aria-label="Agent list">
          {blueprintsQuery.isPending ? (
            <p className="px-2 py-3 text-sm text-base-content/45">Loading agents…</p>
          ) : blueprintsQuery.isError ? (
            <p className="px-2 py-3 text-sm text-base-content/45">Could not load agents.</p>
          ) : visibleAgents.length === 0 ? (
            <p className="px-2 py-3 text-sm text-base-content/45">
              {agents.length === 0 ? 'No agents yet.' : 'No matching agents.'}
            </p>
          ) : (
            <ul className="space-y-0.5">
              {visibleAgents.map((agent) => (
                <li key={agent.id}>{renderAgentLink(agent, false)}</li>
              ))}
            </ul>
          )}

          {hiddenAgents.length > 0 && (
            <div className="mt-3 border-t border-base-300/70 pt-2">
              <button
                type="button"
                className="flex w-full items-center gap-1.5 rounded-md px-2 py-1.5 text-left text-xs font-semibold uppercase tracking-[0.06em] text-base-content/45 hover:bg-base-300/30"
                aria-expanded={hiddenOpen}
                onClick={() => setHiddenOpen((value) => !value)}
              >
                {hiddenOpen ? (
                  <ChevronDown className="h-3.5 w-3.5" aria-hidden="true" />
                ) : (
                  <ChevronRight className="h-3.5 w-3.5" aria-hidden="true" />
                )}
                Hidden
                <span className="font-normal normal-case tracking-normal">({hiddenAgents.length})</span>
              </button>
              {hiddenOpen && (
                <ul className="mt-1 space-y-0.5">
                  {hiddenAgents.map((agent) => (
                    <li key={agent.id} className="flex items-start gap-1">
                      {renderAgentLink(agent, true)}
                      <button
                        type="button"
                        className="btn btn-ghost btn-xs mt-1.5 text-base-content/60"
                        aria-label={`Unhide ${agentLabel(agent)}`}
                        onClick={() => unhideAgent(agent.id)}
                      >
                        <Eye className="h-3.5 w-3.5" aria-hidden="true" />
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </nav>

        <div className="mt-auto border-t border-base-300/70 px-3 py-3 text-sm text-base-content/60">
          <a href="/teams/" className="flex items-center gap-2 rounded-md px-1 py-1.5 hover:text-base-content">
            <Users className="h-4 w-4" aria-hidden="true" />
            Teams
          </a>
          <a href="/settings/" className="flex items-center gap-2 rounded-md px-1 py-1.5 hover:text-base-content">
            <Settings className="h-4 w-4" aria-hidden="true" />
            Settings
          </a>
        </div>
      </aside>

      {menu && (
        <div
          ref={menuRef}
          role="menu"
          aria-label={menu.hidden ? `Actions for hidden ${menu.agentName}` : `Actions for ${menu.agentName}`}
          className="fixed z-50 min-w-[12.5rem] rounded-lg border border-base-300 bg-neutral py-1 text-sm shadow-xl"
          style={{ left: menu.x, top: menu.y }}
        >
          {menu.hidden ? (
            <button
              type="button"
              role="menuitem"
              className="flex w-full items-center gap-2 px-3 py-2 text-left hover:bg-base-300/50"
              onClick={() => unhideAgent(menu.agentId)}
            >
              <Eye className="h-4 w-4" aria-hidden="true" />
              Unhide
            </button>
          ) : (
            <button
              type="button"
              role="menuitem"
              className="flex w-full items-center gap-2 px-3 py-2 text-left hover:bg-base-300/50"
              onClick={() => hideAgent(menu.agentId)}
            >
              <EyeOff className="h-4 w-4" aria-hidden="true" />
              Hide from sidebar
            </button>
          )}
        </div>
      )}
    </>
  )
}
