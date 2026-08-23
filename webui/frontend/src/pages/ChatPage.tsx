import {
  memo,
  useCallback,
  useEffect,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
} from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { AlertCircle, Info, LogIn, MessageSquare, RefreshCw, Send } from 'lucide-react'
import {
  Alert,
  Badge,
  Button,
  LoadingDots,
  LoadingSpinner,
} from '../components/DaisyUI'
import { fetchBlueprints, isAuthError } from '../lib/api'
import {
  buildChatWsFrame,
  buildChatWsUrl,
  newConversationId,
  parseChatWsMessage,
  type ChatWsEvent,
} from '../lib/chatWs'
import {
  reconnectBackoffMs,
  shouldAutoReconnect,
  WS_AUTH_REQUIRED_CODE,
} from '../lib/chatReconnect'
import { renderSafeMarkdown } from '../lib/markdown'
import { isExperimentalEnabled } from '../experimental/flags'
import { ChatMessageActions } from '../experimental/ChatMessageActions'

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

/** Starter prompts shown on the empty chat to give users a way in. */
const SUGGESTED_PROMPTS = [
  'Summarize this repository’s architecture',
  'Write unit tests for a Python function',
  'Plan a multi-step refactor and list the risks',
  'Explain how MCP servers extend an agent',
]

/** Post-login return path for the Django session gate (rooted, same-origin). */
export function chatLoginNext(searchParams: URLSearchParams): string {
  const qs = searchParams.toString()
  return qs ? `/chat?${qs}` : '/chat'
}

export function chatLoginHref(searchParams: URLSearchParams): string {
  return `/accounts/login/?next=${encodeURIComponent(chatLoginNext(searchParams))}`
}

const ChatPage = () => {
  // Teams/Blueprints pages link here as /chat?blueprint=<id> to preselect.
  const [searchParams] = useSearchParams()
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [status, setStatus] = useState<ConnectionStatus>('connecting')
  const [selectedBlueprint, setSelectedBlueprint] = useState(
    () => searchParams.get('blueprint') ?? '',
  )
  const [connectAttempt, setConnectAttempt] = useState(0)
  /** True when the server closed with WS_AUTH_REQUIRED_CODE (no Django session). */
  const [authRejected, setAuthRejected] = useState(false)

  const wsRef = useRef<WebSocket | null>(null)
  const conversationIdRef = useRef(newConversationId())
  const listEndRef = useRef<HTMLDivElement | null>(null)
  const scrollBoxRef = useRef<HTMLDivElement | null>(null)
  const composerRef = useRef<HTMLInputElement | null>(null)
  /** Monotonic counter for collision-free user-echo keys. */
  const userKeyCounterRef = useRef(0)
  const prevStatusRef = useRef<ConnectionStatus>('connecting')
  /** Consecutive auto-reconnect attempts since last successful open. */
  const backoffAttemptRef = useRef(0)
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const intentionalCloseRef = useRef(false)

  const blueprintsQuery = useQuery({
    queryKey: ['blueprints'],
    queryFn: fetchBlueprints,
  })
  const blueprints = blueprintsQuery.data?.data ?? []
  const blueprintMissingFromList =
    Boolean(selectedBlueprint) &&
    !blueprintsQuery.isPending &&
    !blueprintsQuery.isError &&
    !blueprints.some((bp) => bp.id === selectedBlueprint)
  const signInHref = chatLoginHref(searchParams)

  const handleWsEvent = useCallback((event: ChatWsEvent) => {
    if (event.kind === 'unknown') {
      // Frame we don't recognise; log for debugging but never fabricate UI.
      console.warn('Unrecognised chat websocket frame:', event.raw)
      return
    }
    setMessages((prev) => {
      switch (event.kind) {
        case 'user_echo':
          userKeyCounterRef.current += 1
          return [
            ...prev,
            {
              key: `user-${userKeyCounterRef.current}-${Date.now()}`,
              role: 'user',
              text: event.text,
              streaming: false,
            },
          ]
        case 'assistant_start':
          // Server may re-announce an id; keep keys unique.
          if (prev.some((m) => m.key === event.id)) return prev
          return [
            ...prev,
            { key: event.id, role: 'assistant', text: '', streaming: true },
          ]
        case 'assistant_chunk':
          return prev.map((m) =>
            m.key === event.id ? { ...m, text: m.text + event.text } : m,
          )
        case 'assistant_final':
          return prev.map((m) =>
            m.key === event.id
              ? { ...m, text: event.text, streaming: false }
              : m,
          )
      }
    })
  }, [])

  // Connect (and reconnect on demand) to the chat websocket.
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
      ws = new WebSocket(buildChatWsUrl(conversationIdRef.current))
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
      // Auth gate: consumer accept-then-closes with 4401 (session cookie missing).
      // Never-opened failures are usually ASGI/network/origin — not "use API token".
      const rejected = event.code === WS_AUTH_REQUIRED_CODE
      setAuthRejected(rejected)
      setStatus(opened ? 'closed' : 'failed')

      const attempt = backoffAttemptRef.current
      if (
        shouldAutoReconnect(
          event.code,
          intentionalCloseRef.current,
          attempt,
        )
      ) {
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
  }, [connectAttempt, handleWsEvent])

  // Keep the latest message in view while streaming, but only while the user
  // is already at (or near) the bottom — never yank a reader who scrolled up.
  const pinnedToBottomRef = useRef(true)
  useEffect(() => {
    if (pinnedToBottomRef.current) {
      listEndRef.current?.scrollIntoView({ block: 'end' })
    }
  }, [messages])

  // After a user-initiated reconnect succeeds, move focus to the composer so
  // keyboard users can type immediately (skip initial page-load connect).
  useEffect(() => {
    const wasOpen = prevStatusRef.current === 'open'
    prevStatusRef.current = status
    if (status === 'open' && !wasOpen && connectAttempt > 0) {
      composerRef.current?.focus()
    }
  }, [status, connectAttempt])

  const canSend =
    status === 'open' && input.trim().length > 0

  /** Last user prompt, kept for the experimental Retry action. */
  const lastUserTextRef = useRef('')

  const sendText = useCallback(
    (text: string) => {
      const ws = wsRef.current
      const trimmed = text.trim()
      if (!trimmed || !ws || ws.readyState !== WebSocket.OPEN) return
      lastUserTextRef.current = trimmed
      // Protocol from DjangoChatConsumer.receive():
      // {"message": "<text>", "blueprint": "<id>"} — the blueprint field is
      // optional and selects which blueprint generates the reply.
      ws.send(buildChatWsFrame(trimmed, selectedBlueprint || undefined))
    },
    [selectedBlueprint],
  )

  const handleSend = (event: FormEvent) => {
    event.preventDefault()
    sendText(input)
    setInput('')
  }

  const reconnect = () => {
    backoffAttemptRef.current = 0
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current)
      reconnectTimerRef.current = null
    }
    setConnectAttempt((n) => n + 1)
  }

  const handleComposerKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Escape' && input.length > 0) {
      event.preventDefault()
      setInput('')
    }
  }

  const composerPlaceholder =
    status === 'open'
      ? 'Type a message…'
      : status === 'connecting'
        ? 'Connecting… sending is disabled'
        : 'Websocket not connected — sending is disabled'

  return (
    <div className="container mx-auto flex h-[calc(100vh-13rem)] lg:h-[calc(100vh-9rem)] min-h-[28rem] flex-col gap-4 px-4 py-6">
      {/* Header: title + blueprint selector + connection status.
          Stacks vertically below lg; single row on desktop. */}
      <div className="flex flex-col gap-3 lg:flex-row lg:flex-wrap lg:items-end lg:justify-between lg:gap-x-6">
        <h1 className="text-3xl font-bold flex items-center gap-2">
          <MessageSquare className="h-8 w-8" />
          Chat
        </h1>

        {/* Blueprint selector (from /v1/blueprints/) */}
        <div className="flex flex-wrap items-end gap-4 lg:flex-1 lg:justify-end">
          {blueprintsQuery.isPending ? (
            <div className="flex items-center gap-2 py-2">
              <LoadingSpinner size="sm" />
              <span className="text-sm">Loading blueprints…</span>
            </div>
          ) : blueprintsQuery.isError ? (
            <Alert
              type="warning"
              icon={<AlertCircle className="h-5 w-5" />}
              className="max-w-md py-2"
            >
              <span className="text-sm">
                Could not load blueprints
                {isAuthError(blueprintsQuery.error) ? (
                  <>
                    {' '}
                    (authentication failed —{' '}
                    <a href={signInHref} className="link">
                      sign in
                    </a>{' '}
                    for a Django session, or send{' '}
                    <code>Authorization: Bearer</code> for REST)
                  </>
                ) : (
                  ` (${blueprintsQuery.error.message})`
                )}
                .
              </span>
            </Alert>
          ) : (
            <div className="w-full max-w-xs flex flex-col gap-1">
              <div className="mb-1 flex items-center gap-1.5">
                <span className="text-sm font-medium">
                  Blueprint
                </span>
                {/* Focusable so keyboard users can reveal the tooltip;
                    aria-describedby keeps the note available to screen readers. */}
                <span
                  className="tooltip tooltip-bottom before:max-w-[18rem] before:whitespace-normal"
                  data-tip="Sent with every message — the selected blueprint generates the reply. Choose “Server default model” to use the server-configured model instead."
                >
                  <button
                    type="button"
                    className="btn btn-ghost btn-xs btn-circle p-0 min-h-0 h-auto"
                    aria-label="About blueprint selection"
                    tabIndex={0}
                  >
                    <Info className="h-3.5 w-3.5 opacity-60" aria-hidden="true" />
                  </button>
                </span>
              </div>
              <select
                className="select select-sm w-full border border-base-300"
                value={selectedBlueprint}
                onChange={(e) => setSelectedBlueprint(e.target.value)}
                aria-label="Blueprint"
              >
                <option value="">Server default model</option>
                {/* Keep a ?blueprint= preselection visible even if it is not
                    in the fetched list (e.g. a just-created team). */}
                {blueprintMissingFromList && (
                  <option value={selectedBlueprint}>
                    {selectedBlueprint} (not in list)
                  </option>
                )}
                {blueprints.map((bp) => (
                  <option key={bp.id} value={bp.id}>
                    {bp.name || bp.id}
                  </option>
                ))}
              </select>
            </div>
          )}
          <div className="pb-1">
            <ConnectionBadge status={status} authRejected={authRejected} />
          </div>
        </div>
      </div>

      {blueprintMissingFromList && (
        <Alert
          type="warning"
          icon={<AlertCircle className="h-5 w-5" />}
          className="shrink-0"
        >
          <div className="space-y-1 text-sm">
            <span className="font-medium">
              Blueprint <code>{selectedBlueprint}</code> from the URL is not in
              the discoverable list.
            </span>
            <p>
              It stays selected so chat can still request it (for example a
              just-launched team). If the server does not recognise the id, the
              reply errors — it does not fall back to the default model.
            </p>
          </div>
        </Alert>
      )}

      {/* Fallback when the websocket is unavailable.
          shrink-0: fixed-height flex column otherwise collapses this CTA. */}
      {(status === 'failed' || status === 'closed') && (
        <Alert
          type="error"
          icon={<AlertCircle className="h-5 w-5" />}
          className="shrink-0"
        >
          <div className="space-y-2">
            <span className="font-medium">
              {authRejected
                ? 'Websocket unavailable — sign in required.'
                : status === 'failed'
                  ? 'Websocket unavailable.'
                  : 'Websocket connection closed.'}
            </span>
            <p className="text-sm">
              {authRejected ? (
                <>
                  Live chat authenticates with a Django{' '}
                  <strong>session cookie</strong> (form login), not a REST
                  API bearer token. Sign in, then reconnect. Message history
                  above is kept when present.
                </>
              ) : (
                <>
                  Live chat runs over the backend websocket (served by{' '}
                  <code>manage.py runserver</code>, daphne or any ASGI server
                  via <code>swarm.asgi:application</code>). If you are already
                  signed in, check that ASGI is serving <code>/ws/</code> and
                  your Origin matches <code>ALLOWED_HOSTS</code>, then
                  reconnect. Message history above is kept when present.
                </>
              )}
            </p>
            <div className="flex flex-wrap gap-2">
              <a href={signInHref} className="btn btn-sm btn-primary">
                <LogIn className="h-4 w-4 mr-1" aria-hidden="true" />
                Sign in
              </a>
              <Button size="sm" variant="ghost" onClick={reconnect}>
                <RefreshCw className="h-4 w-4 mr-1" aria-hidden="true" />
                Reconnect
              </Button>
            </div>
          </div>
        </Alert>
      )}

      {/* Conversation: scrollable message list + composer pinned at bottom */}
      <div className="card flex min-h-0 flex-1 flex-col overflow-hidden border border-base-300 bg-base-100">
        <div
          ref={scrollBoxRef}
          className="min-h-0 flex-1 space-y-1 overflow-y-auto p-4 focus:outline focus:outline-2 focus:outline-primary"
          aria-live="polite"
          role="log"
          aria-label="Conversation"
          tabIndex={0}
          onScroll={(e) => {
            const el = e.currentTarget
            // Within 48px of the bottom counts as "following" the stream.
            pinnedToBottomRef.current =
              el.scrollHeight - el.scrollTop - el.clientHeight < 48
          }}
        >
          {messages.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center gap-3 text-center">
              <MessageSquare className="h-10 w-10 opacity-20" aria-hidden="true" />
              <div>
                <p className="font-medium text-base-content/70">
                  {status === 'open'
                    ? 'Connected and ready'
                    : status === 'connecting'
                      ? 'Connecting to the chat websocket…'
                      : 'Websocket not connected'}
                </p>
                <p className="text-sm text-base-content/70">
                  {status === 'open'
                    ? 'Send a message below, or try one of these:'
                    : status === 'connecting'
                      ? 'Hang tight — this usually takes a moment.'
                      : authRejected
                        ? 'Sign in with a Django session, then reconnect.'
                        : 'Sign in if needed, confirm ASGI is up, then reconnect.'}
                </p>
              </div>
              {status === 'open' && (
                <div className="flex flex-wrap justify-center gap-2 mt-1 max-w-xl">
                  {SUGGESTED_PROMPTS.map((prompt) => (
                    <button
                      key={prompt}
                      type="button"
                      onClick={() => setInput(prompt)}
                      className="btn btn-sm btn-outline rounded-full normal-case font-normal"
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              )}
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
                    {message.role === 'user' ? 'You' : 'Assistant'}
                  </div>
                  <div
                    className={`chat-bubble ${
                      message.role === 'user' ? 'chat-bubble-primary' : ''
                    }`}
                  >
                    <ChatBubbleBody
                      text={message.text}
                      streaming={message.streaming}
                    />
                  </div>
                  {SHOW_MESSAGE_ACTIONS &&
                    message.role === 'assistant' &&
                    !message.streaming && (
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

        {/* Composer */}
        <form
          onSubmit={handleSend}
          className="flex gap-2 border-t border-base-300 p-3"
        >
          <input
            ref={composerRef}
            type="text"
            className="input input-sm h-10 flex-1"
            placeholder={composerPlaceholder}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleComposerKeyDown}
            disabled={status !== 'open'}
            aria-label="Chat message"
          />
          <Button type="submit" variant="primary" disabled={!canSend}>
            <Send className="h-4 w-4 mr-1" aria-hidden="true" />
            Send
          </Button>
        </form>
      </div>
    </div>
  )
}

/** Memoized bubble body: avoids re-running markdown + sanitize for every
 * already-final message on each streamed chunk. */
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
        className="chat-md break-words [&_p]:my-1 [&_p:first-child]:mt-0 [&_p:last-child]:mb-0 [&_pre]:my-2 [&_pre]:overflow-x-auto [&_pre]:rounded [&_pre]:bg-base-300/40 [&_pre]:p-2 [&_code]:text-sm [&_ul]:my-1 [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:my-1 [&_ol]:list-decimal [&_ol]:pl-5 [&_a]:underline"
        dangerouslySetInnerHTML={{ __html: renderSafeMarkdown(text) }}
      />
    )
  },
  (prev, next) =>
    prev.text === next.text && prev.streaming === next.streaming,
)

function connectionStatusLabel(
  status: ConnectionStatus,
  authRejected: boolean,
): string {
  switch (status) {
    case 'connecting':
      return 'Connecting…'
    case 'open':
      return 'Connected'
    case 'closed':
      return authRejected
        ? 'Unavailable — sign in required'
        : 'Disconnected'
    case 'failed':
      return authRejected
        ? 'Unavailable — sign in required'
        : 'Unavailable — websocket unreachable'
  }
}

function ConnectionBadge({
  status,
  authRejected,
}: {
  status: ConnectionStatus
  authRejected: boolean
}) {
  const label = connectionStatusLabel(status, authRejected)
  return (
    <span
      role="status"
      aria-live="polite"
      aria-atomic="true"
      aria-label="Connection status"
    >
      {status === 'connecting' ? (
        <Badge type="warning">
          <LoadingSpinner size="xs" className="mr-1" />
          {label}
        </Badge>
      ) : status === 'open' ? (
        <Badge type="success">{label}</Badge>
      ) : (
        <Badge type="error">{label}</Badge>
      )}
    </span>
  )
}

export default ChatPage
