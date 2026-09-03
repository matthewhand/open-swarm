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
import { Modal } from './DaisyUI'
import {
  OPEN_HIDDEN_EVENT,
  OPEN_PLUGINS_EVENT,
  notifyOverlayClosed,
} from '../lib/chromeOverlay'

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
  const menuRef = useRef<HTMLDivElement | null>(null)

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

  const closeMenu = useCallback(() => setMenu(null), [])

  const closeHidden = useCallback(() => {
    setHiddenOpen(false)
    notifyOverlayClosed()
  }, [])

  const closePlugins = useCallback(() => {
    setPluginsOpen(false)
    notifyOverlayClosed()
  }, [])

  useEffect(() => {
    const onHidden = () => setHiddenOpen(true)
    const onPlugins = () => setPluginsOpen(true)
    window.addEventListener(OPEN_HIDDEN_EVENT, onHidden)
    window.addEventListener(OPEN_PLUGINS_EVENT, onPlugins)
    return () => {
      window.removeEventListener(OPEN_HIDDEN_EVENT, onHidden)
      window.removeEventListener(OPEN_PLUGINS_EVENT, onPlugins)
    }
  }, [])

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

  const hideAgent = (id: string) => {
    setHiddenIds((current) => hideAgentId(id, current))
    closeMenu()
  }

  const unhideAgent = (id: string) => {
    setHiddenIds((current) => {
      const next = unhideAgentId(id, current)
      if (next.length === 0) {
        setHiddenOpen(false)
        notifyOverlayClosed()
      }
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
    setDropActive(false)
    const payload = parseAgentDragPayload(event.dataTransfer)
    endAgentDrag()
    if (!payload) return
    setPins((current) => pinAgent(payload, current))
  }

  const renderAgentLink = (agent: Blueprint, hidden: boolean) => {
    const name = agentLabel(agent)
    const active = selectedId === agent.id
    const support = isSupportAgent(agent)
    return (
      <Link
        to={`/chat?blueprint=${encodeURIComponent(agent.id)}`}
        className={`os-agent-row ${active ? 'os-agent-row--active' : ''} ${
          support ? 'os-agent-row--support' : ''
        }`}
        aria-current={active ? 'page' : undefined}
        draggable={!hidden}
        onDragStart={(event) => {
          writeAgentDragPayload(event.dataTransfer, { id: agent.id, name })
          event.dataTransfer.effectAllowed = 'copy'
        }}
        onDragEnd={() => endAgentDrag()}
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
          {pins.map((pin) => (
            <Link
              key={pin.id}
              to={`/chat?blueprint=${encodeURIComponent(pin.id)}`}
              className="os-fav-tile"
              title={pin.name}
              aria-label={pin.name}
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

          {hiddenAgents.length > 0 && (
            <button
              type="button"
              className="mt-2 w-full rounded-md px-2 py-1.5 text-left text-xs text-base-content/50 hover:bg-base-300/30 hover:text-base-content/80"
              aria-haspopup="dialog"
              aria-expanded={hiddenOpen}
              onClick={() => setHiddenOpen(true)}
            >
              {hiddenAgents.length} hidden
            </button>
          )}
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

      <Modal
        isOpen={hiddenOpen}
        onClose={closeHidden}
        title="Hidden agents"
        size="sm"
      >
        {hiddenAgents.length === 0 ? (
          <p className="text-sm text-base-content/60">No hidden agents.</p>
        ) : (
          <ul className="max-h-[min(24rem,calc(100dvh-8rem))] space-y-1 overflow-y-auto">
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
        <div className="modal-action">
          <button type="button" className="btn btn-ghost btn-sm" onClick={closeHidden}>
            Close
          </button>
        </div>
      </Modal>

      <Modal isOpen={pluginsOpen} onClose={closePlugins} title="Plugins" size="sm">
        <p className="text-sm text-base-content/60">No plugins installed.</p>
        <div className="modal-action">
          <button type="button" className="btn btn-ghost btn-sm" onClick={closePlugins}>
            Close
          </button>
        </div>
      </Modal>

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
