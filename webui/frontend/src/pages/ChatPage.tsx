import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
} from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Layers, Mic, PanelLeft, Pencil, Plus, Settings } from 'lucide-react'
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
import { useRailChrome } from '../components/RailChrome'
import { ComputerControlStub } from '../components/ComputerControlStub'
import { RemoteSelect } from '../components/RemoteSelect'
import { ChatMessageBubble } from '../components/ChatMessageBubble'
import { fetchBlueprints, fetchCliAgents, fetchRemotes } from '../lib/api'
import {
  agentIdFromBlueprint,
  compactAgentThread,
  conversationIdForAgent,
  conversationIdForTask,
  fetchAgentThread,
  patchAgentMessage,
  type ConversationSummary,
} from '../lib/agentChat'
import { canEditAgentMessages, classifyAgentKind, type AgentKind } from '../lib/agentKind'
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
import { fetchConfiguredRemotes } from '../lib/remotesCatalog'
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
  formatElapsed,
  formatTokenCount,
} from '../lib/chatMeter'
import { isExperimentalEnabled } from '../experimental/flags'
import { ChatMessageActions } from '../experimental/ChatMessageActions'
import { agentRole, exampleRoleAgents, isChiefOfStaff, isExampleRole } from '../lib/agentRoles'
import { assignedBlueprintId, AGENT_EDITS_CHANGED_EVENT } from '../lib/agentEdits'
import {
  agentLabel,
  defaultBlueprintId,
  isSupportAgent,
  SUPPORT_AGENT_ID,
  supportTurnExtras,
} from '../lib/supportAgent'

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
  const [newChatPerTask, setNewChatPerTask] = useState(() =>
    teamFromUrl || remoteFromUrl ? false : loadLocalNewChatPerTask(defaultBlueprintId(searchParams.get('blueprint'))),
  )

  const [threads, setThreads] = useState<Record<string, ChatMessage[]>>({})
  const [summariesByThread, setSummariesByThread] = useState<
    Record<string, ConversationSummary[]>
  >({})
  const [input, setInput] = useState('')
  const [status, setStatus] = useState<ConnectionStatus>('connecting')
  const [memberTarget, setMemberTarget] = useState(ALL_MEMBERS_TARGET)
  const [connectAttempt, setConnectAttempt] = useState(0)
  const [authRejected, setAuthRejected] = useState(false)
  const [nowMs, setNowMs] = useState(() => Date.now())
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
  const conversationIdRef = useRef(conversationId)
  conversationIdRef.current = conversationId
  const listEndRef = useRef<HTMLDivElement | null>(null)
  const scrollBoxRef = useRef<HTMLDivElement | null>(null)
  const composerRef = useRef<HTMLInputElement | null>(null)
  const plusRef = useRef<HTMLDivElement | null>(null)
  /** Monotonic counter for collision-free user-echo keys. */
  const userKeyCounterRef = useRef(0)
  const prevStatusRef = useRef<ConnectionStatus>('connecting')
  /** Consecutive auto-reconnect attempts since last successful open. */
  const backoffAttemptRef = useRef(0)
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const intentionalCloseRef = useRef(false)
  const streamStartedAtRef = useRef<number | null>(null)
  const lastUserTextRef = useRef('')
  /** Last hydrated agent or team thread; used to clear bubbles only on switch. */
  const lastHydratedAgentRef = useRef<string | null>(null)

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
  const selectedAgentName = teamFromUrl
    ? selectedTeamSession?.name || selectedTeam?.name || teamFromUrl
    : remoteFromUrl
      ? selectedRemoteSession?.name || selectedRemote?.title || remoteFromUrl
      : selectedCli
        ? selectedCli.name
        : selectedAgent
          ? agentLabel(selectedAgent)
          : selectedBlueprint === SUPPORT_AGENT_ID
            ? 'Support'
            : selectedBlueprint
  const signInHref = chatLoginHref(searchParams)

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
    return () => window.removeEventListener(AGENT_EDITS_CHANGED_EVENT, onEdits)
  }, [])

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
      return
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
      return
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
      if (thread.messages.length === 0) return
      setThreads((prev) => ({
        ...prev,
        [threadKey]: thread.messages.map((message, index) => ({
          key: `hist-${index}-${message.role}`,
          role: message.role,
          text: message.content,
          streaming: false,
          edited: message.edited === true,
        })),
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
            next = [
              ...current,
              {
                key: `status-${current.length}-${Date.now()}`,
                role: 'status',
                text: event.text,
                streaming: false,
              },
            ]
            break
        }
        return { ...prev, [threadKey]: next }
      })
      if (event.kind === 'assistant_final') {
        notifyGenerationComplete(teamFromUrl ? teamHideId(teamFromUrl) : selectedBlueprint)
      }
    },
    [attachToolToThread, selectedBlueprint, sendToolDecision, teamFromUrl, threadKey],
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
  useEffect(() => {
    if (pinnedToBottomRef.current) {
      listEndRef.current?.scrollIntoView({ block: 'end' })
    }
  }, [messages])

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

  const canSend = status === 'open' && input.trim().length > 0

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
      const cliParams = selectedCli
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
    sendText(input)
    setInput('')
  }

  const handleComposerKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Escape' && input.length > 0) {
      event.preventDefault()
      setInput('')
    }
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
  useEffect(() => {
    if (!streamingMessage) {
      streamStartedAtRef.current = null
      return
    }
    if (streamStartedAtRef.current == null) {
      streamStartedAtRef.current = Date.now()
    }
    const timer = window.setInterval(() => setNowMs(Date.now()), 1000)
    return () => window.clearInterval(timer)
  }, [streamingMessage])

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

  const tokenCount = estimateTokensInContext(contextTextsForMeter(messages, summaries))
  const tokenPct = Math.min(100, Math.round((tokenCount / CONTEXT_METER_TOKENS) * 100))
  const streamElapsed =
    streamingMessage && streamStartedAtRef.current != null
      ? formatElapsed(nowMs - streamStartedAtRef.current)
      : null

  const composerPlaceholder = status === 'open' ? 'Message …' : 'Message …'

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
        <div className="os-chat-header__identity flex min-w-0 items-center gap-2" data-testid="selected-agent-header">
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
          {!teamFromUrl ? (
            <AgentAvatar
              src={selectedAgent?.avatar_path}
              size="lg"
              className="os-chat-header__avatar"
            />
          ) : null}
          <h1 className="truncate text-base font-semibold tracking-tight">
            <button
              type="button"
              className="os-identity-btn truncate text-left"
              aria-label={`Open ${selectedAgentName} definition`}
              onClick={() => {
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
            <div className="tooltip tooltip-bottom" data-tip="Edit agent">
              <button
                type="button"
                className="btn btn-ghost btn-sm btn-square"
                aria-label="Edit agent"
                onClick={() =>
                  openAgentEditor({
                    agentId: selectedBlueprint,
                  })
                }
              >
                <Pencil className="h-4 w-4" aria-hidden="true" />
              </button>
            </div>
          ) : null}
        </div>
        <div className="flex items-center gap-2">
          <RemoteSelect
            remotes={remotesQuery.data}
            value={selectedRemoteId}
            onChange={setSelectedRemoteId}
            size="sm"
            className="h-8 max-w-[10rem]"
          />
          {teamFromUrl ? (
            <select
              className="select select-sm h-8 max-w-[12rem] border border-base-300 bg-base-100"
              value={memberTarget}
              aria-label="Team members"
              onChange={(e) => {
                const value = e.target.value
                if (value === MANAGE_TEAMS_VALUE) {
                  window.location.assign(MANAGE_TEAMS_HREF)
                  return
                }
                setMemberTarget(value)
              }}
            >
              <option value={ALL_MEMBERS_TARGET}>All members</option>
              {(selectedTeam?.members ?? []).map((member) => (
                <option key={member.id} value={member.id}>
                  {memberOptionLabel(member)}
                </option>
              ))}
              <option value={MANAGE_TEAMS_VALUE}>Manage Teams</option>
            </select>
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
        className="min-h-0 flex-1 space-y-1 overflow-y-auto px-4 py-4 focus:outline focus:outline-2 focus:outline-primary"
        aria-live="polite"
        role="log"
        aria-label="Conversation"
        data-agent-kind={remoteFromUrl ? 'remote' : selectedCli ? 'cli' : agentKind}
        data-messages-editable={messagesEditable && !selectedCli ? 'true' : 'false'}
        tabIndex={0}
        onScroll={(e) => {
          const el = e.currentTarget
          pinnedToBottomRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < 48
        }}
      >
        {messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center gap-2 text-center text-base-content/45">
            <p className="text-sm">Message {selectedAgentName}</p>
          </div>
        ) : (
          displayItems.map((item, idx) => {
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
            if (message.role === 'status') {
              return (
                <p key={message.key} className="os-chat-status" data-role="status">
                  {message.text}
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
              <div key={message.key}>
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
          })
        )}
        <div ref={listEndRef} />
      </div>

      <form onSubmit={handleSend} className="os-composer-wrap">
        <div className="os-composer">
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
          <input
            ref={composerRef}
            type="text"
            className="os-composer__input"
            placeholder={composerPlaceholder}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleComposerKeyDown}
            disabled={status !== 'open'}
            aria-label="Chat message"
          />
          <button
            type="button"
            className="os-composer__icon"
            aria-label="Voice input"
            onClick={handleMic}
          >
            <Mic className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>
        <button type="submit" className="sr-only" disabled={!canSend}>
          Send
        </button>
      </form>

      <footer className="os-chat-footer" aria-live="polite">
        <div
          className="h-1 w-16 overflow-hidden rounded-full bg-base-300"
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
        <span className="tabular-nums whitespace-nowrap">{formatTokenCount(tokenCount)} tok</span>
        {streamingMessage ? (
          <span className="min-w-0 truncate">
            {selectedAgentName} · {streamElapsed ?? '0s'}
          </span>
        ) : null}
      </footer>
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
