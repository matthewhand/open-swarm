import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type DragEvent as ReactDragEvent,
  type MouseEvent as ReactMouseEvent,
} from 'react'
import { Link, useLocation, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Eye, EyeOff, Pin, PinOff, Plug, Search, X } from 'lucide-react'
import { fetchBlueprints, type Blueprint } from '../lib/api'
import {
  agentMarkIndex,
  hideAgentId,
  loadHiddenAgentIds,
  unhideAgentId,
} from '../lib/hiddenAgents'
import { defaultHostname, loadHostname, saveHostname } from '../lib/hostname'
import {
  endAgentDrag,
  loadPinnedAgents,
  parseAgentDragPayload,
  pinAgent,
  type PinnedAgent,
  unpinAgent,
  writeAgentDragPayload,
} from '../lib/pinnedAgents'
import {
  agentLabel,
  defaultBlueprintId,
  isSupportAgent,
  supportFirstAgents,
} from '../lib/supportAgent'
import { openSearchPalette } from './SearchPalette'

export interface AgentSidebarProps {
  /** Mobile drawer open. Desktop (lg+) is always visible. */
  open?: boolean
  onClose?: () => void
  onOpenSearch?: () => void
}

interface ContextMenuState {
  agentId: string
  agentName: string
  hidden: boolean
  pinned: boolean
  x: number
  y: number
}

export default function AgentSidebar({ open = false, onClose, onOpenSearch }: AgentSidebarProps) {
  const { pathname } = useLocation()
  const [searchParams] = useSearchParams()
  const selectedId = defaultBlueprintId(
    pathname.startsWith('/chat') || pathname === '/' ? searchParams.get('blueprint') : '',
  )

  const [hiddenIds, setHiddenIds] = useState<string[]>(() => loadHiddenAgentIds())
  const [pins, setPins] = useState<PinnedAgent[]>(() => loadPinnedAgents())
  const [hiddenOpen, setHiddenOpen] = useState(false)
  const [pluginsOpen, setPluginsOpen] = useState(false)
  const [hostname, setHostname] = useState(() => loadHostname())
  const [menu, setMenu] = useState<ContextMenuState | null>(null)
  const [dropActive, setDropActive] = useState(false)
  const [hideDropActive, setHideDropActive] = useState(false)
  const [draggingId, setDraggingId] = useState<string | null>(null)
  const menuRef = useRef<HTMLDivElement | null>(null)
  const hideDropDepth = useRef(0)

  const blueprintsQuery = useQuery({
    queryKey: ['blueprints'],
    queryFn: fetchBlueprints,
    retry: 1,
  })
  const agents = supportFirstAgents(blueprintsQuery.data?.data ?? [])

  const visibleAgents = useMemo(
    () => agents.filter((agent) => !hiddenIds.includes(agent.id)),
    [agents, hiddenIds],
  )
  const hiddenAgents = useMemo(
    () => agents.filter((agent) => hiddenIds.includes(agent.id)),
    [agents, hiddenIds],
  )
  const visiblePins = useMemo(
    () => pins.filter((pin) => !hiddenIds.includes(pin.id)),
    [pins, hiddenIds],
  )

  const closeMenu = useCallback(() => setMenu(null), [])

  const openPalette = useCallback(() => {
    onOpenSearch?.()
    openSearchPalette()
  }, [onOpenSearch])

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
    const height = 88
    const x = Math.min(event.clientX, window.innerWidth - width - pad)
    const y = Math.min(event.clientY, window.innerHeight - height - pad)
    setMenu({
      agentId: agent.id,
      agentName: agentLabel(agent),
      hidden,
      pinned: pins.some((pin) => pin.id === agent.id),
      x: Math.max(pad, x),
      y: Math.max(pad, y),
    })
  }

  const finishDrag = () => {
    endAgentDrag()
    setDraggingId(null)
    setDropActive(false)
    setHideDropActive(false)
    hideDropDepth.current = 0
  }

  /**
   * Hide wins: the id leaves the conversation list and the favourite pin grid.
   * Role agents (support, gate, skeptic) are not exempt. Unhide restores the
   * list row only — it does not re-pin.
   */
  const hideFromRail = (id: string) => {
    if (!id) return
    setHiddenIds((current) => hideAgentId(id, current))
    setPins((current) => unpinAgent(id, current))
  }

  const hideAgent = (id: string) => {
    hideFromRail(id)
    closeMenu()
  }

  const unhideAgent = (id: string) => {
    setHiddenIds((current) => {
      const next = unhideAgentId(id, current)
      if (next.length === 0) setHiddenOpen(false)
      return next
    })
    closeMenu()
  }

  const togglePin = (agent: { id: string; name: string }) => {
    setPins((current) =>
      current.some((pin) => pin.id === agent.id)
        ? unpinAgent(agent.id, current)
        : pinAgent(agent, current),
    )
    closeMenu()
  }

  const dropPin = (event: ReactDragEvent) => {
    event.preventDefault()
    const payload = parseAgentDragPayload(event.dataTransfer)
    setDropActive(false)
    finishDrag()
    if (!payload) return
    setPins((current) => pinAgent(payload, current))
  }

  const dropHide = (event: ReactDragEvent) => {
    event.preventDefault()
    const payload = parseAgentDragPayload(event.dataTransfer)
    finishDrag()
    if (!payload?.id) return
    // Already hidden (or a drop that never left the source row) is a no-op.
    if (hiddenIds.includes(payload.id)) return
    hideFromRail(payload.id)
  }

  const dropOnSelf = (event: ReactDragEvent) => {
    event.preventDefault()
    event.stopPropagation()
    finishDrag()
  }

  const beginRowDrag = (event: ReactDragEvent, agent: { id: string; name: string }) => {
    writeAgentDragPayload(event.dataTransfer, agent)
    try {
      event.dataTransfer.effectAllowed = 'copyMove'
    } catch {
      /* jsdom DataTransfer may be a stub */
    }
    setDraggingId(agent.id)
  }

  const renderAgentLink = (agent: Blueprint, hidden: boolean) => {
    const name = agentLabel(agent)
    const active = selectedId === agent.id
    const support = isSupportAgent(agent)
    const dragging = draggingId === agent.id
    return (
      <Link
        to={`/chat?blueprint=${encodeURIComponent(agent.id)}`}
        className={`os-agent-row ${active ? 'os-agent-row--active' : ''} ${
          support ? 'os-agent-row--support' : ''
        } ${dragging ? 'os-agent-row--dragging' : ''}`}
        data-agent-id={agent.id}
        aria-current={active ? 'page' : undefined}
        draggable={!hidden}
        onDragStart={(event) => beginRowDrag(event, { id: agent.id, name })}
        onDragEnd={finishDrag}
        onDragOver={(event) => {
          // Rows are not drop targets; dropping onto the source is a no-op.
          event.dataTransfer.dropEffect = 'none'
        }}
        onDrop={dropOnSelf}
        onClick={onClose}
        onContextMenu={(event) => openMenu(event, agent, hidden)}
      >
        <span
          className="os-agent-dot mt-1.5"
          data-mark={String(agentMarkIndex(agent.id))}
          data-role={support ? 'support' : undefined}
          aria-hidden="true"
        />
        <span className="min-w-0 flex-1">
          <span className="block truncate text-sm font-semibold leading-5">{name}</span>
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
      <button
        type="button"
        className={`fixed inset-0 z-30 bg-black/50 lg:hidden ${open ? '' : 'hidden'}`}
        aria-label="Close agents sidebar"
        onClick={onClose}
      />

      <aside
        className={`os-agent-sidebar fixed inset-y-0 left-0 z-40 flex w-64 shrink-0 flex-col transition-transform duration-200 lg:static lg:z-0 lg:translate-x-0 ${
          open ? 'translate-x-0' : '-translate-x-full'
        }`}
        aria-label="Agents"
      >
        <div className="flex items-center justify-end px-3 pt-3 lg:hidden">
          <button
            type="button"
            className="btn btn-ghost btn-xs btn-circle"
            aria-label="Close agents sidebar"
            onClick={onClose}
          >
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>

        <div className="px-3 pb-2 pt-3">
          <label className="sr-only" htmlFor="os-rail-search">
            Search
          </label>
          <div className="os-rail-search">
            <Search className="h-3.5 w-3.5 shrink-0 text-base-content/40" aria-hidden="true" />
            <input
              id="os-rail-search"
              type="search"
              className="os-rail-search__input"
              placeholder="Search"
              readOnly
              autoComplete="off"
              onFocus={(event) => {
                event.currentTarget.blur()
                openPalette()
              }}
              onClick={openPalette}
            />
          </div>
        </div>

        <div
          className={`os-fav-grid ${dropActive ? 'os-fav-grid--active' : ''}`}
          aria-label="Pinned agents"
          onDragOver={(event) => {
            event.preventDefault()
            event.dataTransfer.dropEffect = 'copy'
            setDropActive(true)
          }}
          onDragLeave={() => setDropActive(false)}
          onDrop={dropPin}
        >
          {visiblePins.map((pin) => (
            <Link
              key={pin.id}
              to={`/chat?blueprint=${encodeURIComponent(pin.id)}`}
              className={`os-fav-tile ${draggingId === pin.id ? 'os-fav-tile--dragging' : ''}`}
              title={pin.name}
              aria-label={pin.name}
              data-agent-id={pin.id}
              draggable
              onDragStart={(event) => beginRowDrag(event, pin)}
              onDragEnd={finishDrag}
              onClick={onClose}
              onContextMenu={(event) => {
                event.preventDefault()
                setMenu({
                  agentId: pin.id,
                  agentName: pin.name,
                  hidden: hiddenIds.includes(pin.id),
                  pinned: true,
                  x: event.clientX,
                  y: event.clientY,
                })
              }}
            >
              <span
                className="os-agent-dot"
                data-mark={String(agentMarkIndex(pin.id))}
                aria-hidden="true"
              />
            </Link>
          ))}
        </div>

        <nav className="min-h-0 flex-1 overflow-y-auto px-2 pb-3" aria-label="Agent list">
          {blueprintsQuery.isPending ? (
            <p className="px-2 py-3 text-sm text-base-content/45">Loading agents…</p>
          ) : blueprintsQuery.isError && visibleAgents.length === 0 ? (
            <p className="px-2 py-3 text-sm text-base-content/45">Could not load agents.</p>
          ) : visibleAgents.length === 0 ? (
            <p className="px-2 py-3 text-sm text-base-content/45">No agents yet.</p>
          ) : (
            <ul className="space-y-0.5">
              {visibleAgents.map((agent) => (
                <li key={agent.id}>{renderAgentLink(agent, false)}</li>
              ))}
            </ul>
          )}

          <div
            className={`os-hide-drop os-drop-target ${hideDropActive ? 'os-hide-drop--active' : ''}`}
            data-drag-over={hideDropActive ? 'true' : undefined}
            role="region"
            aria-label="Hidden"
            onDragEnter={(event) => {
              event.preventDefault()
              hideDropDepth.current += 1
              setHideDropActive(true)
            }}
            onDragOver={(event) => {
              event.preventDefault()
              event.dataTransfer.dropEffect = 'move'
              setHideDropActive(true)
            }}
            onDragLeave={() => {
              hideDropDepth.current -= 1
              if (hideDropDepth.current <= 0) {
                hideDropDepth.current = 0
                setHideDropActive(false)
              }
            }}
            onDrop={dropHide}
          >
            {hiddenAgents.length > 0 ? (
              <button
                type="button"
                className="os-hide-drop__action"
                aria-haspopup="dialog"
                aria-expanded={hiddenOpen}
                onClick={() => setHiddenOpen(true)}
              >
                {hiddenAgents.length} hidden
              </button>
            ) : (
              <p className="os-hide-drop__hint">drop here to hide</p>
            )}
          </div>
        </nav>

        <div className="mt-auto border-t border-base-300/70 px-3 py-3">
          <button
            type="button"
            className="flex w-full items-center gap-2 rounded-md px-1 py-1.5 text-sm text-base-content/60 hover:bg-base-300/30 hover:text-base-content"
            onClick={() => setPluginsOpen(true)}
          >
            <Plug className="h-4 w-4" aria-hidden="true" />
            Plugins
          </button>
          <label className="sr-only" htmlFor="os-rail-hostname">
            Hostname
          </label>
          <input
            id="os-rail-hostname"
            type="text"
            className="os-rail-hostname"
            value={hostname}
            spellCheck={false}
            onChange={(event) => setHostname(event.target.value)}
            onBlur={() => setHostname(saveHostname(hostname))}
            onKeyDown={(event) => {
              if (event.key === 'Enter') {
                event.currentTarget.blur()
              }
              if (event.key === 'Escape') {
                setHostname(loadHostname() || defaultHostname())
                event.currentTarget.blur()
              }
            }}
          />
        </div>
      </aside>

      {hiddenOpen && (
        <>
          <button
            type="button"
            className="fixed inset-0 z-50 bg-black/45"
            aria-label="Close hidden agents"
            onClick={() => setHiddenOpen(false)}
          />
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="os-hidden-agents-title"
            className="fixed left-1/2 top-1/2 z-50 w-[20rem] max-w-[calc(100vw-2rem)] -translate-x-1/2 -translate-y-1/2 rounded-xl border border-base-300 bg-base-100 p-4 shadow-2xl"
          >
            <div className="mb-3 flex items-center justify-between gap-2">
              <h2 id="os-hidden-agents-title" className="text-sm font-semibold">
                Hidden agents
              </h2>
              <button
                type="button"
                className="btn btn-ghost btn-xs btn-circle"
                aria-label="Close hidden agents"
                onClick={() => setHiddenOpen(false)}
              >
                <X className="h-4 w-4" aria-hidden="true" />
              </button>
            </div>
            {hiddenAgents.length === 0 ? (
              <p className="text-sm text-base-content/60">No hidden agents.</p>
            ) : (
              <ul className="space-y-1">
                {hiddenAgents.map((agent) => (
                  <li key={agent.id} className="flex items-center gap-2">
                    <span className="min-w-0 flex-1 truncate text-sm">{agentLabel(agent)}</span>
                    <button
                      type="button"
                      className="btn btn-ghost btn-xs"
                      aria-label={`Unhide ${agentLabel(agent)}`}
                      onClick={() => unhideAgent(agent.id)}
                    >
                      Unhide
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </>
      )}

      {pluginsOpen && (
        <>
          <button
            type="button"
            className="fixed inset-0 z-50 bg-black/45"
            aria-label="Close plugins"
            onClick={() => setPluginsOpen(false)}
          />
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="os-plugins-title"
            className="fixed left-1/2 top-1/2 z-50 w-[20rem] max-w-[calc(100vw-2rem)] -translate-x-1/2 -translate-y-1/2 rounded-xl border border-base-300 bg-base-100 p-4 shadow-2xl"
          >
            <div className="mb-3 flex items-center justify-between gap-2">
              <h2 id="os-plugins-title" className="text-sm font-semibold">
                Plugins
              </h2>
              <button
                type="button"
                className="btn btn-ghost btn-xs btn-circle"
                aria-label="Close plugins"
                onClick={() => setPluginsOpen(false)}
              >
                <X className="h-4 w-4" aria-hidden="true" />
              </button>
            </div>
            <p className="text-sm text-base-content/60">No plugins installed.</p>
          </div>
        </>
      )}

      {menu && (
        <div
          ref={menuRef}
          role="menu"
          aria-label={`Actions for ${menu.agentName}`}
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
          <button
            type="button"
            role="menuitem"
            className="flex w-full items-center gap-2 px-3 py-2 text-left hover:bg-base-300/50"
            onClick={() => togglePin({ id: menu.agentId, name: menu.agentName })}
          >
            {menu.pinned ? (
              <PinOff className="h-4 w-4" aria-hidden="true" />
            ) : (
              <Pin className="h-4 w-4" aria-hidden="true" />
            )}
            {menu.pinned ? 'Unpin' : 'Pin'}
          </button>
        </div>
      )}
    </>
  )
}
