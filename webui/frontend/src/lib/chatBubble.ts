/** DaisyUI 5 `.chat-start .chat-bubble` squares `border-end-start` (bottom-left)
 * and draws a tail; `.chat-end` squares `border-end-end`. Complete bubbles
 * neutralize that. Streaming assistant keeps a near-square bottom-left. */

export const CHAT_BUBBLE_COMPLETE = 'os-chat-bubble--complete'
export const CHAT_BUBBLE_STREAMING = 'os-chat-bubble--streaming'

/** Hover / a11y name for in-bubble typing dots (not inter-bot hops). */
export function workingLabel(agentName?: string | null): string {
  const name = (agentName || '').trim()
  return name ? `${name} is working` : 'Working'
}

export function chatBubbleClassName(
  role: 'user' | 'assistant',
  streaming: boolean,
): string {
  const tone =
    role === 'user' ? 'bg-neutral text-neutral-content' : 'bg-base-200 text-base-content'
  const streamingTail = role === 'assistant' && streaming
  return [
    'chat-bubble',
    'os-chat-bubble',
    streamingTail ? CHAT_BUBBLE_STREAMING : CHAT_BUBBLE_COMPLETE,
    tone,
  ].join(' ')
}
