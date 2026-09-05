import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
  type ChangeEvent,
  type FormEvent,
  type KeyboardEvent,
} from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowUp, Layers, Mic, PanelLeft, Pencil, Plus, Reply, Settings } from 'lucide-react'
import AgentAvatar from '../components/AgentAvatar'
import { TOAST_KIND_WS_DISCONNECT, useToast } from '../components/DaisyUI'
import ThemeToggle from '../components/ThemeToggle'
import { OPEN_SETTINGS_EVENT, openSettingsSheet } from '../components/SettingsSheet'
import {
  AGENT_SETTINGS_CHANGED_EVENT,
  loadLocalNewChatPerTask,
  openAgentEditor,
  type AgentSettingsChangedDetail,
} from '../lib/agentSettings'
import { persistableMessages, putAgentChatSession } from '../lib/agentChatSessions'
import { useRailChrome } from '../components/RailChrome'
import { ComputerControlStub } from '../components/ComputerControlStub'
import { RemoteSelect } from '../components/RemoteSelect'
import { ChatMessageBubble } from '../components/ChatMessageBubble'
import { ComposerSlashPopup } from '../components/ComposerSlashPopup'
import {
  type SlashItem,
  buildSlashCatalog,
  filterSlashItems,
  getRecentSlashIds,
  recordRecentSlashId,
} from '../lib/slashMenu'
import { fetchConfigOptions, fetchBlueprints, fetchCliAgents, fetchCliModels, fetchRemotes } from '../lib/api'
import {
  agentIdFromBlueprint,
  appendAgentMessage,
  compactAgentThread,
  conversationIdForAgent,
  conversationIdForTask,
  DEFAULT_AGENT_ID,
  fetchAgentThread,
  patchAgentMessage,
  type ConversationSummary,
} from '../lib/agentChat'
import { canEditAgentMessages, classifyAgentKind, type AgentKind } from '../lib/agentKind'
import {
  composerInsetCustomProperty,
  isPinnedToTranscriptBottom,
  measureComposerDockInset,
  scrollTranscriptToBottom,
} from '../lib/composerInset'
import {
  buildDisplayItems,
  contextTextsForMeter,
  summariesById,
} from '../lib/chatCompact'
import {
  buildChatWsEditFrame,
  buildChatWsFrame,
  buildChatWsUrl,
  buildToolDecisionFrame,
  parseChatWsMessage,
  type ChatWsEvent,
} from '../lib/chatWs'
import { ToolCallPopup } from '../components/ToolCallPopup'
import { PrOpenedCard } from '../components/PrOpenedCard'
import {
  openerChatSearch,
  parsePrOpened,
  type PrOpenedEvent,
  type PrOpenedOpener,
} from '../lib/prOpened'
import { TokenDiagnosticsModal } from '../components/TokenDiagnosticsModal'
import {
  isToolAlwaysAllowed,
  rememberAlwaysAllow,
  upsertToolCall,
  type ToolCallState,
} from '../lib/safety'
import { notifyGenerationComplete } from '../lib/railOrder'
import {
  ALL_MEMBERS_TARGET,
  MANAGE_TEAMS_HREF,
  MANAGE_TEAMS_VALUE,
  fetchTeamRosters,
  memberOptionLabel,
  teamHideId,
  teamThreadId,
} from '../lib/teamRosters'
import { fetchConfiguredRemotes, remoteHideId } from '../lib/remotesCatalog'
import { configuredRemotes } from '../lib/remotes'
import {
  AGENT_REMOTE_BINDINGS_CHANGED_EVENT,
  isRemoteKindAgent,
  loadAgentRemoteBinding,
  remotesListForSelect,
  resolveBoundRemoteId,
  saveAgentRemoteBinding,
} from '../lib/agentRemote'
import {
  publishChatConnection,
  type ChatConnectionStatus,
} from '../lib/chatConnection'
import {
  reconnectBackoffMs,
  shouldAutoReconnect,
  WS_AUTH_REQUIRED_CODE,
} from '../lib/chatReconnect'
import {
  CONTEXT_METER_TOKENS,
  estimateTokensInContext,
  formatTokenCount,
} from '../lib/chatMeter'
import { workingLabel } from '../lib/chatBubble'
import { isExperimentalEnabled } from '../experimental/flags'
import { ChatMessageActions } from '../experimental/ChatMessageActions'
import { agentRole, exampleRoleAgents, isChiefOfStaff, isExampleRole } from '../lib/agentRoles'
import { assignedBlueprintId, AGENT_EDITS_CHANGED_EVENT, editedAgentLabel } from '../lib/agentEdits'
import {
  agentLabel,
  defaultBlueprintId,
  isSupportAgent,
  SUPPORT_AGENT_ID,
  supportTurnExtras,
} from '../lib/supportAgent'
import {
  asTranscriptRole,
  formatDropdownStatus,
  isStatusRole,
  shouldRecordDropdownChange,
  type DropdownKind,
} from '../lib/chatStatus'
import { insertCliSessionNotice } from '../lib/chatTranscript'
import {
  restoreKindForAgent,
  restoredSessionNotice,
  switchedSessionNotice,
} from '../lib/sessionRestore'
import {
  discoverChatClis,
  isCliAgentContext,
  isCliBlueprintId,
  preferredChatCli,
  MANAGE_CLI_VALUE,
  MANAGE_CLI_HREF,
} from '../lib/cliAgentContext'

/** EXPERIMENTAL flags are read once per module load; see experimental/flags.ts. */
const SHOW_MESSAGE_ACTIONS = isExperimentalEnabled('chat_message_actions')

type ConnectionStatus = ChatConnectionStatus

interface ChatMessage {
  /** Stable key; for assistant messages this is the server-issued container id. */
  key: string
  role: 'user' | 'assistant' | 'status'
  text: string
  /** True while the assistant message is still streaming. */
  streaming: boolean
  tools?: ToolCallState[]
  edited?: boolean
  /** REQ-71 chrome — structured PR-opened tool result, not markdown. */
  prOpened?: PrOpenedEvent
}

function chatMessageFromThreadRow(
  message: { role: string; content: string; edited?: boolean },
  index: number,
): ChatMessage {
  const prOpened = parsePrOpened(message.content) ?? undefined
  return {
    key: `hist-${index}-${message.role}`,
    role: asTranscriptRole(message.role),
    text: prOpened ? '' : message.content,
    streaming: false,
    edited: message.edited === true,
    prOpened,
  }
}

/** Post-login return path for the Django session gate (rooted, same-origin). */
export function chatLoginNext(searchParams: URLSearchParams): string {
  const qs = searchParams.toString()
  return qs ? `/chat?${qs}` : '/chat'
}

export function chatLoginHref(searchParams: URLSearchParams): string {
  return `/accounts/login/?next=${encodeURIComponent(chatLoginNext(searchParams))}`
}

export {
  estimateTokensInContext,
  formatElapsed,
  formatTokenCount,
} from '../lib/chatMeter'

interface ReplyTarget {
  key: string
  role: string
  speaker: string
  text: string
}

interface MessageContextMenuState {
  x: number
  y: number
  message: ChatMessage
}

const ChatPage = () => {
  const [searchParams, setSearchParams] = useSearchParams()
  const { addToast, dismissByKind } = useToast()
  const { narrow, railOpen, openRail } = useRailChrome()
  const teamFromUrl = searchParams.get('team') ?? ''
  const remoteFromUrl = searchParams.get('remote') ?? ''
  const sessionFromUrl = searchParams.get('session') ?? ''
  const selectedBlueprint = teamFromUrl || remoteFromUrl
    ? ''
    : defaultBlueprintId(searchParams.get('blueprint'))
  const activeChatAgentId = useMemo(
    () =>
      teamFromUrl
        ? teamHideId(teamFromUrl)
        : remoteFromUrl
        ? remoteHideId(remoteFromUrl)
        : selectedBlueprint,
    [teamFromUrl, remoteFromUrl, selectedBlueprint],
  )
  const [newChatPerTask, setNewChatPerTask] = useState(() =>
    teamFromUrl || remoteFromUrl ? false : loadLocalNewChatPerTask(defaultBlueprintId(searchParams.get('blueprint'))),
  )

  const [threads, setThreads] = useState<Record<string, ChatMessage[]>>({})
  const [restoreNotice, setRestoreNotice] = useState<string | null>(null)
  const [summariesByThread, setSummariesByThread] = useState<
    Record<string, ConversationSummary[]>
  >({})
  const [input, setInput] = useState('')
  const [replyTarget, setReplyTarget] = useState<ReplyTarget | null>(null)
  const [contextMenu, setContextMenu] = useState<MessageContextMenuState | null>(null)
  const [slashDismissed, setSlashDismissed] = useState(false)
  const [slashSelectedIndex, setSlashSelectedIndex] = useState(0)
  const [recentSlashIds, setRecentSlashIds] = useState<string[]>(() => getRecentSlashIds())
  const [dynamicSkills, setDynamicSkills] = useState<{ name: string; description?: string }[]>([])
  const [status, setStatus] = useState<ConnectionStatus>('connecting')
  const [memberTarget, setMemberTarget] = useState(ALL_MEMBERS_TARGET)
  const [connectAttempt, setConnectAttempt] = useState(0)
  const [authRejected, setAuthRejected] = useState(false)
  const [plusOpen, setPlusOpen] = useState(false)
  const [editingKey, setEditingKey] = useState<string | null>(null)
  const [agentKind, setAgentKind] = useState<AgentKind>(() =>
    classifyAgentKind(searchParams.get('remote') ? `remote:${searchParams.get('remote')}` : searchParams.get('blueprint')),
  )
  const [messagesEditable, setMessagesEditable] = useState(() =>
    canEditAgentMessages(searchParams.get('blueprint')) &&
    !searchParams.get('team') &&
    !searchParams.get('remote'),
  )
  const [, setEditsTick] = useState(0)
  const [selectedRemoteId, setSelectedRemoteId] = useState('')
  const [conversationId, setConversationId] = useState(() =>
    teamFromUrl
      ? teamThreadId(teamFromUrl)
      : remoteFromUrl
        ? `remote-${remoteFromUrl}${sessionFromUrl ? `-${sessionFromUrl}` : ''}`
        : sessionFromUrl ||
          conversationIdForTask(agentIdFromBlueprint(selectedBlueprint), {
            newChatPerTask: loadLocalNewChatPerTask(
              defaultBlueprintId(searchParams.get('blueprint')),
            ),
          }),
  )
  const threadKey = teamFromUrl
    ? teamThreadId(teamFromUrl)
    : remoteFromUrl
      ? `remote-${remoteFromUrl}${sessionFromUrl ? `-${sessionFromUrl}` : ''}`
      : sessionFromUrl
        ? `${selectedBlueprint}::${sessionFromUrl}`
        : newChatPerTask
          ? conversationId
          : selectedBlueprint

  const messages = useMemo(() => threads[threadKey] ?? [], [threads, threadKey])
  const summaries = useMemo(
    () => summariesByThread[threadKey] ?? [],
    [summariesByThread, threadKey],
  )
  const displayItems = useMemo(
    () => buildDisplayItems(messages, summaries),
    [messages, summaries],
  )
  const summaryMap = useMemo(() => summariesById(summaries), [summaries])

  const wsRef = useRef<WebSocket | null>(null)
  const emptyRemoteOpenedForRef = useRef('')
  const conversationIdRef = useRef(conversationId)
  conversationIdRef.current = conversationId
  const listEndRef = useRef<HTMLDivElement | null>(null)
  const scrollBoxRef = useRef<HTMLDivElement | null>(null)
  const bottomDockRef = useRef<HTMLDivElement | null>(null)
  const composerRef = useRef<HTMLTextAreaElement | null>(null)
  const plusRef = useRef<HTMLDivElement | null>(null)
  const composerWrapRef = useRef<HTMLDivElement | null>(null)
  const [composerInsetPx, setComposerInsetPx] = useState(0)
  /** Monotonic counter for collision-free user-echo keys. */
  const userKeyCounterRef = useRef(0)
  const prevStatusRef = useRef<ConnectionStatus>('connecting')
  /** Consecutive auto-reconnect attempts since last successful open. */
  const backoffAttemptRef = useRef(0)
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const intentionalCloseRef = useRef(false)
  const lastUserTextRef = useRef('')
  /** Last hydrated agent or team thread; used to clear bubbles only on switch. */
  const lastHydratedAgentRef = useRef<string | null>(null)
  const previewSyncTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // REQ-177: Sync active thread messages to localStorage so rail preview snippets update live.
  // Throttled to 250ms during streaming, and immediate on turn completion / user send.
  useEffect(() => {
    if (!activeChatAgentId) return
    const threadMessages = threads[threadKey]
    if (threadMessages === undefined) return
    const isStreaming = threadMessages.some((m) => m.streaming)
    const sync = () => {
      const persistable = persistableMessages(threadMessages)
      putAgentChatSession(activeChatAgentId, {
        conversationId,
        messages: persistable,
      })
    }

    if (isStreaming) {
      if (!previewSyncTimerRef.current) {
        previewSyncTimerRef.current = setTimeout(() => {
          previewSyncTimerRef.current = null
          sync()
        }, 250)
      }
    } else {
      if (previewSyncTimerRef.current) {
        clearTimeout(previewSyncTimerRef.current)
        previewSyncTimerRef.current = null
      }
      sync()
    }
    return () => {
      if (previewSyncTimerRef.current) {
        clearTimeout(previewSyncTimerRef.current)
        previewSyncTimerRef.current = null
      }
    }
  }, [activeChatAgentId, conversationId, threadKey, threads])

  useEffect(() => {
    setReplyTarget(null)
    setContextMenu(null)
  }, [threadKey])

  useEffect(() => {
    if (!contextMenu) return
    const handleKeyDown = (e: globalThis.KeyboardEvent) => {
      if (e.key === 'Escape') {
        setContextMenu(null)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [contextMenu])

  const handleBubbleContextMenu = useCallback(
    (event: React.MouseEvent<HTMLDivElement>, message: ChatMessage) => {
      if (message.streaming) return
      if (typeof window !== 'undefined' && window.getSelection && !window.getSelection()?.isCollapsed) {
        return
      }
      event.preventDefault()
      setContextMenu({
        x: event.clientX,
        y: event.clientY,
        message,
      })
    },
    [],
  )

  const blueprintsQuery = useQuery({
    queryKey: ['blueprints'],
    queryFn: fetchBlueprints,
  })
  const cliQuery = useQuery({
    queryKey: ['cli-agents'],
    queryFn: fetchCliAgents,
  })
  const teamsQuery = useQuery({
    queryKey: ['team-rosters'],
    queryFn: fetchTeamRosters,
  })
  const remotesQuery = useQuery({
    queryKey: ['configured-remotes'],
    queryFn: fetchConfiguredRemotes,
    retry: 1,
  })
  const remotesListQuery = useQuery({
    queryKey: ['remotes-list'],
    queryFn: fetchRemotes,
    retry: 1,
  })
  const blueprints = exampleRoleAgents(blueprintsQuery.data?.data ?? [])
  const cliAgents = cliQuery.data?.rail ?? []
  const teams = teamsQuery.data ?? []
  const remotes = remotesQuery.data ?? []
  const selectedTeam = teams.find((team) => team.id === teamFromUrl) ?? null
  const selectedRemote = remotes.find((remote) => remote.id === remoteFromUrl) ?? null
  const selectedRemoteSession = selectedRemote?.agents.find((agent) => agent.id === sessionFromUrl)
  const selectedTeamSession = selectedTeam?.members.find((member) => member.id === sessionFromUrl)
  const selectedCli = cliAgents.find((row) => row.id === selectedBlueprint)
  const selectedAgent = blueprints.find((bp) => bp.id === selectedBlueprint)
  const runtimeBlueprint = teamFromUrl ? '' : assignedBlueprintId(selectedBlueprint)
  const fallbackAgentName =
    selectedAgent?.name ||
    selectedCli?.name ||
    (selectedBlueprint === SUPPORT_AGENT_ID ? 'Support' : selectedBlueprint)
  const selectedAgentName = teamFromUrl
    ? selectedTeamSession?.name || selectedTeam?.name || teamFromUrl
    : remoteFromUrl
      ? selectedRemoteSession?.name || selectedRemote?.title || remoteFromUrl
      : editedAgentLabel({
          id: selectedBlueprint,
          name: fallbackAgentName,
        })
  const signInHref = chatLoginHref(searchParams)

  const isRemoteBackedTeam = Boolean(
    selectedTeam && (
      (selectedTeam as { kind?: string }).kind === 'remote' ||
      Boolean((selectedTeam as { remote?: string }).remote) ||
      selectedTeam.members?.some(
        (m) =>
          m.kind === 'remote' ||
          (m as { role?: string }).role === 'remote' ||
          Boolean((m as { remote?: string }).remote),
      )
    ),
  )

  const isRemoteAgent = isRemoteKindAgent({
    remoteFromUrl,
    agentKind,
    blueprintId: selectedBlueprint,
    selectedKind: (selectedAgent as { kind?: string } | undefined)?.kind,
    agentType: (selectedAgent as { agent_type?: string })?.agent_type,
    remote: (selectedAgent as { remote?: string })?.remote,
    tags: (selectedAgent as { tags?: string[] })?.tags,
  }) || Boolean(selectedRemote)

  const showRemotesControl = isRemoteAgent || isRemoteBackedTeam
  const bindingAgentId = remoteFromUrl || (showRemotesControl ? selectedBlueprint : '')
  const persistedRemote = bindingAgentId ? loadAgentRemoteBinding(bindingAgentId) : null
  const remotesCatalog = remotesListForSelect(
    remotesListQuery.data,
    remotes,
    remoteFromUrl
      ? {
          id: remoteFromUrl,
          kind: selectedRemote?.kind || persistedRemote?.kind || remoteFromUrl,
          title: selectedRemote?.title,
        }
      : persistedRemote,
  )
  const configuredRemoteRows = configuredRemotes(remotesCatalog)
  const remotesCatalogReady = !remotesListQuery.isPending && !remotesQuery.isPending
  const showEmptyRemoteChrome =
    showRemotesControl && remotesCatalogReady && configuredRemoteRows.length === 0

  const isCliAgent = Boolean(
    !teamFromUrl &&
      !remoteFromUrl &&
      !isRemoteBackedTeam &&
      !isRemoteAgent &&
      (selectedCli ||
        agentKind === 'cli' ||
        isCliBlueprintId(selectedBlueprint) ||
        isCliAgentContext({
          blueprintId: selectedBlueprint,
          searchParams,
        })),
  )

  const isApiAgent = Boolean(
    !teamFromUrl &&
      !remoteFromUrl &&
      !isRemoteBackedTeam &&
      !isRemoteAgent &&
      !isCliAgent,
  )

  const discoveredClis = useMemo(
    () => discoverChatClis(cliQuery.data, searchParams.get('cli') || selectedCli?.cli),
    [cliQuery.data, searchParams, selectedCli],
  )
  const currentCli = useMemo(() => {
    const fromParam = (searchParams.get('cli') ?? '').trim()
    if (fromParam) return fromParam
    if (selectedCli?.cli) return selectedCli.cli
    return preferredChatCli(discoveredClis, '')
  }, [searchParams, selectedCli, discoveredClis])

  const cliModelsQuery = useQuery({
    queryKey: ['cli-models', currentCli],
    queryFn: () => fetchCliModels(currentCli),
    enabled: Boolean(isCliAgent && currentCli),
    retry: 1,
  })
  const availableCliModels = useMemo(() => {
    const list = cliModelsQuery.data?.models ?? (cliQuery.data as any)?.list_models?.[currentCli] ?? []
    return list.length ? list : ['default']
  }, [cliModelsQuery.data, cliQuery.data, currentCli])

  const currentCliModel = useMemo(() => {
    const fromParam = (searchParams.get('model') ?? '').trim()
    if (fromParam && availableCliModels.includes(fromParam)) return fromParam
    return availableCliModels[0] || 'default'
  }, [searchParams, availableCliModels])
  const recordDropdownChange = useCallback(
    (kind: DropdownKind, fromLabel: string, toLabel: string) => {
      if (!shouldRecordDropdownChange(fromLabel, toLabel)) return
      const statusText = formatDropdownStatus(kind, fromLabel, toLabel)
      const statusMsg: ChatMessage = {
        key: `status-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
        role: 'status',
        text: statusText,
        streaming: false,
      }
      setThreads((prev) => ({
        ...prev,
        [threadKey]: [...(prev[threadKey] ?? []), statusMsg],
      }))
      const agent = teamFromUrl
        ? `team-${teamFromUrl}`
        : remoteFromUrl
          ? `remote-${remoteFromUrl}`
          : selectedBlueprint || DEFAULT_AGENT_ID
      void appendAgentMessage(
        agent,
        { role: 'status', content: statusText },
        conversationIdRef.current || undefined,
      ).catch(() => {})
    },
    [threadKey, teamFromUrl, remoteFromUrl, selectedBlueprint],
  )

  useEffect(() => {
    // REQ-28: a selected composition team uses ?team=; do not clobber it
    // with the Support default (REQ-23 owns send-to-all).
    if (searchParams.get('team') || searchParams.get('remote')) return
    if (!searchParams.get('blueprint')) {
      setSearchParams({ blueprint: SUPPORT_AGENT_ID }, { replace: true })
    }
  }, [searchParams, setSearchParams])

  useEffect(() => {
    if (teamFromUrl && sessionFromUrl) {
      setMemberTarget(sessionFromUrl)
      return
    }
    setMemberTarget(ALL_MEMBERS_TARGET)
  }, [teamFromUrl, sessionFromUrl])

  useEffect(() => {
    const onEdits = () => setEditsTick((tick) => tick + 1)
    window.addEventListener(AGENT_EDITS_CHANGED_EVENT, onEdits)
    window.addEventListener(AGENT_REMOTE_BINDINGS_CHANGED_EVENT, onEdits)
    return () => {
      window.removeEventListener(AGENT_EDITS_CHANGED_EVENT, onEdits)
      window.removeEventListener(AGENT_REMOTE_BINDINGS_CHANGED_EVENT, onEdits)
    }
  }, [])

  useEffect(() => {
    if (!showRemotesControl) return
    setSelectedRemoteId(
      resolveBoundRemoteId({
        remoteFromUrl,
        persisted: persistedRemote,
        agentRemoteId: (selectedAgent as { remote_id?: string })?.remote_id,
        configuredIds: configuredRemoteRows.map((row) => row.id),
      }),
    )
  }, [
    showRemotesControl,
    remoteFromUrl,
    bindingAgentId,
    persistedRemote,
    selectedAgent,
    remotesCatalog,
  ])

  useEffect(() => {
    if (!showEmptyRemoteChrome) return
    const key = bindingAgentId || selectedBlueprint
    if (!key || emptyRemoteOpenedForRef.current === key) return
    emptyRemoteOpenedForRef.current = key
    openSettingsSheet({ section: 'remotes', addRemote: true })
  }, [showEmptyRemoteChrome, bindingAgentId, selectedBlueprint])

  useEffect(() => {
    if (teamFromUrl) {
      setNewChatPerTask(false)
      return
    }
    const agent = agentIdFromBlueprint(selectedBlueprint)
    setNewChatPerTask(loadLocalNewChatPerTask(agent))
    const onChange = (event: Event) => {
      const detail = (event as CustomEvent<AgentSettingsChangedDetail>).detail
      if (detail?.agentId && detail.agentId === agent) {
        setNewChatPerTask(detail.new_chat_per_task)
      }
    }
    window.addEventListener(AGENT_SETTINGS_CHANGED_EVENT, onChange)
    return () => window.removeEventListener(AGENT_SETTINGS_CHANGED_EVENT, onChange)
  }, [selectedBlueprint, teamFromUrl])

  // Per-agent thread: stable conversation id + hydrate from disk/DB.
  // Team threads use a stable team-* conversation id and do not use agent JSON.
  // No history chrome — messages just come back after reload / agent switch.
  useEffect(() => {
    if (teamFromUrl) {
      const key = teamThreadId(teamFromUrl)
      const switched =
        lastHydratedAgentRef.current !== null && lastHydratedAgentRef.current !== key
      lastHydratedAgentRef.current = key
      setConversationId(key)
      setEditingKey(null)
      setAgentKind('api')
      setMessagesEditable(false)
      userKeyCounterRef.current = 0
      if (switched) {
        setThreads((prev) => ({ ...prev, [key]: [] }))
        setSummariesByThread((prev) => ({ ...prev, [key]: [] }))
      }
      let cancelled = false
      ;(async () => {
        const thread = await fetchAgentThread(key, key)
        if (cancelled) return
        setSummariesByThread((prev) => ({
          ...prev,
          [key]: thread.summaries,
        }))
        if (thread.messages.length === 0) {
          setRestoreNotice(null)
          return
        }
        setRestoreNotice(restoredSessionNotice(thread.messages, 'team'))
        setThreads((prev) => ({
          ...prev,
          [key]: thread.messages.map(chatMessageFromThreadRow),
        }))
      })()
      return () => {
        cancelled = true
      }
    }
    if (remoteFromUrl) {
      const key = `remote-${remoteFromUrl}${sessionFromUrl ? `-${sessionFromUrl}` : ''}`
      const switched =
        lastHydratedAgentRef.current !== null && lastHydratedAgentRef.current !== key
      lastHydratedAgentRef.current = key
      setConversationId(key)
      setEditingKey(null)
      setAgentKind('remote')
      setMessagesEditable(false)
      userKeyCounterRef.current = 0
      if (switched) {
        setThreads((prev) => ({ ...prev, [key]: [] }))
        setSummariesByThread((prev) => ({ ...prev, [key]: [] }))
      }
      let cancelled = false
      ;(async () => {
        const thread = await fetchAgentThread(`remote:${remoteFromUrl}`, key)
        if (cancelled) return
        setSummariesByThread((prev) => ({
          ...prev,
          [key]: thread.summaries,
        }))
        if (thread.messages.length === 0) {
          setRestoreNotice(null)
          return
        }
        setRestoreNotice(restoredSessionNotice(thread.messages, 'remote'))
        setThreads((prev) => ({
          ...prev,
          [key]: thread.messages.map(chatMessageFromThreadRow),
        }))
      })()
      return () => {
        cancelled = true
      }
    }

    const agent = agentIdFromBlueprint(selectedBlueprint)
    const fresh = !sessionFromUrl && newChatPerTask
    const nextId = fresh
      ? conversationIdForTask(agent, { newChatPerTask: true })
      : sessionFromUrl || conversationIdForAgent(agent)
    const hydrateKey = sessionFromUrl
      ? `${agent}::${sessionFromUrl}`
      : fresh
        ? nextId
        : agent
    const switched =
      lastHydratedAgentRef.current !== null &&
      lastHydratedAgentRef.current !== hydrateKey
    lastHydratedAgentRef.current = hydrateKey
    setConversationId(nextId)
    setEditingKey(null)
    setAgentKind(classifyAgentKind(selectedBlueprint))
    setMessagesEditable(canEditAgentMessages(selectedBlueprint) && !selectedCli)
    userKeyCounterRef.current = 0
    if (switched) {
      setThreads((prev) => ({ ...prev, [threadKey]: [] }))
      setSummariesByThread((prev) => ({ ...prev, [threadKey]: [] }))
    }
    if (fresh) {
      // New empty session — do not restore a prior transcript.
      setRestoreNotice(null)
      return
    }
    let cancelled = false
    ;(async () => {
      const thread = await fetchAgentThread(agent, sessionFromUrl || undefined)
      if (cancelled) return
      setAgentKind(thread.kind ?? classifyAgentKind(selectedBlueprint))
      setMessagesEditable(
        !teamFromUrl &&
          !remoteFromUrl &&
          (thread.editable ?? canEditAgentMessages(selectedBlueprint, thread.kind)),
      )
      setSummariesByThread((prev) => ({
        ...prev,
        [threadKey]: thread.summaries,
      }))
      if (switched && sessionFromUrl) {
        setRestoreNotice(switchedSessionNotice(thread.session_title || thread.conversation_id))
        if (thread.messages.length === 0) return
      } else if (thread.messages.length === 0) {
        setRestoreNotice(null)
        return
      } else {
        setRestoreNotice(restoredSessionNotice(thread.messages, restoreKindForAgent(agent)))
      }
      setThreads((prev) => ({
        ...prev,
        [threadKey]: thread.messages.map(chatMessageFromThreadRow),
      }))
    })()
    return () => {
      cancelled = true
    }
  }, [selectedBlueprint, sessionFromUrl, teamFromUrl, remoteFromUrl, newChatPerTask, threadKey, selectedCli])

  const attachToolToThread = useCallback(
    (tool: ToolCallState) => {
      setThreads((prev) => {
        const current = prev[threadKey] ?? []
        const targetIndex = [...current]
          .reverse()
          .findIndex((message) => message.role === 'assistant')
        const index = targetIndex === -1 ? -1 : current.length - 1 - targetIndex
        if (index === -1) {
          return {
            ...prev,
            [threadKey]: [
              ...current,
              {
                key: `tool-host-${tool.id}`,
                role: 'assistant' as const,
                text: '',
                streaming: true,
                tools: [tool],
              },
            ],
          }
        }
        const next = [...current]
        const host = next[index]!
        next[index] = { ...host, tools: upsertToolCall(host.tools ?? [], tool) }
        return { ...prev, [threadKey]: next }
      })
    },
    [threadKey],
  )

  const sendToolDecision = useCallback((id: string, decision: 'allow' | 'always' | 'deny') => {
    const ws = wsRef.current
    if (!ws || ws.readyState !== WebSocket.OPEN) return
    ws.send(buildToolDecisionFrame(id, decision))
  }, [])

  const jumpToPrOpener = useCallback(
    (opener: PrOpenedOpener) => {
      setSearchParams(openerChatSearch(opener))
    },
    [setSearchParams],
  )

  const handleWsEvent = useCallback(
    (event: ChatWsEvent) => {
      if (event.kind === 'unknown') {
        console.warn('Unrecognised chat websocket frame:', event.raw)
        return
      }
      if (event.kind === 'tool_status') {
        attachToolToThread({
          id: event.id,
          name: event.name,
          status: event.status,
          agentId: event.agentId,
          needsApproval: false,
        })
        return
      }
      if (event.kind === 'pr_opened') {
        setThreads((prev) => {
          const current = prev[threadKey] ?? []
          return {
            ...prev,
            [threadKey]: [
              ...current,
              {
                key: `pr-opened-${current.length}-${Date.now()}`,
                role: 'status' as const,
                text: '',
                streaming: false,
                prOpened: event.event,
              },
            ],
          }
        })
        return
      }
      if (event.kind === 'tool_approval') {
        const agentId = event.agentId || selectedBlueprint || threadKey
        if (isToolAlwaysAllowed(agentId, event.name)) {
          sendToolDecision(event.id, 'always')
          attachToolToThread({
            id: event.id,
            name: event.name,
            status: 'allowed',
            agentId,
            needsApproval: false,
            concerned: true,
          })
          return
        }
        attachToolToThread({
          id: event.id,
          name: event.name,
          status: 'running',
          agentId,
          needsApproval: true,
          concerned: true,
        })
        return
      }
      setThreads((prev) => {
        const current = prev[threadKey] ?? []
        let next = current
        switch (event.kind) {
          case 'user_echo':
            userKeyCounterRef.current += 1
            next = [
              ...current,
              {
                key: `user-${userKeyCounterRef.current}-${Date.now()}`,
                role: 'user',
                text: event.text,
                streaming: false,
              },
            ]
            break
          case 'assistant_start':
            if (current.some((m) => m.key === event.id)) return prev
            next = [...current, { key: event.id, role: 'assistant', text: '', streaming: true }]
            break
          case 'assistant_chunk':
            next = current.map((m) =>
              m.key === event.id ? { ...m, text: m.text + event.text } : m,
            )
            break
          case 'assistant_final':
            next = current.map((m) =>
              m.key === event.id ? { ...m, text: event.text, streaming: false } : m,
            )
            break
          case 'status':
            next = insertCliSessionNotice(current, {
              key: `status-${current.length}-${Date.now()}`,
              role: 'status',
              text: event.text,
              streaming: false,
            })
            break
        }
        return { ...prev, [threadKey]: next }
      })
      if (event.kind === 'assistant_final') {
        if (activeChatAgentId) {
          notifyGenerationComplete(activeChatAgentId)
        }
      }
    },
    [activeChatAgentId, attachToolToThread, sendToolDecision, threadKey],
  )

  useEffect(() => {
    let opened = false
    intentionalCloseRef.current = false
    setStatus('connecting')
    setAuthRejected(false)

    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current)
      reconnectTimerRef.current = null
    }

    let ws: WebSocket
    try {
      ws = new WebSocket(
        buildChatWsUrl(conversationId, teamFromUrl ? undefined : runtimeBlueprint || undefined),
      )
    } catch {
      setStatus('failed')
      const attempt = backoffAttemptRef.current
      if (shouldAutoReconnect(1006, false, attempt)) {
        const delay = reconnectBackoffMs(attempt)
        backoffAttemptRef.current = attempt + 1
        reconnectTimerRef.current = setTimeout(() => {
          reconnectTimerRef.current = null
          setConnectAttempt((n) => n + 1)
        }, delay)
      }
      return
    }
    wsRef.current = ws

    ws.onopen = () => {
      opened = true
      backoffAttemptRef.current = 0
      setStatus('open')
    }
    ws.onmessage = (event: MessageEvent) => {
      if (typeof event.data === 'string') {
        handleWsEvent(parseChatWsMessage(event.data))
      }
    }
    ws.onclose = (event: CloseEvent) => {
      if (wsRef.current === ws) wsRef.current = null
      const rejected = event.code === WS_AUTH_REQUIRED_CODE
      setAuthRejected(rejected)
      setStatus(opened ? 'closed' : 'failed')
      setThreads((prev) => {
        const current = prev[threadKey]
        if (!current || !current.some((m) => m.streaming)) return prev
        return {
          ...prev,
          [threadKey]: current.map((m) => (m.streaming ? { ...m, streaming: false } : m)),
        }
      })

      const attempt = backoffAttemptRef.current
      if (shouldAutoReconnect(event.code, intentionalCloseRef.current, attempt)) {
        const delay = reconnectBackoffMs(attempt)
        backoffAttemptRef.current = attempt + 1
        reconnectTimerRef.current = setTimeout(() => {
          reconnectTimerRef.current = null
          setConnectAttempt((n) => n + 1)
        }, delay)
      }
    }

    return () => {
      intentionalCloseRef.current = true
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current)
        reconnectTimerRef.current = null
      }
      ws.onopen = null
      ws.onmessage = null
      ws.onclose = null
      ws.close()
      if (wsRef.current === ws) wsRef.current = null
    }
  }, [connectAttempt, handleWsEvent, conversationId, runtimeBlueprint, teamFromUrl])

  useEffect(() => {
    publishChatConnection(status)
  }, [status])

  const pinnedToBottomRef = useRef(true)

  const applyComposerInset = useCallback(() => {
    const next = measureComposerDockInset(bottomDockRef.current)
    setComposerInsetPx((prev) => (prev === next ? prev : next))
  }, [])

  useLayoutEffect(() => {
    applyComposerInset()
  }, [applyComposerInset, messages, replyTarget, input])

  useLayoutEffect(() => {
    const dock = bottomDockRef.current
    if (!dock || typeof ResizeObserver === 'undefined') return undefined
    const observer = new ResizeObserver(() => {
      applyComposerInset()
    })
    observer.observe(dock)
    return () => observer.disconnect()
  }, [applyComposerInset])

  useEffect(() => {
    if (pinnedToBottomRef.current) {
      scrollTranscriptToBottom(scrollBoxRef.current, listEndRef.current)
    }
  }, [messages, composerInsetPx])

  useEffect(() => {
    const wasOpen = prevStatusRef.current === 'open'
    prevStatusRef.current = status
    if (status === 'open' && !wasOpen && connectAttempt > 0) {
      composerRef.current?.focus()
    }
  }, [status, connectAttempt])

  const reconnect = useCallback(() => {
    backoffAttemptRef.current = 0
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current)
      reconnectTimerRef.current = null
    }
    setConnectAttempt((n) => n + 1)
  }, [])

  useEffect(() => {
    if (status === 'open') {
      dismissByKind(TOAST_KIND_WS_DISCONNECT)
      return
    }
    if (status !== 'failed' && status !== 'closed') return
    const title = authRejected
      ? 'Chat unavailable — sign in required'
      : status === 'failed'
        ? 'Chat websocket unreachable'
        : 'Chat disconnected'
    const detail = authRejected
      ? 'Live chat needs a Django session cookie. Sign in, then reconnect.'
      : status === 'failed'
        ? 'ASGI is not serving /ws/ or Origin does not match ALLOWED_HOSTS.'
        : 'The chat websocket closed. Message history is kept.'
    addToast({
      kind: TOAST_KIND_WS_DISCONNECT,
      type: 'error',
      title,
      message: (
        <span>
          {detail}{' '}
          {authRejected ? (
            <a href={signInHref} className="link">
              Sign in
            </a>
          ) : null}{' '}
          <button type="button" className="link" onClick={reconnect}>
            Reconnect
          </button>
        </span>
      ),
      position: 'bottom-right',
    })
  }, [status, authRejected, signInHref, addToast, dismissByKind, reconnect])

  const hasSendableDraft = input.trim().length > 0
  const canSend = status === 'open' && hasSendableDraft

  const sendText = useCallback(
    (text: string) => {
      const ws = wsRef.current
      const trimmed = text.trim()
      if (!trimmed || !ws || ws.readyState !== WebSocket.OPEN) return
      lastUserTextRef.current = trimmed
      // Team compose adds params { team, target: "all" | memberId }.
      if (teamFromUrl) {
        ws.send(
          buildChatWsFrame(trimmed, undefined, {
            team: teamFromUrl,
            target: memberTarget || ALL_MEMBERS_TARGET,
          }),
        )
        return
      }
      const supportParams = isSupportAgent({
        id: runtimeBlueprint || selectedBlueprint || SUPPORT_AGENT_ID,
      })
        ? supportTurnExtras()
        : undefined
      const selectedModelParam = (searchParams.get('model') ?? '').trim()
      const cliParams = isCliAgent
        ? {
            cli: currentCli,
            ...(selectedModelParam && selectedModelParam !== 'default' ? { model: selectedModelParam } : {}),
          }
        : isApiAgent && selectedModelParam && selectedModelParam !== 'default'
          ? { model: selectedModelParam }
          : selectedCli
            ? { cli: selectedCli.cli }
            : newChatPerTask
              ? { new_session: messages.length === 0 }
              : undefined
      ws.send(
        buildChatWsFrame(
          trimmed,
          runtimeBlueprint || selectedBlueprint || undefined,
          supportParams || cliParams
            ? { ...cliParams, ...supportParams }
            : undefined,
        ),
      )
    },
    [
      runtimeBlueprint,
      selectedBlueprint,
      selectedCli,
      isCliAgent,
      currentCli,
      currentCliModel,
      isApiAgent,
      teamFromUrl,
      memberTarget,
      newChatPerTask,
      messages.length,
    ],
  )

  const saveEditedMessage = useCallback(
    async (index: number, nextText: string) => {
      if (!messagesEditable) return
      const current = threads[threadKey] ?? []
      const target = current[index]
      if (!target || target.streaming) return
      setThreads((prev) => {
        const list = prev[threadKey] ?? []
        if (!list[index]) return prev
        const next = list.slice()
        next[index] = { ...next[index], text: nextText, edited: true }
        return { ...prev, [threadKey]: next }
      })
      setEditingKey(null)
      const ws = wsRef.current
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(buildChatWsEditFrame(index, nextText))
      }
      try {
        await patchAgentMessage(agentIdFromBlueprint(selectedBlueprint), {
          index,
          content: nextText,
          conversation_id: conversationIdRef.current,
        })
      } catch {
        addToast({
          type: 'error',
          title: 'Could not save edit',
          message: 'The message was updated in this view, but persist failed.',
        })
      }
    },
    [addToast, messagesEditable, selectedBlueprint, threadKey, threads],
  )

  const handleSend = (event: FormEvent) => {
    event.preventDefault()
    if (!canSend) return
    const quotePrefix = replyTarget ? (replyTarget.speaker ? `> **${replyTarget.speaker}**: ` : `> `) : ''
    const textToSend = replyTarget
      ? `${quotePrefix}${replyTarget.text.replace(/\r\n/g, '\n').split('\n').join('\n> ')}\n\n${input}`
      : input
    sendText(textToSend)
    setInput('')
    setReplyTarget(null)
  }

  // Dynamic skills loading for slash catalog (REQ-169)
  useEffect(() => {
    let unmounted = false
    void fetchConfigOptions()
      .then((opts) => {
        if (!unmounted && opts?.skills) {
          setDynamicSkills(
            opts.skills.map((s) => ({ name: s.name, description: s.description })),
          )
        }
      })
      .catch(() => {
        // Silently ignore if config options endpoint is unavailable
      })
    return () => {
      unmounted = true
    }
  }, [])

  const slashCatalog = useMemo(() => buildSlashCatalog(dynamicSkills), [dynamicSkills])
  const isSlashOpen = input.startsWith('/') && !slashDismissed
  const slashQuery = input.startsWith('/') ? input.slice(1) : ''
  const filteredSlashItems = useMemo(
    () => filterSlashItems(slashCatalog, slashQuery, recentSlashIds),
    [slashCatalog, slashQuery, recentSlashIds],
  )

  useEffect(() => {
    setSlashSelectedIndex(0)
  }, [slashQuery])

  useEffect(() => {
    if (!isSlashOpen) return
    const onPointerDown = (event: MouseEvent | TouchEvent) => {
      if (composerWrapRef.current && !composerWrapRef.current.contains(event.target as Node)) {
        setSlashDismissed(true)
      }
    }
    document.addEventListener('mousedown', onPointerDown)
    document.addEventListener('touchstart', onPointerDown)
    return () => {
      document.removeEventListener('mousedown', onPointerDown)
      document.removeEventListener('touchstart', onPointerDown)
    }
  }, [isSlashOpen])

  const handleInputChange = (e: ChangeEvent<HTMLTextAreaElement>) => {
    const val = e.target.value
    if (val.startsWith('/') && !input.startsWith('/')) {
      setSlashDismissed(false)
      setSlashSelectedIndex(0)
    }
    setInput(val)
  }

  const handleMic = () => {
    type SpeechRec = {
      start: () => void
      onresult: ((event: { results: Array<Array<{ transcript: string }>> }) => void) | null
    }
    const Ctor = (
      window as unknown as {
        SpeechRecognition?: new () => SpeechRec
        webkitSpeechRecognition?: new () => SpeechRec
      }
    ).SpeechRecognition ||
      (window as unknown as { webkitSpeechRecognition?: new () => SpeechRec }).webkitSpeechRecognition
    if (!Ctor) {
      addToast({
        type: 'info',
        title: 'Voice input',
        message: 'Speech recognition is not available in this browser.',
      })
      return
    }
    const recognition = new Ctor()
    recognition.onresult = (event) => {
      const spoken = event.results?.[0]?.[0]?.transcript
      if (spoken) setInput((prev) => (prev ? `${prev} ${spoken}` : spoken))
    }
    recognition.start()
  }

  useEffect(() => {
    if (!plusOpen) return
    const onPointer = (event: Event) => {
      if (plusRef.current && !plusRef.current.contains(event.target as Node)) {
        setPlusOpen(false)
      }
    }
    window.addEventListener('mousedown', onPointer)
    return () => window.removeEventListener('mousedown', onPointer)
  }, [plusOpen])

  const streamingMessage = messages.find((message) => message.streaming)
  const wasStreamingRef = useRef(false)
  useEffect(() => {
    if (streamingMessage) {
      wasStreamingRef.current = true
    } else if (wasStreamingRef.current) {
      wasStreamingRef.current = false
      if (activeChatAgentId) {
        notifyGenerationComplete(activeChatAgentId)
      }
    }
  }, [streamingMessage, activeChatAgentId])

  const handleCompact = useCallback(async () => {
    setPlusOpen(false)
    if (messages.length === 0) {
      addToast({
        type: 'info',
        title: 'Compact',
        message: 'Nothing to compact yet.',
      })
      return
    }
    try {
      const result = await compactAgentThread({
        conversationId,
        agentId: teamFromUrl || agentIdFromBlueprint(selectedBlueprint),
        messages: messages.map((message) => ({
          role: message.role,
          content: message.text,
        })),
      })
      setSummariesByThread((prev) => ({ ...prev, [threadKey]: result.summaries }))
    } catch {
      addToast({
        type: 'error',
        title: 'Compact failed',
        message: 'Could not compact this chat. Sign in and try again.',
      })
    }
  }, [addToast, conversationId, messages, selectedBlueprint, teamFromUrl, threadKey])

  const handleSelectSlashItem = useCallback(
    (item: SlashItem) => {
      recordRecentSlashId(item.id)
      setRecentSlashIds(getRecentSlashIds())
      setSlashDismissed(true)

      if (item.id === 'compact') {
        void handleCompact()
        setInput('')
      } else {
        setInput(`${item.command} `)
      }
      setTimeout(() => {
        composerRef.current?.focus()
      }, 0)
    },
    [handleCompact],
  )

  const handleComposerKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (isSlashOpen) {
      if (event.key === 'ArrowDown') {
        event.preventDefault()
        setSlashSelectedIndex((prev) =>
          filteredSlashItems.length > 0 ? (prev + 1) % filteredSlashItems.length : 0,
        )
        return
      }
      if (event.key === 'ArrowUp') {
        event.preventDefault()
        setSlashSelectedIndex((prev) =>
          filteredSlashItems.length > 0
            ? (prev - 1 + filteredSlashItems.length) % filteredSlashItems.length
            : 0,
        )
        return
      }
      if (event.key === 'Enter' || event.key === 'Tab') {
        if (filteredSlashItems.length > 0) {
          event.preventDefault()
          const selected = filteredSlashItems[slashSelectedIndex] || filteredSlashItems[0]
          if (selected) {
            handleSelectSlashItem(selected)
            return
          }
        }
      }
      if (event.key === 'Escape') {
        event.preventDefault()
        setSlashDismissed(true)
        return
      }
    }

    if (event.key === 'Escape') {
      if (replyTarget) {
        event.preventDefault()
        setReplyTarget(null)
        return
      }
      if (input.length > 0) {
        event.preventDefault()
        setInput('')
        return
      }
    }
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      if (status === 'open' && input.trim().length > 0) {
        const quotePrefix = replyTarget ? (replyTarget.speaker ? `> **${replyTarget.speaker}**: ` : `> `) : ''
        const textToSend = replyTarget
          ? `${quotePrefix}${replyTarget.text.replace(/\r\n/g, '\n').split('\n').join('\n> ')}\n\n${input}`
          : input
        sendText(textToSend)
        setInput('')
        setReplyTarget(null)
      }
    }
  }

  const tokenCount = estimateTokensInContext(contextTextsForMeter(messages, summaries))
  const tokenPct = Math.min(100, Math.round((tokenCount / CONTEXT_METER_TOKENS) * 100))
  const [tokenDiagOpen, setTokenDiagOpen] = useState(false)

  const userTexts = useMemo(
    () => messages.filter((m) => m.role === 'user').map((m) => m.text),
    [messages],
  )
  const assistantTexts = useMemo(
    () => messages.filter((m) => m.role === 'assistant').map((m) => m.text),
    [messages],
  )
  const inputTokens = useMemo(() => estimateTokensInContext(userTexts), [userTexts])
  const outputTokens = useMemo(() => estimateTokensInContext(assistantTexts), [assistantTexts])
  const toolCallsCount = useMemo(
    () => messages.reduce((sum, m) => sum + (m.tools?.length ?? 0), 0),
    [messages],
  )
  const userMessageCount = useMemo(
    () => messages.filter((m) => m.role === 'user').length,
    [messages],
  )
  const assistantMessageCount = useMemo(
    () => messages.filter((m) => m.role === 'assistant').length,
    [messages],
  )
  const composerPlaceholder = replyTarget ? 'Reply…' : 'Message …'
  const workingTip = workingLabel(selectedAgentName)

  const statusLabel = useMemo(() => {
    if (status === 'open') return ''
    if (status === 'connecting') return 'Connecting…'
    if (authRejected) return 'Unavailable — sign in required'
    if (status === 'failed') return 'Unavailable — websocket unreachable'
    return 'Disconnected'
  }, [authRejected, status])

  return (
    <div className="os-chat flex h-full min-h-0 w-full flex-col">
      <header className="os-chat-header">
        <div className="os-chat-header__identity flex min-w-0 items-center gap-2 group">
          {narrow ? (
            <button
              type="button"
              className="btn btn-ghost btn-sm btn-square shrink-0"
              aria-label="Open agent list"
              aria-expanded={railOpen}
              onClick={openRail}
            >
              <PanelLeft className="h-5 w-5" aria-hidden="true" />
            </button>
          ) : null}
          <div
            className="os-navbar-identity-card flex min-w-0 items-center gap-2 rounded-lg px-2 py-1 -my-1 border border-transparent transition-colors hover:bg-base-200/50 hover:border-base-content/10 cursor-pointer"
            data-testid="selected-agent-header"
            role="button"
            tabIndex={0}
            aria-label={`Agent identity: ${selectedAgentName}`}
            onClick={() => {
              if (!teamFromUrl && selectedBlueprint) {
                openAgentEditor({
                  agentId: selectedBlueprint,
                })
                return
              }
              if (teamFromUrl) {
                openSettingsSheet({
                  section: 'definition',
                  definitionKind: 'team',
                  definitionId: teamFromUrl,
                  teamId: teamFromUrl,
                })
                return
              }
              const role = agentRole({
                id: selectedBlueprint,
                name: selectedAgentName,
                role: selectedAgent?.role,
              })
              openSettingsSheet({
                section: 'definition',
                definitionKind: isExampleRole(role) || isChiefOfStaff(role) ? 'role' : 'blueprint',
                definitionId: selectedBlueprint,
                blueprintId: selectedBlueprint,
              })
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault()
                if (!teamFromUrl && selectedBlueprint) {
                  openAgentEditor({
                    agentId: selectedBlueprint,
                  })
                  return
                }
                if (teamFromUrl) {
                  openSettingsSheet({
                    section: 'definition',
                    definitionKind: 'team',
                    definitionId: teamFromUrl,
                    teamId: teamFromUrl,
                  })
                  return
                }
                const role = agentRole({
                  id: selectedBlueprint,
                  name: selectedAgentName,
                  role: selectedAgent?.role,
                })
                openSettingsSheet({
                  section: 'definition',
                  definitionKind: isExampleRole(role) || isChiefOfStaff(role) ? 'role' : 'blueprint',
                  definitionId: selectedBlueprint,
                  blueprintId: selectedBlueprint,
                })
              }
            }}
          >
            {!teamFromUrl ? (
              <AgentAvatar
                src={selectedAgent?.avatar_path}
                agentId={agentIdFromBlueprint(selectedBlueprint)}
                active={Boolean(streamingMessage)}
                size="lg"
                className="os-chat-header__avatar shrink-0"
              />
            ) : null}
            <h1 className="truncate text-base font-semibold tracking-tight">
              <button
                type="button"
                className="os-identity-btn truncate text-left"
                aria-label={`Open ${selectedAgentName} definition`}
                onClick={(e) => {
                  e.stopPropagation()
                  if (teamFromUrl) {
                    openSettingsSheet({
                      section: 'definition',
                      definitionKind: 'team',
                      definitionId: teamFromUrl,
                      teamId: teamFromUrl,
                    })
                    return
                  }
                  const role = agentRole({
                    id: selectedBlueprint,
                    name: selectedAgentName,
                    role: selectedAgent?.role,
                  })
                  openSettingsSheet({
                    section: 'definition',
                    definitionKind: isExampleRole(role) || isChiefOfStaff(role) ? 'role' : 'blueprint',
                    definitionId: selectedBlueprint,
                    blueprintId: selectedBlueprint,
                  })
                }}
              >
                {selectedAgentName}
              </button>
            </h1>
            {!teamFromUrl && selectedBlueprint ? (
              <div className="tooltip tooltip-bottom shrink-0" data-tip="Edit agent">
                <button
                  type="button"
                  className="btn btn-ghost btn-sm btn-square os-navbar-edit-btn"
                  aria-label="Edit agent"
                  onClick={(e) => {
                    e.stopPropagation()
                    openAgentEditor({
                      agentId: selectedBlueprint,
                    })
                  }}
                >
                  <Pencil className="h-4 w-4" aria-hidden="true" />
                </button>
              </div>
            ) : null}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            className="btn btn-ghost btn-xs h-auto p-1 gap-1.5 font-normal text-inherit hover:bg-base-300/40 normal-case shrink-0"
            aria-label="Session token usage"
            data-testid="token-meter-button"
            onClick={() => setTokenDiagOpen(true)}
          >
            <div
              className="h-1 w-14 overflow-hidden rounded-full bg-base-300"
              role="meter"
              aria-label="Tokens in context"
              aria-valuemin={0}
              aria-valuemax={CONTEXT_METER_TOKENS}
              aria-valuenow={tokenCount}
            >
              <div
                className="h-full rounded-full bg-base-content/45"
                style={{ width: `${Math.max(tokenCount > 0 ? 4 : 0, tokenPct)}%` }}
              />
            </div>
            <span className="tabular-nums whitespace-nowrap text-xs">{formatTokenCount(tokenCount)} tok</span>
          </button>
          {showEmptyRemoteChrome ? (
            <button
              type="button"
              className="btn btn-sm h-8 border border-base-300 bg-base-100"
              onClick={() => openSettingsSheet({ section: 'remotes', addRemote: true })}
            >
              Add remote
            </button>
          ) : showRemotesControl ? (
            <RemoteSelect
              remotes={remotesCatalog}
              value={selectedRemoteId}
              onChange={(nextId) => {
                setSelectedRemoteId(nextId)
                const remote = configuredRemoteRows.find((row) => row.id === nextId)
                if (bindingAgentId && remote) {
                  saveAgentRemoteBinding(bindingAgentId, {
                    id: remote.id,
                    kind: remote.kind || remote.id,
                  })
                } else if (bindingAgentId && !nextId) {
                  saveAgentRemoteBinding(bindingAgentId, null)
                }
                if (remoteFromUrl && nextId && nextId !== remoteFromUrl) {
                  setSearchParams((prev) => {
                    const params = new URLSearchParams(prev)
                    params.set('remote', nextId)
                    params.delete('session')
                    return params
                  })
                }
              }}
              size="sm"
              className="h-8 max-w-[10rem]"
            />
          ) : null}
          {teamFromUrl ? (
            <select
              className="select select-sm h-8 max-w-[12rem] border border-base-300 bg-base-100"
              value={memberTarget}
              aria-label="Team members"
              onChange={(e) => {
                const value = e.target.value
                if (value === MANAGE_TEAMS_VALUE) {
                  if (teamFromUrl) {
                    window.location.assign(`${MANAGE_TEAMS_HREF}#${encodeURIComponent(teamFromUrl)}`)
                  } else {
                    window.location.assign(MANAGE_TEAMS_HREF)
                  }
                  return
                }
                const prev = memberTarget
                const prevMember = (selectedTeam?.members ?? []).find((m) => m.id === prev)
                const nextMember = (selectedTeam?.members ?? []).find((m) => m.id === value)
                const fromLabel = prev === ALL_MEMBERS_TARGET ? 'All members' : memberOptionLabel(prevMember || { id: prev, name: prev })
                const toLabel = value === ALL_MEMBERS_TARGET ? 'All members' : memberOptionLabel(nextMember || { id: value, name: value })
                setMemberTarget(value)
                recordDropdownChange('team', fromLabel, toLabel)
              }}
            >
              <option value={ALL_MEMBERS_TARGET}>All members</option>
              {(selectedTeam?.members ?? []).map((member) => (
                <option key={member.id} value={member.id}>
                  {memberOptionLabel(member)}
                </option>
              ))}
              <option disabled aria-hidden="true">
                ──────────
              </option>
              <option value={MANAGE_TEAMS_VALUE}>Manage Team</option>
            </select>
          ) : null}
          {isCliAgent ? (
            <>
              <select
                className="select select-sm h-8 max-w-[10rem] border border-base-300 bg-base-100"
                value={currentCli}
                aria-label="CLI"
                data-testid="cli-select"
                onChange={(e) => {
                  const nextCli = e.target.value
                  if (nextCli === MANAGE_CLI_VALUE) {
                    window.location.assign(MANAGE_CLI_HREF)
                    return
                  }
                  const prev = currentCli
                  setSearchParams(
                    (prevParams) => {
                      const nextParams = new URLSearchParams(prevParams)
                      nextParams.set('cli', nextCli)
                      return nextParams
                    },
                    { replace: true },
                  )
                  recordDropdownChange('cli', prev, nextCli)
                }}
              >
                {discoveredClis.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
                <option disabled aria-hidden="true">
                  ──────────
                </option>
                <option value={MANAGE_CLI_VALUE}>Manage Cli</option>
              </select>
              <select
                className="select select-sm h-8 max-w-[10rem] border border-base-300 bg-base-100"
                value={currentCliModel}
                aria-label="Model"
                data-testid="cli-model-select"
                onChange={(e) => {
                  const nextModel = e.target.value
                  const prev = currentCliModel
                  setSearchParams(
                    (prevParams) => {
                      const nextParams = new URLSearchParams(prevParams)
                      nextParams.set('model', nextModel)
                      return nextParams
                    },
                    { replace: true },
                  )
                  recordDropdownChange('model', prev, nextModel)
                }}
              >
                {availableCliModels.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
            </>
          ) : null}
          <div
            className="flex items-center gap-2"
            role="toolbar"
            aria-label="Chat tools"
          >
            <ComputerControlStub />
            <ThemeToggle />
            <button
              type="button"
              className="btn btn-ghost btn-sm btn-square"
              aria-label="Open settings"
              aria-haspopup="dialog"
              onClick={() => window.dispatchEvent(new CustomEvent(OPEN_SETTINGS_EVENT))}
            >
              <Settings className="h-4 w-4" aria-hidden="true" />
            </button>
          </div>
        </div>
      </header>

      <span role="status" aria-live="polite" aria-atomic="true" aria-label="Connection status" className="sr-only">
        {statusLabel}
      </span>

      <div
        ref={scrollBoxRef}
        className="os-chat-transcript min-h-0 flex-1 space-y-1 overflow-y-auto px-2 py-3 sm:px-3 select-none outline-none focus:outline-none flex flex-col justify-between relative"
        style={composerInsetCustomProperty(composerInsetPx) as CSSProperties}
        aria-live="polite"
        role="log"
        aria-label="Conversation"
        data-agent-kind={
          remoteFromUrl || isRemoteAgent || agentKind === 'remote'
            ? 'remote'
            : isCliAgent
              ? 'cli'
              : agentKind
        }
        data-messages-editable={messagesEditable && !isCliAgent && agentKind !== 'remote' ? 'true' : 'false'}
        data-composer-inset={composerInsetPx}
        tabIndex={0}
        onScroll={(e) => {
          pinnedToBottomRef.current = isPinnedToTranscriptBottom(e.currentTarget, composerInsetPx)
        }}
      >
        <div className="os-chat-messages space-y-1 flex-1" data-testid="chat-messages-container">
        {messages.length === 0 ? (
          <div className="flex h-full min-h-64 flex-col items-center justify-center gap-2 text-center text-base-content/45">
            <p className="text-sm">Message {selectedAgentName}</p>
          </div>
        ) : (
          <>
          {restoreNotice ? (
            <p className="os-chat-status" data-role="status" data-testid="chat-status">
              <span>{restoreNotice}</span>
            </p>
          ) : null}
          {displayItems.map((item, idx) => {
            if (item.kind === 'summary') {
              return (
                <SummaryBlock
                  key={`sum-${item.summary.id}`}
                  summary={item.summary}
                  byId={summaryMap}
                />
              )
            }
            const message = item.message
            const liveMessage = messages.find((row) => row.key === message.key)
            const prOpened = liveMessage?.prOpened
            if (prOpened) {
              const openerId = prOpened.opener?.agentId
              const openerAgent = openerId
                ? blueprints.find((bp) => bp.id === openerId) ||
                  cliAgents.find((row) => row.id === openerId)
                : undefined
              const openerLabel =
                prOpened.opener?.name ||
                (openerAgent
                  ? editedAgentLabel({
                      id: openerId || '',
                      name: openerAgent.name || openerId,
                    })
                  : openerId)
              return (
                <div key={message.key} className="os-pr-opened-wrap my-2">
                  <PrOpenedCard
                    event={prOpened}
                    currentAgentId={activeChatAgentId}
                    currentConversationId={conversationId}
                    openerName={openerLabel}
                    openerAvatarSrc={(openerAgent as { avatar_path?: string } | undefined)?.avatar_path}
                    onJumpToOpener={jumpToPrOpener}
                  />
                </div>
              )
            }
            if (isStatusRole(message.role)) {
              return (
                <p
                  key={message.key}
                  className="os-chat-status"
                  data-role="status"
                  data-testid="chat-status"
                >
                  <span>{message.text}</span>
                </p>
              )
            }
            const isLast = idx === displayItems.length - 1
            const retryEnabled =
              SHOW_MESSAGE_ACTIONS &&
              isLast &&
              message.role === 'assistant' &&
              !message.streaming &&
              lastUserTextRef.current.length > 0
            const messageIndex = messages.findIndex((row) => row.key === message.key)
            const canEditThis =
              messagesEditable &&
              !selectedCli &&
              !message.streaming &&
              (message.role === 'user' || message.role === 'assistant')
            return (
              <div
                key={message.key}
                onContextMenu={(e) => handleBubbleContextMenu(e, message)}
              >
                <ChatMessageBubble
                  role={message.role}
                  agentName={selectedAgentName}
                  text={message.text}
                  streaming={message.streaming}
                  edited={message.edited}
                  canEdit={canEditThis}
                  editing={editingKey === message.key}
                  onStartEdit={() => setEditingKey(message.key)}
                  onCancelEdit={() => setEditingKey(null)}
                  onSaveEdit={(next) => {
                    if (messageIndex >= 0) void saveEditedMessage(messageIndex, next)
                  }}
                >
                  {(message.tools ?? []).map((tool) => (
                    <ToolCallPopup
                      key={tool.id}
                      tool={tool}
                      onDecision={(decision) => {
                        const agentId = tool.agentId || selectedBlueprint || threadKey
                        if (decision === 'always') rememberAlwaysAllow(agentId, tool.name)
                        sendToolDecision(tool.id, decision)
                        attachToolToThread({
                          ...tool,
                          needsApproval: false,
                          status:
                            decision === 'deny'
                              ? 'denied'
                              : decision === 'always' || decision === 'allow'
                                ? 'allowed'
                                : tool.status,
                        })
                      }}
                    />
                  ))}
                </ChatMessageBubble>
                {SHOW_MESSAGE_ACTIONS && message.role === 'assistant' && !message.streaming && (
                  <ChatMessageActions
                    text={message.text}
                    onRetry={
                      retryEnabled
                        ? () => {
                            sendText(lastUserTextRef.current)
                          }
                        : undefined
                    }
                  />
                )}
              </div>
            )
          })}
          </>
        )}
        <div ref={listEndRef} />
        </div>

        <div
          ref={bottomDockRef}
          className="os-chat-bottom-dock sticky bottom-0 z-20 -mx-2 sm:-mx-3 -mb-3 bg-base-100 border-t border-base-content/5"
          data-testid="chat-bottom-dock"
        >
          {streamingMessage ? (
            <div
              className="os-composer-working"
              data-testid="composer-working-indicator"
              role="status"
              aria-live="polite"
              aria-label={workingTip}
            >
              <span className="tooltip tooltip-top os-composer-working__tip" data-tip={workingTip}>
                <span className="os-composer-working__avatar">
                  <AgentAvatar
                    src={selectedAgent?.avatar_path}
                    agentId={teamFromUrl || agentIdFromBlueprint(selectedBlueprint)}
                    active={true}
                    size="xs"
                    className="shrink-0"
                  />
                </span>
              </span>
            </div>
          ) : null}
          <form onSubmit={handleSend} className="os-composer-wrap">
            <div className="relative" ref={composerWrapRef}>
              <ComposerSlashPopup
                open={isSlashOpen}
                query={slashQuery}
                items={filteredSlashItems}
                selectedIndex={slashSelectedIndex}
                onSelectIndex={setSlashSelectedIndex}
                onSelectItem={handleSelectSlashItem}
                recentIds={recentSlashIds}
              />
              <div className={`os-composer ${replyTarget ? 'os-composer--reply flex-col items-stretch !rounded-2xl !p-2' : ''}`}>
                {replyTarget && (
                  <div
                    className="flex items-center justify-between gap-2 px-2.5 py-1 text-xs text-base-content/70 border-b border-base-content/10 mb-1 w-full"
                    data-testid="composer-reply-strip"
                  >
                    <div className="flex items-center gap-1.5 min-w-0 flex-1">
                      <Reply className="h-3.5 w-3.5 shrink-0 opacity-70" aria-hidden="true" />
                      <span className="truncate" title={replyTarget.text}>
                        {replyTarget.speaker ? (
                          <strong className="font-semibold text-base-content/90 mr-1">
                            {replyTarget.speaker}:
                          </strong>
                        ) : null}
                        <span className="opacity-75">
                          {replyTarget.text.replace(/\s+/g, ' ').slice(0, 100)}
                        </span>
                      </span>
                    </div>
                    <button
                      type="button"
                      className="btn btn-ghost btn-xs btn-circle h-5 w-5 min-h-0 text-base-content/60 hover:text-base-content"
                      aria-label="Dismiss reply"
                      data-testid="dismiss-reply-button"
                      onClick={() => setReplyTarget(null)}
                    >
                      ×
                    </button>
                  </div>
                )}
                <div className={`flex items-center gap-1.5 min-h-0 ${replyTarget ? 'w-full' : 'flex-1'}`}>
                  <div className="relative" ref={plusRef}>
                    <button
                      type="button"
                      className="os-composer__icon"
                      aria-label="Add"
                      aria-haspopup="menu"
                      aria-expanded={plusOpen}
                      onClick={() => setPlusOpen((value) => !value)}
                    >
                      <Plus className="h-4 w-4" aria-hidden="true" />
                    </button>
                    {plusOpen && (
                      <ul
                        role="menu"
                        aria-label="Chat actions"
                        className="os-plus-menu"
                      >
                        <li role="none">
                          <button
                            type="button"
                            role="menuitem"
                            className="os-plus-menu__item"
                            onClick={() => {
                              void handleCompact()
                            }}
                          >
                            <Layers className="h-4 w-4" aria-hidden="true" />
                            Compact
                          </button>
                        </li>
                      </ul>
                    )}
                  </div>
                  <textarea
                    ref={composerRef}
                    rows={1}
                    className="os-composer__input"
                    placeholder={composerPlaceholder}
                    value={input}
                    onChange={handleInputChange}
                    onKeyDown={handleComposerKeyDown}
                    disabled={status !== 'open'}
                    aria-label="Chat message"
                    aria-haspopup="listbox"
                    aria-expanded={isSlashOpen}
                    aria-controls={isSlashOpen ? 'composer-slash-menu' : undefined}
                  />
                  {!input ? (
                    <kbd
                      className="os-composer__hint kbd kbd-xs"
                      data-testid="composer-send-hint"
                      title="Enter to send"
                    >
                      ↵
                    </kbd>
                  ) : (
                    <kbd
                      className="os-composer__hint kbd kbd-xs"
                      data-testid="composer-clear-hint"
                      title="Esc to clear"
                    >
                      Esc
                    </kbd>
                  )}
                  <button
                    type="button"
                    className="os-composer__icon"
                    aria-label="Voice input"
                    onClick={handleMic}
                  >
                    <Mic className="h-4 w-4" aria-hidden="true" />
                  </button>
                  {hasSendableDraft ? (
                    <button
                      type="submit"
                      className="os-composer__send"
                      aria-label="Send"
                    >
                      <ArrowUp className="h-4 w-4" strokeWidth={2.5} aria-hidden="true" />
                    </button>
                  ) : null}
                </div>
              </div>
            </div>
          </form>
        </div>
      </div>

      {contextMenu && (
        <>
          <div
            className="fixed inset-0 z-40"
            data-testid="context-menu-backdrop"
            onClick={() => setContextMenu(null)}
            onContextMenu={(e) => {
              e.preventDefault()
              setContextMenu(null)
            }}
          />
          <div
            role="menu"
            aria-label="Message actions"
            data-testid="message-context-menu"
            className="fixed z-50 min-w-32 rounded-lg border border-base-300 bg-base-100 p-1 shadow-xl text-sm"
            style={{
              left: `${Math.min(contextMenu.x, typeof window !== 'undefined' ? window.innerWidth - 150 : 0)}px`,
              top: `${Math.min(contextMenu.y, typeof window !== 'undefined' ? window.innerHeight - 80 : 0)}px`,
            }}
          >
            <button
              type="button"
              role="menuitem"
              className="flex w-full items-center gap-2 rounded px-3 py-1.5 text-left text-sm hover:bg-base-200 cursor-pointer"
              data-testid="context-menu-reply"
              onClick={() => {
                setReplyTarget({
                  key: contextMenu.message.key,
                  role: contextMenu.message.role,
                  speaker:
                    contextMenu.message.role === 'user' ? 'You' : selectedAgentName,
                  text: contextMenu.message.text,
                })
                setContextMenu(null)
                composerRef.current?.focus()
              }}
            >
              <Reply className="h-4 w-4 opacity-70" aria-hidden="true" />
              Reply
            </button>
          </div>
        </>
      )}

      <TokenDiagnosticsModal
        isOpen={tokenDiagOpen}
        onClose={() => setTokenDiagOpen(false)}
        agentName={selectedAgentName}
        conversationId={conversationId}
        tokenCount={tokenCount}
        inputTokens={inputTokens}
        outputTokens={outputTokens}
        compactsCount={summaries.length}
        toolCallsCount={toolCallsCount}
        messageCount={messages.length}
        userMessageCount={userMessageCount}
        assistantMessageCount={assistantMessageCount}
      />
    </div>
  )
}

function SummaryBlock({
  summary,
  byId,
  depth = 0,
}: {
  summary: ConversationSummary
  byId: Record<number, ConversationSummary>
  depth?: number
}) {
  const parent =
    summary.parent_summary_id != null ? byId[summary.parent_summary_id] : undefined
  const replaced =
    summary.replaced_count ?? summary.span.end - summary.span.start + 1
  return (
    <div
      className={depth > 0 ? 'chat-summary chat-summary--nested' : 'chat-summary'}
      data-testid="chat-summary"
    >
      <div className="chat-summary__label">Summary</div>
      <div className="chat-summary__body whitespace-pre-wrap break-words">{summary.body}</div>
      <div className="chat-summary__meta">Replaced {replaced} turns</div>
      {parent ? <SummaryBlock summary={parent} byId={byId} depth={depth + 1} /> : null}
    </div>
  )
}

export default ChatPage
