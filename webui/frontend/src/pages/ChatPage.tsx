import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { AlertCircle, MessageSquare, RefreshCw, Send } from 'lucide-react'
import {
  Alert,
  Badge,
  Button,
  Card,
  LoadingDots,
  LoadingSpinner,
  SmartSelect,
} from '../components/DaisyUI'
import { fetchBlueprints, isAuthError } from '../lib/api'
import {
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
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [status, setStatus] = useState<ConnectionStatus>('connecting')
  const [selectedBlueprint, setSelectedBlueprint] = useState('')
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
    // Protocol from DjangoChatConsumer.receive(): {"message": "<text>"}
    ws.send(JSON.stringify({ message: text }))
    setInput('')
  }

  const reconnect = () => setConnectAttempt((n) => n + 1)

  const isStreaming = messages.some((m) => m.streaming)

  return (
    <div className="container mx-auto px-4 py-8 space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2 mb-2">
            <MessageSquare className="h-8 w-8" />
            Chat
          </h1>
          <p className="text-gray-500">
            Live chat over the backend websocket (/ws/ai-demo/…)
          </p>
        </div>
        <ConnectionBadge status={status} />
      </div>

      {/* Blueprint selector (from /v1/blueprints/) */}
      <Card bordered compact>
        <div className="max-w-md">
          {blueprintsQuery.isPending ? (
            <div className="flex items-center gap-2 py-2">
              <LoadingSpinner size="sm" />
              <span className="text-sm">Loading blueprints…</span>
            </div>
          ) : blueprintsQuery.isError ? (
            <Alert type="warning" icon={<AlertCircle className="h-5 w-5" />}>
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
            <SmartSelect
              label="Blueprint"
              placeholder="Select a blueprint"
              value={selectedBlueprint}
              onChange={(e) => setSelectedBlueprint(e.target.value)}
              options={blueprints.map((bp) => ({
                value: bp.id,
                label: bp.name || bp.id,
              }))}
            />
          )}
          <p className="text-xs text-gray-500 mt-2">
            Note: the current websocket protocol does not take a blueprint
            parameter — replies come from the server-configured model. The
            selection here does not change the websocket conversation yet.
          </p>
        </div>
      </Card>

      {/* Fallback when the websocket is unavailable */}
      {(status === 'failed' || status === 'closed') && (
        <Alert type="error" icon={<AlertCircle className="h-5 w-5" />}>
          <div className="space-y-1">
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
            <Button size="sm" variant="ghost" onClick={reconnect}>
              <RefreshCw className="h-4 w-4 mr-1" />
              Reconnect
            </Button>
          </div>
        </Alert>
      )}

      {/* Message list */}
      <Card bordered>
        <div
          className="h-96 overflow-y-auto space-y-1 pr-2"
          aria-live="polite"
        >
          {messages.length === 0 ? (
            <div className="h-full flex items-center justify-center text-gray-500 text-sm">
              {status === 'open'
                ? 'Connected. Send a message to start the conversation.'
                : status === 'connecting'
                  ? 'Connecting to the chat websocket…'
                  : 'No messages — the websocket is not connected.'}
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
      </Card>

      {/* Input */}
      <form onSubmit={handleSend} className="flex gap-2">
        <input
          type="text"
          className="input input-bordered flex-1"
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
