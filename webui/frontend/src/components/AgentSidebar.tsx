import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type DragEvent as ReactDragEvent,
  type MouseEvent as ReactMouseEvent,
} from 'react'
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Eye, EyeOff, Pencil, Pin, PinOff, Plug, Plus, Search, Users, X } from 'lucide-react'
import AddAgentWizard, { type AgentKind } from './AddAgentWizard'
import {
  fetchBlueprints,
  fetchCliAgents,
  fetchHerdrAgents,
  type Blueprint,
  type CliRailAgent,
  type HerdrAgent,
} from '../lib/api'
import AgentAvatar from './AgentAvatar'
import {
  agentRole,
  exampleRoleAgents,
  isChiefOfStaff,
  roleBadgeLabel,
  roleCssClass,
  roleFromAgent,
  showsBlueprintEdit,
} from '../lib/agentRoles'
import { openAgentEditor } from '../lib/agentSettings'
import {
  hasHiddenAgentsStorage,
  hideAgentId,
  loadHiddenAgentIds,
  loadOrSeedHiddenAgentIds,
  unhideAgentId,
} from '../lib/hiddenAgents'
import { defaultHostname, loadHostname, saveHostname } from '../lib/hostname'
import {
  GENERATION_COMPLETE_EVENT,
  applyRailOrder,
  beginRailDrag,
  bumpRailIdToTop,
  endRailDrag,
  generationCompleteAgentId,
  loadRailOrder,
  mergeRailOrder,
  moveRailId,
  peekRailDrag,
  saveRailOrder,
} from '../lib/railOrder'
import {
  BUMP_COMPLETED_EVENT,
  loadBumpCompleted,
} from '../lib/settingsPrefs'
import {
  endAgentDrag,
  excludePinnedFromList,
  loadOrSeedPinnedAgents,
  movePinnedAgent,
  parseAgentDragPayload,
  pinAgent,
  type PinnedAgent,
  unpinAgent,
  writeAgentDragPayload,
} from '../lib/pinnedAgents'
import {
  loadAllAgentSessions,
  SCALE_OUT_SESSIONS_EVENT,
  sessionHref,
  shouldOpenSessionPicker,
  type AgentSession,
} from '../lib/scaleOutSessions'
import { agentLabel, defaultBlueprintId, isSupportAgent } from '../lib/supportAgent'
import { formatRailTimestamp, getRowLastMessage } from '../lib/chatTime'
import { fetchTeamRosters, teamHideId, type TeamRoster } from '../lib/teamRosters'
import { fetchConfiguredRemotes, remoteHideId, type RemoteEntry } from '../lib/remotesCatalog'
import { selectStackedFaces } from '../lib/avatarStack'
import {
  defaultSessionForRemote,
  defaultSessionForTeam,
  sessionsForRemote,
  sessionsForTeam,
  stackFacesForRemote,
  stackFacesForTeam,
  type MemberSession,
} from '../lib/sessionPicker'
import {
  AGENT_SETTINGS_CHANGED_EVENT,
  loadLocalNewChatPerTask,
} from '../lib/agentSettings'
import { activeTaskSessionCount } from '../lib/agentChat'
import { openSearchPalette } from './SearchPalette'
import { AGENT_EDITS_CHANGED_EVENT } from '../lib/agentEdits'
import SessionPicker from './SessionPicker'
import { openSettingsSheet } from './SettingsSheet'
import AvatarStack from './AvatarStack'
import StackedAvatars from './StackedAvatars'

const EMPTY_BLUEPRINTS: Blueprint[] = []

export interface AgentSidebarProps {
  /** Mobile drawer open. Desktop (lg+) is always visible. */
  open?: boolean
  /** Below Tailwind `lg` — drawer + inert when closed. */
  narrow?: boolean
  onClose?: () => void
  /** Agent / conversation / team pick — parent may tuck the rail (REQ-54). */
  onPick?: () => void
  onOpenSearch?: () => void
}

interface ContextMenuState {
  agentId: string
  agentName: string
  hidden: boolean
  pinned: boolean
  x: number
  y: number
  kind?: 'agent' | 'team' | 'remote'
  sessions?: MemberSession[]
}

interface SessionPickerState {
  agentId: string
  agentName: string
  sessions: AgentSession[]
}

type SidebarAgent = Blueprint & {
  kind?: string
  remote?: string
  cli?: string
}

type RailRow =
  | { kind: 'agent'; id: string; agent: SidebarAgent }
  | { kind: 'team'; id: string; team: TeamRoster }
  | { kind: 'remote'; id: string; remote: RemoteEntry }

function isHerdrAgent(agent: { id: string; kind?: string }): boolean {
  return agent.kind === 'herdr' || String(agent.id).startsWith('herdr:')
}

function sidebarHref(agent: { id: string; kind?: string }): string {
  if (isHerdrAgent(agent)) return '/teams/#herdr-members'
  return `/chat?blueprint=${encodeURIComponent(agent.id)}`
}

function toSidebarCli(row: CliRailAgent): SidebarAgent {
  return {
    id: row.id,
    object: 'blueprint',
    name: row.name,
    description: row.installed ? row.description : `${row.description} (not on PATH)`,
    abbreviation: null,
    required_mcp_servers: [],
    tags: ['cli'],
    installed: row.installed,
    compiled: true,
    kind: 'cli',
    cli: row.cli,
  }
}

/** Host CLI verify rows (grok_agent, agy_agent, …) stay on the rail. */
function isCliRailAgent(agent: { id?: string; kind?: string }): boolean {
  return agent.kind === 'cli'
}

function toSidebarHerdr(row: HerdrAgent): SidebarAgent {
  return {
    id: `herdr:${row.name}`,
    object: 'blueprint',
    name: row.name,
    description: row.remote ? `Herdr · ${row.remote}` : 'Herdr · localhost',
    abbreviation: null,
    required_mcp_servers: [],
    tags: [],
    installed: true,
    compiled: true,
    kind: 'herdr',
    remote: row.remote || '',
  }
}

interface PickerState {
  title: string
  sessions: MemberSession[]
}

export default function AgentSidebar({
  open = false,
  narrow = false,
  onClose,
  onPick,
  onOpenSearch,
}: AgentSidebarProps) {
  const pickOrClose = onPick ?? onClose
  const drawerHidden = Boolean(narrow && !open)
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const onChat = pathname.startsWith('/chat') || pathname === '/'
  const selectedTeamId = onChat ? (searchParams.get('team') ?? '') : ''
  const selectedRemoteId = onChat ? (searchParams.get('remote') ?? '') : ''
  const selectedId =
    selectedTeamId || selectedRemoteId
      ? ''
      : defaultBlueprintId(onChat ? searchParams.get('blueprint') : '')

  const [hiddenIds, setHiddenIds] = useState<string[] | null>(() =>
    hasHiddenAgentsStorage() ? loadHiddenAgentIds() : null,
  )
  const [pins, setPins] = useState<PinnedAgent[]>(() => loadOrSeedPinnedAgents())
  const [hiddenOpen, setHiddenOpen] = useState(false)
  const [hoveringHidden, setHoveringHidden] = useState(false)
  const [pluginsOpen, setPluginsOpen] = useState(false)
  const [hostname, setHostname] = useState(() => loadHostname())
  const [menu, setMenu] = useState<ContextMenuState | null>(null)
  const [settingsTick, setSettingsTick] = useState(0)
  const [dropActive, setDropActive] = useState(false)
  const [listDropActive, setListDropActive] = useState(false)
  const [hideDropActive, setHideDropActive] = useState(false)
  const [draggingId, setDraggingId] = useState<string | null>(null)
  const [picker, setPicker] = useState<PickerState | null>(null)
  const [, setEditsTick] = useState(0)
  const [dropTargetId, setDropTargetId] = useState<string | null>(null)
  const [railOrder, setRailOrder] = useState<string[]>(() => loadRailOrder())
  const [bumpCompleted, setBumpCompleted] = useState(() => loadBumpCompleted())
  const [sessionTick, setSessionTick] = useState(0)
  const [sessionPicker, setSessionPicker] = useState<SessionPickerState | null>(null)
  const menuRef = useRef<HTMLDivElement | null>(null)
  const hideDropDepth = useRef(0)
  const [tipsDismissed, setTipsDismissed] = useState(() => {
    try {
      return Boolean(localStorage.getItem('swarm_keybinding_tips_dismissed'))
    } catch {
      return false
    }
  })
  const isMac =
    typeof navigator !== 'undefined' &&
    /Mac|iPod|iPhone|iPad/.test(navigator.platform || navigator.userAgent)
  const searchShortcutLabel = isMac ? '⌘K' : 'Ctrl+K'
  const [addWizardOpen, setAddWizardOpen] = useState(false)
  const handleAgentCreated = useCallback(
    (created: { id: string; name: string; kind: AgentKind }) => {
      setAddWizardOpen(false)
      if (created.kind === 'remote') {
        navigate(`/chat?remote=${encodeURIComponent(created.id)}`)
      } else {
        navigate(`/chat?blueprint=${encodeURIComponent(created.id)}`)
      }
      onClose?.()
    },
    [navigate, onClose],
  )
  const sessionsByAgent = useMemo(() => loadAllAgentSessions(), [sessionTick])

  useEffect(() => {
    const onChange = () => setSessionTick((n) => n + 1)
    window.addEventListener(SCALE_OUT_SESSIONS_EVENT, onChange)
    window.addEventListener('storage', onChange)
    return () => {
      window.removeEventListener(SCALE_OUT_SESSIONS_EVENT, onChange)
      window.removeEventListener('storage', onChange)
    }
  }, [])

  useEffect(() => {
    const onEdits = () => setEditsTick((tick) => tick + 1)
    window.addEventListener(AGENT_EDITS_CHANGED_EVENT, onEdits)
    return () => window.removeEventListener(AGENT_EDITS_CHANGED_EVENT, onEdits)
  }, [])

  const blueprintsQuery = useQuery({
    queryKey: ['blueprints'],
    queryFn: fetchBlueprints,
    retry: 1,
  })
  const teamsQuery = useQuery({
    queryKey: ['team-rosters'],
    queryFn: fetchTeamRosters,
    retry: 1,
  })
  const herdrQuery = useQuery({
    queryKey: ['herdr-agents'],
    queryFn: fetchHerdrAgents,
    retry: 1,
  })
  const remotesQuery = useQuery({
    queryKey: ['configured-remotes'],
    queryFn: fetchConfiguredRemotes,
    retry: 1,
  })
  const cliQuery = useQuery({
    queryKey: ['cli-agents'],
    queryFn: fetchCliAgents,
    retry: 1,
  })
  const catalog = blueprintsQuery.data?.data ?? EMPTY_BLUEPRINTS
  const teams = teamsQuery.data ?? []
  const remotes = remotesQuery.data ?? []
  const agents = useMemo<SidebarAgent[]>(() => {
    const fromBlueprints = exampleRoleAgents(catalog)
    const seen = new Set(fromBlueprints.map((a) => a.id))
    const fromRosters: SidebarAgent[] = []
    for (const roster of teams) {
      for (const member of roster.members) {
        if (member.kind === 'team' || seen.has(member.id)) continue
        if (!isChiefOfStaff(member.role) && member.id !== 'cos') continue
        seen.add(member.id)
        fromRosters.push({
          id: member.id,
          object: 'blueprint',
          name: member.id === 'cos' ? 'Chief of Staff' : member.id,
          description: 'Talks to any available team.',
          abbreviation: 'CoS',
          required_mcp_servers: [],
          tags: [],
          installed: true,
          compiled: true,
          role: 'chief_of_staff',
        })
      }
    }
    const herdr = (herdrQuery.data?.data ?? []).map(toSidebarHerdr)
    const clis = (cliQuery.data?.rail ?? []).map(toSidebarCli)
    const cliIds = new Set(clis.map((a) => a.id))
    const fromBlueprintsNoCli = fromBlueprints.filter((a) => !cliIds.has(a.id))
    const list = [...fromRosters, ...fromBlueprintsNoCli, ...herdr]
    const support = list.filter((a) => isSupportAgent(a))
    const rest = list.filter((a) => !isSupportAgent(a))
    const merged = [...support, ...clis, ...rest]
    const railRank = (a: SidebarAgent) => {
      if (isSupportAgent(a)) return 0
      if (a.kind === 'cli') return 1
      if (isChiefOfStaff(roleFromAgent(a))) return 2
      return 3
    }
    return merged.sort((a, b) => railRank(a) - railRank(b))
  }, [catalog, cliQuery.data, herdrQuery.data, teams])
  const rosterById = useMemo(() => new Map(teams.map((r) => [r.id, r])), [teams])
  const childTeamIds = useMemo(() => {
    const ids = new Set<string>()
    for (const team of teams) {
      for (const member of team.members) {
        if (member.kind === 'team') ids.add(member.team_id || member.id)
      }
    }
    return ids
  }, [teams])
  const rootTeams = useMemo(
    () => teams.filter((team) => !childTeamIds.has(team.id)),
    [teams, childTeamIds],
  )
  const resolvedHiddenIds =
    hiddenIds ?? (blueprintsQuery.isPending ? [] : loadOrSeedHiddenAgentIds(agents))

  useEffect(() => {
    if (hiddenIds !== null || blueprintsQuery.isPending) return
    setHiddenIds(loadOrSeedHiddenAgentIds(agents))
  }, [hiddenIds, blueprintsQuery.isPending, agents])

  useEffect(() => {
    const onSettings = () => setSettingsTick((n) => n + 1)
    window.addEventListener(AGENT_SETTINGS_CHANGED_EVENT, onSettings)
    return () => window.removeEventListener(AGENT_SETTINGS_CHANGED_EVENT, onSettings)
  }, [])

  const visibleAgents = useMemo(
    () =>
      agents.filter(
        (agent) => isCliRailAgent(agent) || !resolvedHiddenIds.includes(agent.id),
      ),
    [agents, resolvedHiddenIds],
  )
  const hiddenAgents = useMemo(
    () =>
      agents.filter(
        (agent) => !isCliRailAgent(agent) && resolvedHiddenIds.includes(agent.id),
      ),
    [agents, resolvedHiddenIds],
  )
  const visibleTeams = useMemo(
    () => teams.filter((team) => !resolvedHiddenIds.includes(teamHideId(team.id))),
    [teams, resolvedHiddenIds],
  )
  const visibleRootTeams = useMemo(
    () => rootTeams.filter((team) => !resolvedHiddenIds.includes(teamHideId(team.id))),
    [rootTeams, resolvedHiddenIds],
  )
  const hiddenTeams = useMemo(
    () => teams.filter((team) => resolvedHiddenIds.includes(teamHideId(team.id))),
    [teams, resolvedHiddenIds],
  )
  const visibleRemotes = useMemo(
    () => remotes.filter((remote) => !resolvedHiddenIds.includes(remoteHideId(remote.id))),
    [remotes, resolvedHiddenIds],
  )
  const hiddenRemotes = useMemo(
    () => remotes.filter((remote) => resolvedHiddenIds.includes(remoteHideId(remote.id))),
    [remotes, resolvedHiddenIds],
  )
  const hiddenCount = hiddenAgents.length + hiddenTeams.length + hiddenRemotes.length
  const visibleCount = visibleAgents.length + visibleTeams.length + visibleRemotes.length
  const loadingList = blueprintsQuery.isPending && teamsQuery.isPending
  const loadFailed = blueprintsQuery.isError && teamsQuery.isError && visibleCount === 0
  const supportAgents = visibleAgents.filter((agent) => isSupportAgent(agent))
  const cliAgents = visibleAgents.filter((agent) => agent.kind === 'cli')
  const otherAgents = visibleAgents.filter(
    (agent) => !isSupportAgent(agent) && agent.kind !== 'cli',
  )
  const catalogRows = useMemo<RailRow[]>(() => {
    const supportRows: RailRow[] = supportAgents.map((agent) => ({
      kind: 'agent',
      id: agent.id,
      agent,
    }))
    const cliRows: RailRow[] = cliAgents.map((agent) => ({
      kind: 'agent',
      id: agent.id,
      agent,
    }))
    const teamRows: RailRow[] = visibleRootTeams.map((team) => ({
      kind: 'team',
      id: teamHideId(team.id),
      team,
    }))
    const remoteRows: RailRow[] = visibleRemotes.map((remote) => ({
      kind: 'remote',
      id: remoteHideId(remote.id),
      remote,
    }))
    const otherRows: RailRow[] = otherAgents.map((agent) => ({
      kind: 'agent',
      id: agent.id,
      agent,
    }))
    return excludePinnedFromList(
      [...supportRows, ...cliRows, ...teamRows, ...remoteRows, ...otherRows],
      pins,
    )
  }, [supportAgents, cliAgents, visibleRootTeams, visibleRemotes, otherAgents, pins])
  const orderedRows = useMemo(
    () => applyRailOrder(catalogRows, railOrder),
    [catalogRows, railOrder],
  )
  const visibleRowIds = useMemo(() => orderedRows.map((row) => row.id), [orderedRows])
  const visiblePins = useMemo(
    () => pins.filter((pin) => !resolvedHiddenIds.includes(pin.id)),
    [pins, resolvedHiddenIds],
  )

  const closeMenu = useCallback(() => setMenu(null), [])

  const openPalette = useCallback(() => {
    onOpenSearch?.()
    openSearchPalette()
  }, [onOpenSearch])

  const openGroupPicker = useCallback((title: string, sessions: MemberSession[]) => {
    setPicker({ title, sessions })
  }, [])

  const closePicker = useCallback(() => setPicker(null), [])

  const selectSession = useCallback(
    (session: MemberSession) => {
      setPicker(null)
      navigate(session.href)
      onClose?.()
    },
    [navigate, onClose],
  )

  const persistVisibleOrder = useCallback((nextVisible: string[]) => {
    setRailOrder(saveRailOrder(nextVisible))
  }, [])

  const reorderBefore = useCallback(
    (fromId: string, beforeId: string) => {
      if (!fromId || !beforeId || fromId === beforeId) return
      const base = mergeRailOrder(railOrder, visibleRowIds)
      persistVisibleOrder(moveRailId(base, fromId, beforeId))
    },
    [railOrder, visibleRowIds, persistVisibleOrder],
  )

  useEffect(() => {
    const onBump = () => setBumpCompleted(loadBumpCompleted())
    window.addEventListener(BUMP_COMPLETED_EVENT, onBump)
    return () => window.removeEventListener(BUMP_COMPLETED_EVENT, onBump)
  }, [])

  useEffect(() => {
    const onComplete = (event: Event) => {
      if (!bumpCompleted) return
      const agentId = generationCompleteAgentId(event)
      if (!agentId || !visibleRowIds.includes(agentId)) return
      const base = mergeRailOrder(railOrder, visibleRowIds)
      persistVisibleOrder(bumpRailIdToTop(base, agentId))
    }
    window.addEventListener(GENERATION_COMPLETE_EVENT, onComplete)
    return () => window.removeEventListener(GENERATION_COMPLETE_EVENT, onComplete)
  }, [bumpCompleted, visibleRowIds, railOrder, persistVisibleOrder])
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

  useEffect(() => {
    const onAltDigit = (event: KeyboardEvent) => {
      if (event.altKey && !event.ctrlKey && !event.metaKey && !event.shiftKey && /^[1-9]$/.test(event.key)) {
        const idx = parseInt(event.key, 10) - 1
        const pin = visiblePins[idx]
        if (pin) {
          event.preventDefault()
          if (isHerdrAgent(pin)) {
            window.location.assign('/teams/#herdr-members')
          } else {
            navigate(`/chat?blueprint=${encodeURIComponent(pin.id)}`)
          }
          onClose?.()
        }
      }
    }
    window.addEventListener('keydown', onAltDigit)
    return () => window.removeEventListener('keydown', onAltDigit)
  }, [visiblePins, navigate, onClose])

  const openMenu = (
    event: ReactMouseEvent,
    hideId: string,
    label: string,
    hidden: boolean,
    kind?: 'agent' | 'team' | 'remote',
    sessions?: MemberSession[],
  ) => {
    event.preventDefault()
    const pad = 8
    const width = 200
    const height = 120
    const x = Math.min(event.clientX, window.innerWidth - width - pad)
    const y = Math.min(event.clientY, window.innerHeight - height - pad)
    setMenu({
      agentId: hideId,
      agentName: label,
      hidden,
      pinned: pins.some((pin) => pin.id === hideId),
      x: Math.max(pad, x),
      y: Math.max(pad, y),
      kind,
      sessions,
    })
  }

  const finishDrag = () => {
    endAgentDrag()
    endRailDrag()
    setDraggingId(null)
    setDropTargetId(null)
    setDropActive(false)
    setListDropActive(false)
    setHideDropActive(false)
    hideDropDepth.current = 0
  }

  const isPinnedId = (id: string | null | undefined) =>
    Boolean(id && pins.some((pin) => pin.id === id))

  /**
   * Hide conceals the id from the conversation list and the visible favourite
   * grid. The pin stays in swarm_pinned_agents so Unhide restores the same
   * favourite slot. Role agents (support, gate, skeptic) are not exempt.
   */
  const hideFromRail = (id: string) => {
    if (!id) return
    if (agents.some((agent) => agent.id === id && isCliRailAgent(agent))) return
    setHiddenIds((current) => hideAgentId(id, current ?? resolvedHiddenIds))
  }

  const hideAgent = (id: string) => {
    hideFromRail(id)
    closeMenu()
  }

  const unhideAgent = (id: string) => {
    setHiddenIds((current) => {
      const next = unhideAgentId(id, current ?? resolvedHiddenIds)
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
    // Already-pinned drops on empty grid space are a no-op; tile drops reorder.
    setPins((current) =>
      current.some((pin) => pin.id === payload.id) ? current : pinAgent(payload, current),
    )
  }

  const dropPinReorder = (event: ReactDragEvent, beforeId: string) => {
    event.preventDefault()
    event.stopPropagation()
    const payload = parseAgentDragPayload(event.dataTransfer)
    finishDrag()
    if (!payload?.id || payload.id === beforeId) return
    setPins((current) => {
      if (current.some((pin) => pin.id === payload.id)) {
        return movePinnedAgent(payload.id, beforeId, current)
      }
      return pinAgent(payload, current)
    })
  }

  const dropUnfavourite = (event: ReactDragEvent) => {
    event.preventDefault()
    const payload = parseAgentDragPayload(event.dataTransfer)
    finishDrag()
    if (!payload?.id) return
    setPins((current) =>
      current.some((pin) => pin.id === payload.id) ? unpinAgent(payload.id, current) : current,
    )
  }

  const allowListUnfavourite = (event: ReactDragEvent) => {
    const fromId = peekRailDrag() || parseAgentDragPayload(event.dataTransfer)?.id
    if (!isPinnedId(fromId)) return
    event.preventDefault()
    try {
      event.dataTransfer.dropEffect = 'move'
    } catch {
      /* synthetic events may omit dataTransfer */
    }
    setListDropActive(true)
  }

  const dropHide = (event: ReactDragEvent) => {
    event.preventDefault()
    const payload = parseAgentDragPayload(event.dataTransfer)
    finishDrag()
    if (!payload?.id) return
    // Already hidden (or a drop that never left the source row) is a no-op.
    if (resolvedHiddenIds.includes(payload.id)) return
    hideFromRail(payload.id)
  }

  const allowRowDrop = (event: ReactDragEvent, targetId: string) => {
    const fromId = peekRailDrag() || parseAgentDragPayload(event.dataTransfer)?.id
    if (!fromId || fromId === targetId) {
      try {
        event.dataTransfer.dropEffect = 'none'
      } catch {
        /* synthetic events may omit dataTransfer */
      }
      return
    }
    event.preventDefault()
    try {
      event.dataTransfer.dropEffect = 'move'
    } catch {
      /* synthetic events may omit dataTransfer */
    }
    setDropTargetId(targetId)
  }

  const dropReorder = (event: ReactDragEvent, targetId: string) => {
    event.preventDefault()
    event.stopPropagation()
    const fromId = peekRailDrag() || parseAgentDragPayload(event.dataTransfer)?.id
    if (fromId && fromId !== targetId) {
      if (isPinnedId(fromId)) {
        setPins((current) => unpinAgent(fromId, current))
      } else {
        reorderBefore(fromId, targetId)
      }
    }
    finishDrag()
  }

  const dropOnSelf = (event: ReactDragEvent) => {
    event.preventDefault()
    event.stopPropagation()
    const fromId = peekRailDrag() || parseAgentDragPayload(event.dataTransfer)?.id
    if (isPinnedId(fromId)) {
      setPins((current) => unpinAgent(fromId!, current))
    }
    finishDrag()
  }

  const beginRowDrag = (event: ReactDragEvent, agent: { id: string; name: string }) => {
    writeAgentDragPayload(event.dataTransfer, agent)
    beginRailDrag(agent.id)
    try {
      event.dataTransfer.effectAllowed = 'copyMove'
    } catch {
      /* jsdom DataTransfer may be a stub */
    }
    setDraggingId(agent.id)
  }

  const openEditor = (agent: Blueprint) => {
    openAgentEditor({ agentId: agent.id })
    onClose?.()
  }

  const openDefinition = (
    kind: 'role' | 'blueprint' | 'team',
    id: string,
    extras?: { blueprintId?: string; teamId?: string },
  ) => {
    openSettingsSheet({
      section: 'definition',
      definitionKind: kind,
      definitionId: id,
      blueprintId: extras?.blueprintId,
      teamId: extras?.teamId,
    })
    onClose?.()
  }

  const openAgentSettings = (agent: { id: string; name: string }) => {
    openAgentEditor({ agentId: agent.id, agentName: agent.name })
    closeMenu()
    onClose?.()
  }

  const renderAgentRow = (agent: SidebarAgent, hidden: boolean) => {
    const name = agentLabel(agent)
    const herdr = isHerdrAgent(agent)
    const sessions = sessionsByAgent[agent.id] ?? []
    const scaleOut = !herdr && shouldOpenSessionPicker(sessions)
    const active = !herdr && selectedId === agent.id
    const role = agentRole(agent)
    const showEdit = !herdr && showsBlueprintEdit(agent)
    const dragging = draggingId === agent.id
    const dropping = dropTargetId === agent.id
    const badge = roleBadgeLabel(role)
    const taskCount = settingsTick >= 0 && loadLocalNewChatPerTask(agent.id)
      ? activeTaskSessionCount(agent.id)
      : 0
    const dataRole = role !== 'default' ? role : undefined
    const className = `os-agent-row ${active ? 'os-agent-row--active' : ''} ${
      dragging ? 'os-agent-row--dragging' : ''
    } ${dropping ? 'os-agent-row--drop' : ''}`
    const { snippet, timestamp } = getRowLastMessage(agent.id, sessions, agent as any)
    const timestampLabel = formatRailTimestamp(timestamp)
    const mark = (
      scaleOut ? (
        // Teams/remotes (#398) must not be stacked here — import AvatarStack there.
        <StackedAvatars sessions={sessions} />
      ) : (
        <AgentAvatar
          src={agent.avatar_path}
          size="sm"
          className="mt-1.5"
        />
      )
    )
    const body = (
      <>
        {mark}
        <span className="min-w-0 flex-1">
          <span className="flex min-w-0 items-center justify-between gap-1.5">
            <span className="block truncate text-sm font-semibold leading-5">{name}</span>
            {timestampLabel ? (
              <span
                className="os-rail-timestamp shrink-0 text-xs text-base-content/40 tabular-nums"
                data-testid="rail-row-timestamp"
              >
                {timestampLabel}
              </span>
            ) : null}
          </span>
          <span className="mt-0.5 flex min-w-0 items-center justify-between gap-1.5 text-xs text-base-content/45">
            <span className="block truncate min-w-0 flex-1">
              {snippet || agent.description}
            </span>
            {badge ? (
              <span
                className={`os-agent-role-badge ${roleCssClass(role)}`}
                data-role={role}
                data-definition-id={agent.id}
                role="button"
                tabIndex={0}
                aria-label={`Open ${role} settings`}
                onClick={(event) => {
                  event.preventDefault()
                  event.stopPropagation()
                  openDefinition('role', agent.id, { blueprintId: agent.id })
                }}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault()
                    event.stopPropagation()
                    openDefinition('role', agent.id, { blueprintId: agent.id })
                  }
                }}
              >
                {badge}
              </span>
            ) : null}
            {taskCount > 1 ? (
              <span
                className="badge badge-sm badge-outline shrink-0"
                data-task-sessions={taskCount}
                title={`${taskCount} running chats`}
              >
                {taskCount} chats
              </span>
            ) : null}
          </span>
        </span>
      </>
    )
    if (herdr) {
      return (
        <a
          href={sidebarHref(agent)}
          className={className}
          data-agent-id={agent.id}
          data-role={dataRole}
          draggable={!hidden}
          onDragStart={(event) => beginRowDrag(event, { id: agent.id, name })}
          onDragEnd={finishDrag}
          onDragOver={(event) => allowRowDrop(event, agent.id)}
          onDrop={(event) => dropReorder(event, agent.id)}
          onClick={pickOrClose}
          onContextMenu={(event) => openMenu(event, agent.id, name, hidden)}
        >
          {body}
        </a>
      )
    }
    const dragHandlers = {
      draggable: !hidden,
      onDragStart: (event: ReactDragEvent) => beginRowDrag(event, { id: agent.id, name }),
      onDragEnd: finishDrag,
      onDragOver: (event: ReactDragEvent) => allowRowDrop(event, agent.id),
      onDrop: (event: ReactDragEvent) => dropReorder(event, agent.id),
      onContextMenu: (event: ReactMouseEvent) => openMenu(event, agent.id, name, hidden),
    }

    if (scaleOut) {
      return (
        <div
          className="os-agent-row-wrap"
          data-role={role}
          data-scale-out="true"
        >
          <button
            type="button"
            className={`${className} w-full`}
            data-agent-id={agent.id}
            data-role={dataRole}
            data-scale-out="true"
            aria-haspopup="dialog"
            aria-current={active ? 'page' : undefined}
            aria-label={`${name}, ${sessions.length} sessions`}
            {...dragHandlers}
            onClick={() => {
              setSessionPicker({ agentId: agent.id, agentName: name, sessions })
            }}
          >
            {body}
          </button>
          {showEdit ? (
            <button
              type="button"
              className="os-agent-edit"
              aria-label={`Edit ${name} blueprint`}
              onClick={(event) => {
                event.preventDefault()
                event.stopPropagation()
                openBlueprintEditor(agent)
              }}
              onKeyDown={(event) => {
                if (event.key === 'Enter') {
                  event.preventDefault()
                  event.stopPropagation()
                  openBlueprintEditor(agent)
                }
              }}
            >
              <Pencil className="h-3.5 w-3.5" aria-hidden="true" />
            </button>
          ) : null}
        </div>
      )
    }

    return (
      <div
        className="os-agent-row-wrap"
        data-role={role}
      >
        <Link
          to={sidebarHref(agent)}
          className={className}
          data-agent-id={agent.id}
          data-role={dataRole}
          aria-current={active ? 'page' : undefined}
          {...dragHandlers}
          onClick={pickOrClose}
        >
          {body}
        </Link>
        {showEdit ? (
          <button
            type="button"
            className="os-agent-edit"
            aria-label={`Edit ${name}`}
            onClick={(event) => {
              event.preventDefault()
              event.stopPropagation()
              openEditor(agent)
            }}
            onKeyDown={(event) => {
              if (event.key === 'Enter') {
                event.preventDefault()
                event.stopPropagation()
                openEditor(agent)
              }
            }}
          >
            <Pencil className="h-3.5 w-3.5" aria-hidden="true" />
          </button>
        ) : null}
      </div>
    )
  }

  const renderTeamLink = (team: TeamRoster, hidden: boolean, nested = false) => {
    const name = team.name || team.id
    const hideId = teamHideId(team.id)
    const active = selectedTeamId === team.id
    const sessions = sessionsForTeam(team)
    const stacked = selectStackedFaces(stackFacesForTeam(team))
    const dragging = draggingId === hideId
    const dropping = dropTargetId === hideId
    const { snippet: teamSnippet, timestamp: teamTime } = getRowLastMessage(
      teamHideId(team.id),
      sessions as any,
      team as any,
    )
    const teamTimestampLabel = formatRailTimestamp(teamTime)
    return (
      <Link
        to={`/chat?team=${encodeURIComponent(team.id)}`}
        className={`os-team-item os-agent-row os-agent-row--team ${
          active ? 'os-agent-row--active' : ''
        } ${nested ? 'os-agent-row--nested' : ''} ${dragging ? 'os-agent-row--dragging' : ''} ${
          dropping ? 'os-agent-row--drop' : ''
        }`}
        aria-current={active ? 'page' : undefined}
        aria-label={`${name} (team)`}
        data-agent-id={hideId}
        data-kind="team"
        data-stack-count={String(stacked.faces.length)}
        data-remainder={String(stacked.remainder)}
        draggable={!hidden}
        onDragStart={(event) => beginRowDrag(event, { id: hideId, name })}
        onDragEnd={finishDrag}
        onDragOver={(event) => allowRowDrop(event, hideId)}
        onDrop={(event) => dropReorder(event, hideId)}
        onClick={(event) => {
          event.preventDefault()
          const def = defaultSessionForTeam(team)
          if (def) {
            navigate(def.href)
            onClose?.()
          } else {
            openGroupPicker(name, sessions)
          }
        }}
        onContextMenu={(event) => openMenu(event, hideId, name, hidden, 'team', sessions)}
      >
        {stacked.faces.length > 0 ? (
          <AvatarStack
            faces={stacked.faces}
            remainder={stacked.remainder}
            animate
            label={`${name} members`}
          />
        ) : (
          <span
            className="os-team-mark os-agent-team-icon mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-md bg-base-300 text-base-content/80"
            aria-hidden="true"
          >
            <Users className="h-3.5 w-3.5" />
          </span>
        )}
        <span className="min-w-0 flex-1">
          <span className="flex min-w-0 items-center justify-between gap-1.5">
            <span className="block truncate text-sm font-semibold leading-5">{name}</span>
            {teamTimestampLabel ? (
              <span
                className="os-rail-timestamp shrink-0 text-xs text-base-content/40 tabular-nums"
                data-testid="rail-row-timestamp"
              >
                {teamTimestampLabel}
              </span>
            ) : null}
          </span>
          <span className="mt-0.5 flex min-w-0 items-center justify-between gap-1.5 text-xs text-base-content/45">
            <span className="block truncate min-w-0 flex-1">
              {teamSnippet || team.description}
            </span>
            <span
              className="os-agent-role-badge badge badge-ghost badge-xs shrink-0 font-medium uppercase tracking-wide text-base-content/55"
              data-kind="team"
              role="button"
              tabIndex={0}
              aria-label={`Open ${name} team settings`}
              data-definition-id={team.id}
              onClick={(event) => {
                event.preventDefault()
                event.stopPropagation()
                openDefinition('team', team.id, { teamId: team.id })
              }}
              onKeyDown={(event) => {
                if (event.key === 'Enter' || event.key === ' ') {
                  event.preventDefault()
                  event.stopPropagation()
                  openDefinition('team', team.id, { teamId: team.id })
                }
              }}
            >
              Team
            </span>
          </span>
        </span>
      </Link>
    )
  }

  const renderRemoteRow = (remote: RemoteEntry, hidden: boolean) => {
    const name = remote.title
    const hideId = remoteHideId(remote.id)
    const active = selectedRemoteId === remote.id
    const dragging = draggingId === hideId
    const sessions = sessionsForRemote(remote)
    const stacked = selectStackedFaces(stackFacesForRemote(remote))
    const { snippet: remoteSnippet, timestamp: remoteTime } = getRowLastMessage(
      hideId,
      sessions as any,
      remote as any,
    )
    const remoteTimestampLabel = formatRailTimestamp(remoteTime)
    return (
      <Link
        to={`/chat?remote=${encodeURIComponent(remote.id)}`}
        className={`os-remote-item os-agent-row os-agent-row--remote ${
          active ? 'os-agent-row--active' : ''
        } ${dragging ? 'os-agent-row--dragging' : ''}`}
        aria-current={active ? 'page' : undefined}
        aria-label={`${name} (remote)`}
        data-agent-id={hideId}
        data-kind="remote"
        data-remote-id={remote.id}
        data-stack-count={String(stacked.faces.length)}
        data-remainder={String(stacked.remainder)}
        draggable={!hidden}
        onDragStart={(event) => beginRowDrag(event, { id: hideId, name })}
        onDragEnd={finishDrag}
        onDragOver={(event) => {
          const fromId = peekRailDrag() || parseAgentDragPayload(event.dataTransfer)?.id
          if (isPinnedId(fromId)) {
            allowRowDrop(event, hideId)
            return
          }
          try {
            event.dataTransfer.dropEffect = 'none'
          } catch {
            /* synthetic events may omit dataTransfer */
          }
        }}
        onDrop={dropOnSelf}
        onClick={(event) => {
          event.preventDefault()
          const def = defaultSessionForRemote(remote)
          if (def) {
            navigate(def.href)
            onClose?.()
          } else {
            openGroupPicker(name, sessions)
          }
        }}
        onContextMenu={(event) => openMenu(event, hideId, name, hidden, 'remote', sessions)}
      >
        <AvatarStack
          faces={stacked.faces}
          remainder={stacked.remainder}
          animate
          label={`${name} members`}
        />
        <span className="min-w-0 flex-1">
          <span className="flex min-w-0 items-center justify-between gap-1.5">
            <span className="block truncate text-sm font-semibold leading-5">{name}</span>
            {remoteTimestampLabel ? (
              <span
                className="os-rail-timestamp shrink-0 text-xs text-base-content/40 tabular-nums"
                data-testid="rail-row-timestamp"
              >
                {remoteTimestampLabel}
              </span>
            ) : null}
          </span>
          <span className="mt-0.5 flex min-w-0 items-center justify-between gap-1.5 text-xs text-base-content/45">
            <span className="block truncate min-w-0 flex-1">
              {remoteSnippet || (remote as any).description || 'Remote team'}
            </span>
            <span
              className="os-agent-role-badge badge badge-ghost badge-xs shrink-0 font-medium uppercase tracking-wide text-base-content/55"
              data-kind="remote"
            >
              Remote
            </span>
          </span>
        </span>
      </Link>
    )
  }

  const renderTeamRow = (team: TeamRoster, nested = false, seen: string[] = []) => {
    const hidden = resolvedHiddenIds.includes(teamHideId(team.id))
    if (hidden && !nested) return null
    const childSlots = team.members.filter((m) => m.kind === 'team')
    return (
      <li key={`team-${team.id}`}>
        {hidden ? null : renderTeamLink(team, false, nested)}
        {childSlots.length > 0 && !seen.includes(team.id) ? (
          <ul className="os-agent-team-nest">
            {childSlots.map((m) => {
              const child = rosterById.get(m.team_id || m.id)
              if (child) return renderTeamRow(child, true, seen.concat(team.id))
              return (
                <li key={`team-slot-${m.id}`}>
                  <span className="os-agent-row os-agent-row--team os-agent-row--nested">
                    <Users className="os-agent-team-icon mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-semibold leading-5">
                        {m.team_id || m.id}
                      </span>
                      <span
                        className="os-agent-role-badge"
                        data-kind="team"
                        data-definition-id={m.team_id || m.id}
                        role="button"
                        tabIndex={0}
                        aria-label={`Open ${m.team_id || m.id} team settings`}
                        onClick={(event) => {
                          event.preventDefault()
                          event.stopPropagation()
                          const teamId = m.team_id || m.id
                          openDefinition('team', teamId, { teamId })
                        }}
                        onKeyDown={(event) => {
                          if (event.key === 'Enter' || event.key === ' ') {
                            event.preventDefault()
                            event.stopPropagation()
                            const teamId = m.team_id || m.id
                            openDefinition('team', teamId, { teamId })
                          }
                        }}
                      >
                        Team
                      </span>
                    </span>
                  </span>
                </li>
              )
            })}
          </ul>
        ) : null}
      </li>
    )
  }

  return (
    <>
      <button
        type="button"
        className={`fixed inset-0 z-30 bg-black/50 lg:hidden ${open ? '' : 'hidden'}`}
        hidden={!open}
        aria-label="Close agents sidebar"
        onClick={onClose}
      />

      <aside
        className={`os-agent-sidebar fixed inset-y-0 left-0 z-40 flex w-64 shrink-0 flex-col transition-transform duration-200 lg:static lg:z-0 lg:translate-x-0 ${
          open ? 'translate-x-0' : '-translate-x-full'
        }`}
        aria-label="Agents"
        data-testid="os-agent-rail"
        data-rail-open={open ? 'true' : 'false'}
        aria-hidden={drawerHidden || undefined}
        {...(drawerHidden ? { inert: '' } : {})}
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

        {!tipsDismissed && (
          <div className="px-3 pt-2" data-testid="first-load-tips">
            <div className="os-keybinding-tips alert p-2 text-xs flex items-center justify-between gap-1 shadow-sm border border-base-content/10 bg-base-200/50">
              <div className="flex flex-wrap items-center gap-1.5 min-w-0">
                <span className="font-semibold text-base-content/80">Tips:</span>
                <span><kbd className="kbd kbd-xs">{searchShortcutLabel}</kbd> Search</span>
                <span><kbd className="kbd kbd-xs">{isMac ? '⌥1–9' : 'Alt+1–9'}</kbd> Pins</span>
                <span><kbd className="kbd kbd-xs">Esc</kbd> Clear</span>
              </div>
              <button
                type="button"
                className="btn btn-ghost btn-xs btn-square shrink-0 text-base-content/60 hover:text-base-content"
                aria-label="Dismiss tips"
                onClick={() => {
                  try {
                    localStorage.setItem('swarm_keybinding_tips_dismissed', '1')
                  } catch {}
                  setTipsDismissed(true)
                }}
              >
                <X className="h-3.5 w-3.5" aria-hidden="true" />
              </button>
            </div>
          </div>
        )}

        <div className="os-rail-search-row flex items-center gap-1.5 px-3 pb-2 pt-3">
          <label className="sr-only" htmlFor="os-rail-search">
            Search
          </label>
          <div className="os-rail-search min-w-0 flex-1">
            <Search className="h-3.5 w-3.5 shrink-0 text-base-content/40" aria-hidden="true" />
            <input
              id="os-rail-search"
              type="search"
              className="os-rail-search__input"
              placeholder={`Search ${searchShortcutLabel}`}
              readOnly
              autoComplete="off"
              onFocus={(event) => {
                event.currentTarget.blur()
                openPalette()
              }}
              onClick={openPalette}
            />
            <kbd className="os-rail-search__kbd kbd kbd-xs">{searchShortcutLabel}</kbd>
          </div>
          <button
            type="button"
            className="os-search-add-btn"
            aria-label="Add agent"
            title="Add agent"
            data-testid="add-agent-button"
            onClick={() => setAddWizardOpen(true)}
          >
            <Plus className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>

        <div
          className={`os-fav-grid ${dropActive ? 'os-fav-grid--active' : ''} ${
            visiblePins.length === 0 &&
            !dropActive &&
            !(draggingId && !isPinnedId(draggingId))
              ? 'os-fav-grid--bare'
              : ''
          } ${visiblePins.length === 0 ? 'os-fav-grid--empty' : ''}`}
            aria-label="Pinned agents"
            data-fav-layout="2-up"
            data-testid="agent-fav-grid"
            data-fav-empty={visiblePins.length === 0 ? 'true' : 'false'}
            onDragOver={(event) => {
              event.preventDefault()
              try {
                event.dataTransfer.dropEffect = 'move'
              } catch {
                /* synthetic events may omit dataTransfer */
              }
              setDropActive(true)
            }}
            onDragLeave={() => setDropActive(false)}
            onDrop={dropPin}
          >
            {visiblePins.length === 0 ? (
              <div
                className="os-fav-grid__hint"
                data-testid="fav-empty-hint"
              >
                {dropActive || (draggingId && !isPinnedId(draggingId)) ? 'drop' : '+'}
              </div>
            ) : null}
          {visiblePins.map((pin, pinIdx) => {
            const live = agents.find((agent) => agent.id === pin.id)
            const pinName = live ? agentLabel(live) : pin.name || pin.id
            const role = live ? agentRole(live) : 'default'
            const badge = live ? roleBadgeLabel(role) : ''
            const pinActive = Boolean(selectedId && selectedId === pin.id)
            const pinClass = `os-fav-tile ${
              draggingId === pin.id ? 'os-fav-tile--dragging' : ''
            } ${dropTargetId === pin.id ? 'os-fav-tile--drop' : ''} ${
              pinActive ? 'os-fav-tile--active' : ''
            }`
            const pinFace = (
              <>
                {badge ? (
                  <span
                    className={`os-fav-tile__badge os-agent-role-badge ${roleCssClass(role)}`}
                    data-role={role}
                    data-definition-id={pin.id}
                    role="button"
                    tabIndex={0}
                    aria-label={`Open ${role} settings`}
                    onClick={(event) => {
                      event.preventDefault()
                      event.stopPropagation()
                      openDefinition('role', pin.id, { blueprintId: pin.id })
                    }}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter' || event.key === ' ') {
                        event.preventDefault()
                        event.stopPropagation()
                        openDefinition('role', pin.id, { blueprintId: pin.id })
                      }
                    }}
                  >
                    {badge}
                  </span>
                ) : null}
                <AgentAvatar
                  src={live?.avatar_path}
                  size="lg"
                  className="os-fav-tile__avatar"
                />
                <span className="os-fav-tile__name">{pinName}</span>
                {pinIdx < 9 && (
                  <span
                    className="os-fav-tile__shortcut"
                    aria-label={`Shortcut ${isMac ? '⌥' : 'Alt+'}${pinIdx + 1}`}
                  >
                    {isMac ? `⌥${pinIdx + 1}` : `Alt+${pinIdx + 1}`}
                  </span>
                )}
              </>
            )
            const pinHandlers = {
              draggable: true as const,
              onDragStart: (event: ReactDragEvent) => beginRowDrag(event, pin),
              onDragEnd: finishDrag,
              onDragOver: (event: ReactDragEvent) => allowRowDrop(event, pin.id),
              onDrop: (event: ReactDragEvent) => dropPinReorder(event, pin.id),
              onClick: pickOrClose,
              onContextMenu: (event: ReactMouseEvent) => {
                event.preventDefault()
                setMenu({
                  agentId: pin.id,
                  agentName: pinName,
                  hidden: resolvedHiddenIds.includes(pin.id),
                  pinned: true,
                  x: event.clientX,
                  y: event.clientY,
                })
              },
            }
            if (isHerdrAgent(pin)) {
              return (
                <a
                  key={pin.id}
                  href="/teams/#herdr-members"
                  className={pinClass}
                  title={pinName}
                  aria-label={pinName}
                  data-agent-id={pin.id}
                  {...pinHandlers}
                >
                  {pinFace}
                </a>
              )
            }
            return (
              <Link
                key={pin.id}
                to={`/chat?blueprint=${encodeURIComponent(pin.id)}`}
                className={pinClass}
                title={pinName}
                aria-label={pinName}
                data-agent-id={pin.id}
                {...pinHandlers}
              >
                {pinFace}
              </Link>
            )
          })}
          </div>


        <nav className="min-h-0 flex-1 overflow-y-auto px-2 pb-3" aria-label="Agent list">
          <div
            className={`os-agent-list ${listDropActive ? 'os-agent-list--unfav' : ''}`}
            data-testid="agent-list-drop"
            data-unfavourite-target="true"
            onDragOver={allowListUnfavourite}
            onDragLeave={(event) => {
              if (!event.currentTarget.contains(event.relatedTarget as Node)) {
                setListDropActive(false)
              }
            }}
            onDrop={dropUnfavourite}
          >
            {loadingList ? (
              <p className="px-2 py-3 text-sm text-base-content/45">Loading agents…</p>
            ) : loadFailed ? (
              <p className="px-2 py-3 text-sm text-base-content/45">Could not load agents.</p>
            ) : visibleCount === 0 ? (
              <p className="px-2 py-3 text-sm text-base-content/45">
                {isPinnedId(draggingId) ? 'drop here to unfavourite' : 'No agents yet.'}
              </p>
            ) : (
              <ul className="space-y-0.5">
                {orderedRows.map((row, index) => (
                  <li key={row.id} data-rail-id={row.id} data-rail-index={index}>
                    {row.kind === 'team'
                      ? renderTeamRow(row.team)
                      : row.kind === 'remote'
                        ? renderRemoteRow(row.remote, false)
                        : renderAgentRow(row.agent, false)}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </nav>

        <div
          className={`os-hidden-bots ${hiddenCount === 0 ? 'os-hidden-bots--empty' : 'os-hide-drop--has-hidden'} ${
            hideDropActive ? 'os-hidden-bots--active' : ''
          }`}
          data-testid="hidden-bots-row"
          data-empty={hiddenCount === 0 ? 'true' : 'false'}
          data-drag-over={hideDropActive ? 'true' : undefined}
          role="region"
          aria-label="Hidden Bots"
          onDragEnter={(event) => {
            event.preventDefault()
            hideDropDepth.current += 1
            setHideDropActive(true)
          }}
          onDragOver={(event) => {
            event.preventDefault()
            try {
              event.dataTransfer.dropEffect = 'move'
            } catch {
              /* synthetic events may omit dataTransfer */
            }
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
          {hiddenCount > 0 ? (
            <button
              type="button"
              className="os-hide-drop__action os-hidden-bots-row group"
              aria-haspopup="dialog"
              aria-expanded={hiddenOpen}
              aria-label={`Hidden Bots ${hiddenCount} (${hiddenCount} hidden)`}
              data-testid="os-hidden-bots-button"
              onClick={() => setHiddenOpen(true)}
              onMouseEnter={() => setHoveringHidden(true)}
              onMouseLeave={() => setHoveringHidden(false)}
            >
              <span className="os-hidden-bots-label font-medium">Hidden Bots</span>
              <span className="os-hidden-bots-tail font-mono text-xs" data-testid="os-hidden-bots-tail">
                <span
                  className={`os-hidden-bots-count ${hoveringHidden ? 'hidden' : 'inline group-hover:hidden'}`}
                  data-testid="os-hidden-bots-count"
                >
                  {hiddenCount}
                </span>
                <span
                  className={`os-hidden-bots-chevron ${hoveringHidden ? 'inline' : 'hidden group-hover:inline'}`}
                  aria-hidden="true"
                  data-testid="os-hidden-bots-chevron"
                >
                  &gt;
                </span>
              </span>
            </button>
          ) : null}
        </div>

        <div className="border-t border-base-300/70 px-3 py-3">
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
            {hiddenCount === 0 ? (
              <p className="text-sm text-base-content/60">No hidden agents.</p>
            ) : (
              <ul className="space-y-1">
                {hiddenTeams.map((team) => (
                  <li key={teamHideId(team.id)} className="flex items-center gap-2">
                    <span className="min-w-0 flex-1 truncate text-sm">{team.name || team.id}</span>
                    <button
                      type="button"
                      className="btn btn-ghost btn-xs"
                      aria-label={`Unhide ${team.name || team.id}`}
                      onClick={() => unhideAgent(teamHideId(team.id))}
                    >
                      Unhide
                    </button>
                  </li>
                ))}
                {hiddenRemotes.map((remote) => (
                  <li key={remoteHideId(remote.id)} className="flex items-center gap-2">
                    <span className="min-w-0 flex-1 truncate text-sm">{remote.title}</span>
                    <button
                      type="button"
                      className="btn btn-ghost btn-xs"
                      aria-label={`Unhide ${remote.title}`}
                      onClick={() => unhideAgent(remoteHideId(remote.id))}
                    >
                      Unhide
                    </button>
                  </li>
                ))}
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

      <SessionPicker
        open={Boolean(picker)}
        title={picker?.title ?? ''}
        sessions={picker?.sessions ?? []}
        onClose={closePicker}
        onSelect={selectSession}
      />

      <SessionPicker
        open={sessionPicker !== null}
        agentName={sessionPicker?.agentName ?? ''}
        sessions={sessionPicker?.sessions ?? []}
        onClose={() => setSessionPicker(null)}
        onSelect={(session) => {
          const agentId = sessionPicker?.agentId || session.agentId
          navigate(sessionHref(agentId, session.id))
          onClose?.()
        }}
      />

      {menu && (
        <div
          ref={menuRef}
          role="menu"
          aria-label={`Actions for ${menu.agentName}`}
          className="fixed z-50 min-w-[12.5rem] rounded-lg border border-base-300 bg-neutral py-1 text-sm shadow-xl"
          style={{ left: menu.x, top: menu.y }}
        >
          {menu.sessions && menu.sessions.length > 0 && (
            <button
              type="button"
              role="menuitem"
              className="flex w-full items-center gap-2 px-3 py-2 text-left hover:bg-base-300/50"
              onClick={() => {
                const s = menu.sessions!
                const title = menu.agentName
                closeMenu()
                openGroupPicker(title, s)
              }}
            >
              <Users className="h-4 w-4" aria-hidden="true" />
              Select Agent
            </button>
          )}
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
            onClick={() => openAgentSettings({ id: menu.agentId, name: menu.agentName })}
          >
            <Pencil className="h-4 w-4" aria-hidden="true" />
            Edit agent
          </button>
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
      <AddAgentWizard
        isOpen={addWizardOpen}
        onClose={() => setAddWizardOpen(false)}
        onCreated={handleAgentCreated}
      />
    </>
  )
}
