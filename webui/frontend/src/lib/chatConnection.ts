/**
 * Shared chat websocket status for chrome that sits outside ChatPage
 * (left-rail hostname icon). ChatPage publishes; the rail subscribes.
 */

export type ChatConnectionStatus = 'connecting' | 'open' | 'closed' | 'failed'

export type HostnameIconTone = 'bland' | 'error'

export const CHAT_CONNECTION_EVENT = 'swarm:chat-connection'

const STATUSES: readonly ChatConnectionStatus[] = [
  'connecting',
  'open',
  'closed',
  'failed',
]

let current: ChatConnectionStatus = 'connecting'

export function isChatConnectionStatus(value: unknown): value is ChatConnectionStatus {
  return (
    typeof value === 'string' &&
    (STATUSES as readonly string[]).includes(value)
  )
}

export function getChatConnection(): ChatConnectionStatus {
  return current
}

export function resetChatConnection(): void {
  current = 'connecting'
}

export function publishChatConnection(status: ChatConnectionStatus): void {
  current = status
  if (typeof window === 'undefined') return
  window.dispatchEvent(
    new CustomEvent<ChatConnectionStatus>(CHAT_CONNECTION_EVENT, { detail: status }),
  )
}

/**
 * Connected (and the initial handshake) stay muted.
 * A drop or handshake failure is the red disconnected state.
 * `connecting` after a drop keeps the previous tone so reconnect
 * only goes bland again when the socket is open.
 */
export function hostnameIconTone(
  status: ChatConnectionStatus,
  previous: HostnameIconTone = 'bland',
): HostnameIconTone {
  if (status === 'open') return 'bland'
  if (status === 'closed' || status === 'failed') return 'error'
  return previous
}
