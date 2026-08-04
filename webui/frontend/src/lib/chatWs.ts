/**
 * Client for the Django Channels chat websocket.
 *
 * Protocol (verified against src/swarm/consumers.py DjangoChatConsumer and
 * src/swarm/templates/chat.html / websocket_partials/*):
 *
 * - URL: ws(s)://<host>/ws/ai-demo/<conversation_id>/
 *   (the Django UI connects via HTMx: ws-connect="/ws/ai-demo/{{ conversation.id }}/")
 *   An optional ?blueprint=<id> query param sets a connection-level default
 *   blueprint on the server.
 * - Client -> server: JSON text frames: {"message": "<user text>"} with an
 *   optional "blueprint": "<id>" field selecting which discovered blueprint
 *   answers (per-message field overrides the URL default; omitting both
 *   falls back to the server-configured model).
 * - Server -> client: HTML partials with HTMx out-of-band swap attributes:
 *   1. user echo:        <div id="message-list" hx-swap-oob="beforeend">
 *                          <div class="user-message ...">{text}</div></div>
 *   2. assistant start:  <div id="message-list" hx-swap-oob="beforeend">
 *                          <div id="message-response-<hex>" class="assistant-message ..."></div></div>
 *   3. stream chunk:     <div hx-swap-oob="beforeend:#message-response-<hex>">{chunk}</div>
 *   4. final message:    <div id="message-response-<hex>" hx-swap-oob="true" ...>{full text}</div>
 *
 * The consumer requires an authenticated Django session (it closes the
 * socket otherwise) and the server must run under ASGI with Channels for the
 * /ws/ route to exist at all.
 */

export type ChatWsEvent =
  | { kind: 'user_echo'; text: string }
  | { kind: 'assistant_start'; id: string }
  | { kind: 'assistant_chunk'; id: string; text: string }
  | { kind: 'assistant_final'; id: string; text: string }
  | { kind: 'unknown'; raw: string }

const OOB_CHUNK_PREFIX = 'beforeend:#'
const ASSISTANT_ID_PREFIX = 'message-response-'

export function buildChatWsUrl(
  conversationId: string,
  blueprintId?: string,
): string {
  const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws'
  const base = `${scheme}://${window.location.host}/ws/ai-demo/${encodeURIComponent(conversationId)}/`
  return blueprintId
    ? `${base}?blueprint=${encodeURIComponent(blueprintId)}`
    : base
}

/** Build the JSON frame sent to DjangoChatConsumer.receive(). */
export function buildChatWsFrame(message: string, blueprintId?: string): string {
  return JSON.stringify(
    blueprintId ? { message, blueprint: blueprintId } : { message },
  )
}

export function newConversationId(): string {
  try {
    return crypto.randomUUID()
  } catch {
    return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`
  }
}

/** Parse one HTMx HTML partial frame into a typed event. */
export function parseChatWsMessage(raw: string): ChatWsEvent {
  let root: Element | null = null
  try {
    const doc = new DOMParser().parseFromString(raw, 'text/html')
    root = doc.body.firstElementChild
  } catch {
    return { kind: 'unknown', raw }
  }
  if (!root) {
    return { kind: 'unknown', raw }
  }

  const oob = root.getAttribute('hx-swap-oob') ?? ''

  // 3. Streaming chunk appended to an assistant message container.
  if (oob.startsWith(OOB_CHUNK_PREFIX)) {
    return {
      kind: 'assistant_chunk',
      id: oob.slice(OOB_CHUNK_PREFIX.length),
      text: root.textContent ?? '',
    }
  }

  // 1 + 2. Appends to the global #message-list.
  if (root.id === 'message-list' && oob === 'beforeend') {
    const child = root.firstElementChild
    if (child?.classList.contains('user-message')) {
      return { kind: 'user_echo', text: (child.textContent ?? '').trim() }
    }
    if (child?.id.startsWith(ASSISTANT_ID_PREFIX)) {
      return { kind: 'assistant_start', id: child.id }
    }
    return { kind: 'unknown', raw }
  }

  // 4. Final replacement of the assistant message container.
  if (root.id.startsWith(ASSISTANT_ID_PREFIX) && oob === 'true') {
    return {
      kind: 'assistant_final',
      id: root.id,
      text: (root.textContent ?? '').trim(),
    }
  }

  return { kind: 'unknown', raw }
}
