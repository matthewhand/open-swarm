import {
  memo,
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
import { Book, Mic, Plus, Settings, Users } from 'lucide-react'
import { LoadingDots, useToast } from '../components/DaisyUI'
import ThemeToggle from '../components/ThemeToggle'
import BrowserControlPane from '../components/BrowserControlPane'
import RuntimeBanner from '../components/RuntimeBanner'
import { OPEN_SETTINGS_EVENT } from '../components/SettingsSheet'
import { fetchBlueprints } from '../lib/api'
import {
  agentIdFromBlueprint,
  conversationIdForAgent,
  fetchAgentThread,
} from '../lib/agentChat'
import {
  buildChatWsFrame,
  buildChatWsUrl,
  parseChatWsMessage,
  type ChatWsEvent,
} from '../lib/chatWs'
import {
  ALL_MEMBERS_TARGET,
  MANAGE_TEAMS_HREF,
  MANAGE_TEAMS_VALUE,
  fetchTeamRosters,
  memberOptionLabel,
  teamThreadId,
} from '../lib/teamRosters'
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
import { renderSafeMarkdown } from '../lib/markdown'
import { isExperimentalEnabled } from '../experimental/flags'
import { ChatMessageActions } from '../experimental/ChatMessageActions'
import { exampleRoleAgents } from '../lib/agentRoles'
import {
  agentLabel,
  defaultBlueprintId,
  SUPPORT_AGENT_ID,
} from '../lib/supportAgent'

/** EXPERIMENTAL flags are read once per module load; see experimental/flags.ts. */
const SHOW_MESSAGE_ACTIONS = isExperimentalEnabled('chat_message_actions')

type ConnectionStatus = 'connecting' | 'open' | 'closed' | 'failed'

interface ChatMessage {
  /** Stable key; for assistant messages this is the server-issued container id. */
  key: string
  role: 'user' | 'assistant'
  text: string
  /** True while the assistant message is still streaming. */
  streaming: boolean
}

const OPERATOR_LINKS = [
  { href: '/blueprint-library/', label: 'Blueprints', icon: Book },
  { href: '/teams/launch/', label: 'Teams', icon: Users },
  { href: '/settings/', label: 'Settings', icon: Settings },
] as const

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
  const { addToast } = useToast()
  const teamFromUrl = searchParams.get('team') ?? ''
  const selectedBlueprint = teamFromUrl
    ? ''
    : defaultBlueprintId(searchParams.get('blueprint'))
  const threadKey = teamFromUrl ? teamThreadId(teamFromUrl) : selectedBlueprint

  const [threads, setThreads] = useState<Record<string, ChatMessage[]>>({})
  const [input, setInput] = useState('')
  const [status, setStatus] = useState<ConnectionStatus>('connecting')
  const [memberTarget, setMemberTarget] = useState(ALL_MEMBERS_TARGET)
  const [connectAttempt, setConnectAttempt] = useState(0)
  const [authRejected, setAuthRejected] = useState(false)
  const [nowMs, setNowMs] = useState(() => Date.now())
  const [plusOpen, setPlusOpen] = useState(false)
  const [conversationId, setConversationId] = useState(() =>
    teamFromUrl
      ? teamThreadId(teamFromUrl)
      : conversationIdForAgent(agentIdFromBlueprint(selectedBlueprint)),
  )

  const messages = useMemo(() => threads[threadKey] ?? [], [threads, threadKey])

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
  const toastedOutageRef = useRef(false)
  const streamStartedAtRef = useRef<number | null>(null)
  const lastUserTextRef = useRef('')
  /** Last hydrated agent or team thread; used to clear bubbles only on switch. */
  const lastHydratedAgentRef = useRef<string | null>(null)

  const blueprintsQuery = useQuery({
    queryKey: ['blueprints'],
    queryFn: fetchBlueprints,
  })
  const teamsQuery = useQuery({
    queryKey: ['team-rosters'],
    queryFn: fetchTeamRosters,
  })
  const blueprints = exampleRoleAgents(blueprintsQuery.data?.data ?? [])
  const teams = teamsQuery.data ?? []
  const selectedTeam = teams.find((team) => team.id === teamFromUrl) ?? null
  const selectedAgent = blueprints.find((bp) => bp.id === selectedBlueprint)
  const selectedAgentName = teamFromUrl
    ? selectedTeam?.name || teamFromUrl
    : selectedAgent
      ? agentLabel(selectedAgent)
      : selectedBlueprint === SUPPORT_AGENT_ID
        ? 'Support'
        : selectedBlueprint
  const signInHref = chatLoginHref(searchParams)

  useEffect(() => {
    if (searchParams.get('team')) return
    if (!searchParams.get('blueprint')) {
      setSearchParams({ blueprint: SUPPORT_AGENT_ID }, { replace: true })
    }
  }, [searchParams, setSearchParams])

  useEffect(() => {
    setMemberTarget(ALL_MEMBERS_TARGET)
  }, [teamFromUrl])

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
      userKeyCounterRef.current = 0
      if (switched) {
        setThreads((prev) => ({ ...prev, [key]: [] }))
      }
      return
    }

    const agent = agentIdFromBlueprint(selectedBlueprint)
    const switched =
      lastHydratedAgentRef.current !== null &&
      lastHydratedAgentRef.current !== agent
    lastHydratedAgentRef.current = agent
    setConversationId(conversationIdForAgent(agent))
    userKeyCounterRef.current = 0
    if (switched) {
      setThreads((prev) => ({ ...prev, [selectedBlueprint]: [] }))
    }
    let cancelled = false
    ;(async () => {
      const thread = await fetchAgentThread(agent)
      if (cancelled) return
      if (thread.messages.length === 0) return
      setThreads((prev) => ({
        ...prev,
        [selectedBlueprint]: thread.messages.map((message, index) => ({
          key: `hist-${index}-${message.role}`,
          role: message.role,
          text: message.content,
          streaming: false,
        })),
      }))
    })()
    return () => {
      cancelled = true
    }
  }, [selectedBlueprint, teamFromUrl])

  const handleWsEvent = useCallback(
    (event: ChatWsEvent) => {
      if (event.kind === 'unknown') {
        console.warn('Unrecognised chat websocket frame:', event.raw)
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
        }
        return { ...prev, [threadKey]: next }
      })
    },
    [threadKey],
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
        buildChatWsUrl(conversationId, teamFromUrl ? undefined : selectedBlueprint || undefined),
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
  }, [connectAttempt, handleWsEvent, conversationId, selectedBlueprint, teamFromUrl])

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
    toastedOutageRef.current = false
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current)
      reconnectTimerRef.current = null
    }
    setConnectAttempt((n) => n + 1)
  }, [])

  useEffect(() => {
    if (status === 'open') {
      toastedOutageRef.current = false
      return
    }
    if (status !== 'failed' && status !== 'closed') return
    if (toastedOutageRef.current) return
    toastedOutageRef.current = true
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
  }, [status, authRejected, signInHref, addToast, reconnect])

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
      ws.send(buildChatWsFrame(trimmed, selectedBlueprint || undefined))
    },
    [selectedBlueprint, teamFromUrl, memberTarget],
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

  const tokenCount = estimateTokensInContext(messages.map((message) => message.text))
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
      <RuntimeBanner />
      <header className="os-chat-header">
        <h1 className="truncate text-base font-semibold tracking-tight">{selectedAgentName}</h1>
        <div className="flex items-center gap-2" aria-label="Chat tools">
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
          <BrowserControlPane />
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
          messages.map((message, idx) => {
            const isLast = idx === messages.length - 1
            const retryEnabled =
              SHOW_MESSAGE_ACTIONS &&
              isLast &&
              message.role === 'assistant' &&
              !message.streaming &&
              lastUserTextRef.current.length > 0
            return (
              <div
                key={message.key}
                className={`chat ${message.role === 'user' ? 'chat-end' : 'chat-start'}`}
              >
                <div className="chat-header text-xs opacity-60">
                  {message.role === 'user' ? 'You' : selectedAgentName}
                </div>
                <div
                  className={`chat-bubble ${
                    message.role === 'user'
                      ? 'bg-neutral text-neutral-content'
                      : 'bg-base-200 text-base-content'
                  }`}
                >
                  <ChatBubbleBody text={message.text} streaming={message.streaming} />
                </div>
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
                aria-label="Operator pages"
                className="os-plus-menu"
              >
                {OPERATOR_LINKS.map((item) => {
                  const Icon = item.icon
                  return (
                    <li key={item.href} role="none">
                      <a
                        role="menuitem"
                        href={item.href}
                        className="os-plus-menu__item"
                        onClick={() => setPlusOpen(false)}
                      >
                        <Icon className="h-4 w-4" aria-hidden="true" />
                        {item.label}
                      </a>
                    </li>
                  )
                })}
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

const ChatBubbleBody = memo(
  function ChatBubbleBody({
    text,
    streaming,
  }: {
    text: string
    streaming: boolean
  }) {
    if (text.length === 0) {
      return streaming ? (
        <LoadingDots size="sm" />
      ) : (
        <span className="opacity-60">(empty response)</span>
      )
    }
    return (
      <div
        data-testid="chat-md"
        className="chat-md break-words [&_p]:my-1 [&_p:first-child]:mt-0 [&_p:last-child]:mb-0 [&_pre]:my-2 [&_pre]:overflow-x-auto [&_pre]:rounded [&_pre]:bg-base-300/40 [&_pre]:p-2 [&_code]:text-sm [&_ul]:my-1 [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:my-1 [&_ol]:list-decimal [&_ol]:pl-5 [&_a]:underline"
        dangerouslySetInnerHTML={{ __html: renderSafeMarkdown(text) }}
      />
    )
  },
  (prev, next) => prev.text === next.text && prev.streaming === next.streaming,
)

export default ChatPage
