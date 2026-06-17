import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { AlertCircle, Info, MessageSquare, RefreshCw, Send } from 'lucide-react'
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

type ConnectionStatus = 'connecting' | 'open' | 'closed' | 'failed'

interface ChatMessage {
  /** Stable key; for assistant messages this is the server-issued container id. */
  key: string
  role: 'user' | 'assistant'
  text: string
  /** True while the assistant message is still streaming. */
  streaming: boolean
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

  const wsRef = useRef<WebSocket | null>(null)
  const conversationIdRef = useRef(newConversationId())
  const listEndRef = useRef<HTMLDivElement | null>(null)

  const blueprintsQuery = useQuery({
    queryKey: ['blueprints'],
    queryFn: fetchBlueprints,
  })
  const blueprints = blueprintsQuery.data?.data ?? []

  const handleWsEvent = useCallback((event: ChatWsEvent) => {
    if (event.kind === 'unknown') {
      // Frame we don't recognise; log for debugging but never fabricate UI.
      console.warn('Unrecognised chat websocket frame:', event.raw)
      return
    }
    setMessages((prev) => {
      switch (event.kind) {
        case 'user_echo':
          return [
            ...prev,
            {
              key: `user-${prev.length}-${Date.now()}`,
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
    setStatus('connecting')

    let ws: WebSocket
    try {
      ws = new WebSocket(buildChatWsUrl(conversationIdRef.current))
    } catch {
      setStatus('failed')
      return
    }
    wsRef.current = ws

    ws.onopen = () => {
      opened = true
      setStatus('open')
    }
    ws.onmessage = (event: MessageEvent) => {
      if (typeof event.data === 'string') {
        handleWsEvent(parseChatWsMessage(event.data))
      }
    }
    ws.onclose = () => {
      if (wsRef.current === ws) wsRef.current = null
      setStatus(opened ? 'closed' : 'failed')
    }

    return () => {
      ws.onopen = null
      ws.onmessage = null
      ws.onclose = null
      ws.close()
      if (wsRef.current === ws) wsRef.current = null
    }
  }, [connectAttempt, handleWsEvent])

  // Keep the latest message in view while streaming.
  useEffect(() => {
    listEndRef.current?.scrollIntoView({ block: 'end' })
  }, [messages])

  const canSend =
    status === 'open' && input.trim().length > 0

  const handleSend = (event: FormEvent) => {
    event.preventDefault()
    const text = input.trim()
    const ws = wsRef.current
    if (!text || !ws || ws.readyState !== WebSocket.OPEN) return
    // Protocol from DjangoChatConsumer.receive():
    // {"message": "<text>", "blueprint": "<id>"} — the blueprint field is
    // optional and selects which blueprint generates the reply.
    ws.send(buildChatWsFrame(text, selectedBlueprint || undefined))
    setInput('')
  }

  const reconnect = () => setConnectAttempt((n) => n + 1)

  const isStreaming = messages.some((m) => m.streaming)

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
                    <Link to="/settings" className="link">
                      set an API token
                    </Link>
                    )
                  </>
                ) : (
                  ` (${blueprintsQuery.error.message})`
                )}
                .
              </span>
            </Alert>
          ) : (
            <label className="form-control w-full max-w-xs">
              <div className="mb-1 flex items-center gap-1.5">
                <span className="label-text text-sm font-medium">
                  Blueprint
                </span>
                <span
                  className="tooltip tooltip-bottom before:max-w-[18rem] before:whitespace-normal"
                  data-tip="Sent with every message — the selected blueprint generates the reply. Choose “Server default model” to use the server-configured model instead."
                >
                  <Info
                    className="h-3.5 w-3.5 opacity-60"
                    aria-label="Blueprint selection note"
                  />
                </span>
              </div>
              <select
                className="select select-bordered select-sm w-full border border-base-300"
                value={selectedBlueprint}
                onChange={(e) => setSelectedBlueprint(e.target.value)}
                aria-label="Blueprint"
              >
                <option value="">Server default model</option>
                {/* Keep a ?blueprint= preselection visible even if it is not
                    in the fetched list (e.g. a just-created team). */}
                {selectedBlueprint &&
                  !blueprints.some((bp) => bp.id === selectedBlueprint) && (
                    <option value={selectedBlueprint}>
                      {selectedBlueprint}
                    </option>
                  )}
                {blueprints.map((bp) => (
                  <option key={bp.id} value={bp.id}>
                    {bp.name || bp.id}
                  </option>
                ))}
              </select>
            </label>
          )}
          <div className="pb-1">
            <ConnectionBadge status={status} />
          </div>
        </div>
      </div>

      {/* Fallback when the websocket is unavailable */}
      {(status === 'failed' || status === 'closed') && (
        <Alert type="error" icon={<AlertCircle className="h-5 w-5" />}>
          <div className="space-y-1" role="alert" aria-live="assertive">
            <span className="font-medium">
              {status === 'failed'
                ? 'Websocket connection failed.'
                : 'Websocket connection closed.'}
            </span>
            <p className="text-sm">
              Live chat runs over the backend websocket (served by{' '}
              <code>manage.py runserver</code>, daphne or any ASGI server via{' '}
              <code>swarm.asgi:application</code>), and the chat consumer only
              accepts authenticated Django sessions. Your message history
              above is kept; reconnect when the server is available.
            </p>
            <Button size="sm" variant="ghost" onClick={reconnect} aria-label="Reconnect to chat server">
              <RefreshCw className="h-4 w-4 mr-1" />
              Reconnect
            </Button>
          </div>
        </Alert>
      )}

      {/* Conversation: scrollable message list + composer pinned at bottom */}
      <div className="card flex min-h-0 flex-1 flex-col overflow-hidden border border-base-300 bg-base-100">
        <div
          className="min-h-0 flex-1 space-y-1 overflow-y-auto p-4 focus:outline focus:outline-2 focus:outline-primary"
          aria-live="polite"
          role="log"
          aria-label="Conversation"
          tabIndex={0}
        >
          {messages.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center gap-3 text-center" aria-live="polite" aria-busy={status === 'connecting'}>
              {status === 'connecting' ? (
                <LoadingSpinner size="lg" aria-label="Connecting to chat" />
              ) : (
                <MessageSquare className="h-10 w-10 opacity-20" />
              )}
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
                    ? 'Send a message below to start the conversation.'
                    : status === 'connecting'
                      ? 'Hang tight — this usually takes a moment.'
                      : 'No messages yet — reconnect to start chatting.'}
                </p>
              </div>
            </div>
          ) : (
            messages.map((message) => (
              <div
                key={message.key}
                className={`chat ${message.role === 'user' ? 'chat-end' : 'chat-start'}`}
              >
                <div className="chat-header text-xs opacity-60">
                  {message.role === 'user' ? 'You' : 'Assistant'}
                </div>
                <div
                  className={`chat-bubble whitespace-pre-wrap ${
                    message.role === 'user' ? 'chat-bubble-primary' : ''
                  }`}
                >
                  {message.text.length > 0 ? (
                    message.text
                  ) : message.streaming ? (
                    <LoadingDots size="sm" />
                  ) : (
                    <span className="opacity-60">(empty response)</span>
                  )}
                </div>
              </div>
            ))
          )}
          <div ref={listEndRef} />
        </div>

        {/* Composer */}
        <form
          onSubmit={handleSend}
          className="flex gap-2 border-t border-base-300 p-3"
        >
          <input
            type="text"
            className="input input-bordered input-sm h-10 flex-1"
            placeholder={
              status === 'open'
                ? 'Type a message…'
                : 'Websocket not connected — sending is disabled'
            }
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={status !== 'open'}
            aria-label="Chat message"
          />
          <Button type="submit" variant="primary" disabled={!canSend}>
            {isStreaming ? (
              <LoadingSpinner size="sm" className="mr-1" />
            ) : (
              <Send className="h-4 w-4 mr-1" />
            )}
            Send
          </Button>
        </form>
      </div>
    </div>
  )
}

function ConnectionBadge({ status }: { status: ConnectionStatus }) {
  switch (status) {
    case 'connecting':
      return (
        <Badge type="warning">
          <LoadingSpinner size="xs" className="mr-1" />
          Connecting…
        </Badge>
      )
    case 'open':
      return <Badge type="success">Connected</Badge>
    case 'closed':
      return <Badge type="error">Disconnected</Badge>
    case 'failed':
      return <Badge type="error">Unavailable</Badge>
  }
}

export default ChatPage
