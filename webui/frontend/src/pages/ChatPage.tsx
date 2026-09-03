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
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Book, Mic, Plus, Settings, Users } from 'lucide-react'
import { LoadingDots, useToast } from '../components/DaisyUI'
import ThemeToggle from '../components/ThemeToggle'
import { fetchBlueprints } from '../lib/api'
import {
  agentIdFromBlueprint,
  agentThreadQueryKey,
  conversationIdForAgent,
  fetchAgentThread,
  type AgentThread,
} from '../lib/agentChat'
import { chatBubbleClassName, workingLabel } from '../lib/chatBubble'
import {
  AGENT_RENAME_EVENT,
  catalogAgentName,
  saveAgentNameOverride,
} from '../lib/agentNames'
import { decorateConversationRows } from '../lib/chatLog'
import { loadLastRead, saveLastRead } from '../lib/chatLastRead'
import { parseCreatedAtMs } from '../lib/chatTime'
import {
  hopFromAssistantName,
  parseHandoffAssistant,
  type ChatItem,
} from '../lib/interBot'
import { ChatGapLabel, ChatNewRule } from '../components/ChatLogMarkers'
import InterBotLine from '../components/InterBotLine'
import {
  buildChatWsFrame,
  buildChatWsUrl,
  parseChatWsMessage,
  type ChatWsEvent,
} from '../lib/chatWs'
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
import {
  agentLabel,
  defaultBlueprintId,
  SUPPORT_AGENT_ID,
  supportFirstAgents,
} from '../lib/supportAgent'

/** EXPERIMENTAL flags are read once per module load; see experimental/flags.ts. */
const SHOW_MESSAGE_ACTIONS = isExperimentalEnabled('chat_message_actions')

type ConnectionStatus = 'connecting' | 'open' | 'closed' | 'failed'

type ChatMessage = Extract<ChatItem, { type: 'message' }>

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
export {
  CHAT_BUBBLE_COMPLETE,
  CHAT_BUBBLE_STREAMING,
  chatBubbleClassName,
  workingLabel,
} from '../lib/chatBubble'

const ChatPage = () => {
  const [searchParams, setSearchParams] = useSearchParams()
  const { addToast } = useToast()
  const selectedBlueprint = defaultBlueprintId(searchParams.get('blueprint'))

  const queryClient = useQueryClient()
  const [threads, setThreads] = useState<Record<string, ChatItem[]>>({})
  const [input, setInput] = useState('')
  const [status, setStatus] = useState<ConnectionStatus>('connecting')
  const [connectAttempt, setConnectAttempt] = useState(0)
  const [authRejected, setAuthRejected] = useState(false)
  const [nowMs, setNowMs] = useState(() => Date.now())
  const [plusOpen, setPlusOpen] = useState(false)
  const [conversationId, setConversationId] = useState(() =>
    conversationIdForAgent(agentIdFromBlueprint(selectedBlueprint)),
  )

  const threadItems = useMemo(
    () => threads[selectedBlueprint] ?? [],
    [threads, selectedBlueprint],
  )
  const messages = useMemo(
    () => threadItems.filter((item): item is ChatMessage => item.type === 'message'),
    [threadItems],
  )
  const sessionReadCount = useMemo(
    () => loadLastRead(agentIdFromBlueprint(selectedBlueprint), conversationId)?.messageCount ?? null,
    [conversationId, selectedBlueprint],
  )
  const conversationRows = useMemo(
    () =>
      decorateConversationRows(threadItems, {
        lastReadMessageCount: sessionReadCount,
        nowMs,
      }),
    [nowMs, sessionReadCount, threadItems],
  )

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
  /** Last hydrated agent; used to clear bubbles only when the user switches. */
  const lastHydratedAgentRef = useRef<string | null>(null)

  const blueprintsQuery = useQuery({
    queryKey: ['blueprints'],
    queryFn: fetchBlueprints,
  })
  const blueprints = supportFirstAgents(blueprintsQuery.data?.data ?? [])
  const selectedAgent = blueprints.find((bp) => bp.id === selectedBlueprint)
  const catalogName = selectedAgent
    ? catalogAgentName(selectedAgent)
    : selectedBlueprint === SUPPORT_AGENT_ID
      ? 'Support'
      : selectedBlueprint
  const [nameTick, setNameTick] = useState(0)
  const selectedAgentName = useMemo(() => {
    return selectedAgent ? agentLabel(selectedAgent) : agentLabel({ id: selectedBlueprint, name: catalogName })
  }, [catalogName, nameTick, selectedAgent, selectedBlueprint])
  const [nameDraft, setNameDraft] = useState(selectedAgentName)
  const skipNameCommitRef = useRef(false)
  const signInHref = chatLoginHref(searchParams)

  useEffect(() => {
    setNameDraft(selectedAgentName)
  }, [selectedAgentName])

  useEffect(() => {
    const onRename = () => setNameTick((n) => n + 1)
    window.addEventListener(AGENT_RENAME_EVENT, onRename)
    return () => window.removeEventListener(AGENT_RENAME_EVENT, onRename)
  }, [])

  const commitAgentName = useCallback(() => {
    const next = saveAgentNameOverride(selectedBlueprint, nameDraft, catalogName)
    setNameDraft(next)
    setNameTick((n) => n + 1)
  }, [catalogName, nameDraft, selectedBlueprint])

  useEffect(() => {
    if (!searchParams.get('blueprint')) {
      setSearchParams({ blueprint: SUPPORT_AGENT_ID }, { replace: true })
    }
  }, [searchParams, setSearchParams])

  // Per-agent thread: stable conversation id + hydrate from disk/DB.
  // No history chrome — messages just come back after reload / agent switch.
  useEffect(() => {
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
        [selectedBlueprint]: thread.messages.map((message, index) => {
          const handoff = parseHandoffAssistant(message.content)
          if (handoff) {
            const key = `hist-hop-${index}`
            return { type: 'hop' as const, key, hop: hopFromAssistantName(key, handoff, false) }
          }
          return {
            type: 'message' as const,
            key: `hist-${index}-${message.role}`,
            role: message.role,
            text: message.content,
            streaming: false,
            createdAtMs: parseCreatedAtMs(message.ts),
          }
        }),
      }))
    })()
    return () => {
      cancelled = true
    }
  }, [selectedBlueprint])

  useEffect(() => {
    if (messages.length === 0) return
    saveLastRead(agentIdFromBlueprint(selectedBlueprint), conversationId, messages.length)
  }, [conversationId, messages.length, selectedBlueprint])

  const rememberThreadLine = useCallback(
    (role: 'user' | 'assistant', content: string) => {
      const agent = agentIdFromBlueprint(selectedBlueprint)
      queryClient.setQueryData<AgentThread>(agentThreadQueryKey(agent), (prev) => ({
        agent_id: prev?.agent_id ?? agent,
        conversation_id: prev?.conversation_id ?? conversationIdForAgent(agent),
        messages: [...(prev?.messages ?? []), { role, content }],
      }))
      void queryClient.invalidateQueries({ queryKey: agentThreadQueryKey(agent) })
    },
    [queryClient, selectedBlueprint],
  )

  const handleWsEvent = useCallback(
    (event: ChatWsEvent) => {
      if (event.kind === 'unknown') {
        console.warn('Unrecognised chat websocket frame:', event.raw)
        return
      }
      setThreads((prev) => {
        const current = prev[selectedBlueprint] ?? []
        let next = current
        switch (event.kind) {
          case 'user_echo':
            userKeyCounterRef.current += 1
            next = [
              ...current,
              {
                type: 'message',
                key: `user-${userKeyCounterRef.current}-${Date.now()}`,
                role: 'user',
                text: event.text,
                streaming: false,
                createdAtMs: Date.now(),
              },
            ]
            break
          case 'assistant_start':
            if (current.some((item) => item.key === event.id)) return prev
            next = [
              ...current,
              {
                type: 'message',
                key: event.id,
                role: 'assistant',
                text: '',
                streaming: true,
                createdAtMs: Date.now(),
              },
            ]
            break
          case 'assistant_chunk':
            next = current.map((item) =>
              item.type === 'message' && item.key === event.id
                ? { ...item, text: item.text + event.text }
                : item,
            )
            break
          case 'assistant_final': {
            const handoff = parseHandoffAssistant(event.text)
            if (handoff) {
              next = current.filter((item) => item.key !== event.id)
              next = [
                ...next,
                { type: 'hop', key: event.id, hop: hopFromAssistantName(event.id, handoff, false) },
              ]
              break
            }
            next = current.map((item) =>
              item.type === 'message' && item.key === event.id
                ? { ...item, text: event.text, streaming: false }
                : item,
            )
            break
          }
          case 'interbot_hop': {
            const hop = hopFromAssistantName(event.id, event.name, event.pending, event.agentId)
            const existing = current.findIndex((item) => item.key === event.id || (item.type === 'hop' && item.hop.id === event.id))
            if (existing >= 0) {
              next = current.map((item, index) =>
                index === existing ? { type: 'hop', key: event.id, hop } : item,
              )
            } else {
              next = [...current, { type: 'hop', key: event.id, hop }]
            }
            break
          }
        }
        return { ...prev, [selectedBlueprint]: next }
      })
      if (event.kind === 'user_echo') rememberThreadLine('user', event.text)
      if (event.kind === 'assistant_final' && !parseHandoffAssistant(event.text)) {
        rememberThreadLine('assistant', event.text)
      }
    },
    [rememberThreadLine, selectedBlueprint],
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
      ws = new WebSocket(buildChatWsUrl(conversationId, selectedBlueprint || undefined))
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
  }, [connectAttempt, handleWsEvent, conversationId, selectedBlueprint])

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
      ws.send(buildChatWsFrame(trimmed, selectedBlueprint || undefined))
    },
    [selectedBlueprint],
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
      <header className="os-chat-header">
        <h1 className="os-chat-header__start min-w-0">
          <label className="sr-only" htmlFor="os-agent-name">
            Agent name
          </label>
          <input
            id="os-agent-name"
            className="os-chat-title"
            value={nameDraft}
            spellCheck={false}
            onChange={(event) => setNameDraft(event.target.value)}
            onBlur={() => {
              if (skipNameCommitRef.current) {
                skipNameCommitRef.current = false
                return
              }
              commitAgentName()
            }}
            onKeyDown={(event) => {
              if (event.key === 'Enter') {
                event.preventDefault()
                event.currentTarget.blur()
              }
              if (event.key === 'Escape') {
                event.preventDefault()
                skipNameCommitRef.current = true
                setNameDraft(selectedAgentName)
                event.currentTarget.blur()
              }
            }}
          />
        </h1>
        <div className="os-chat-header__center">
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
        </div>
        <div className="os-chat-header__end">
          <ThemeToggle />
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
        {conversationRows.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center gap-2 text-center text-base-content/45">
            <p className="text-sm">Message {selectedAgentName}</p>
          </div>
        ) : (
          conversationRows.map((row, idx) => {
            if (row.type === 'hop-line') {
              return <InterBotLine key={`hop-${idx}-${row.line.kind}`} line={row.line} />
            }
            if (row.type === 'gap') {
              return <ChatGapLabel key={row.key} label={row.label} />
            }
            if (row.type === 'new') {
              return <ChatNewRule key={row.key} />
            }
            const message = row.message
            const isLast = idx === conversationRows.length - 1
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
                  className={chatBubbleClassName(message.role, message.streaming)}
                  data-streaming={message.streaming ? 'true' : 'false'}
                >
                  <ChatBubbleBody
                    text={message.text}
                    streaming={message.streaming}
                    agentName={selectedAgentName}
                  />
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

      {streamingMessage ? (
        <footer className="os-chat-footer" aria-live="polite">
          <span className="min-w-0 truncate">
            {selectedAgentName} · {streamElapsed ?? '0s'}
          </span>
        </footer>
      ) : null}
    </div>
  )
}

const ChatBubbleBody = memo(
  function ChatBubbleBody({
    text,
    streaming,
    agentName,
  }: {
    text: string
    streaming: boolean
    agentName: string
  }) {
    const dots = streaming ? (
      <span title={workingLabel(agentName)}>
        <LoadingDots size="sm" aria-label={workingLabel(agentName)} />
      </span>
    ) : null
    if (text.length === 0) {
      return streaming ? dots : <span className="opacity-60">(empty response)</span>
    }
    return (
      <>
        <div
          data-testid="chat-md"
          className="chat-md break-words [&_p]:my-1 [&_p:first-child]:mt-0 [&_p:last-child]:mb-0 [&_pre]:my-2 [&_pre]:overflow-x-auto [&_pre]:rounded [&_pre]:bg-base-300/40 [&_pre]:p-2 [&_code]:text-sm [&_ul]:my-1 [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:my-1 [&_ol]:list-decimal [&_ol]:pl-5 [&_a]:underline"
          dangerouslySetInnerHTML={{ __html: renderSafeMarkdown(text) }}
        />
        {dots}
      </>
    )
  },
  (prev, next) =>
    prev.text === next.text && prev.streaming === next.streaming && prev.agentName === next.agentName,
)

export default ChatPage
