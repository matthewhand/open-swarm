import { useState } from 'react'
import { Check, Copy, RotateCcw } from 'lucide-react'

/**
 * EXPERIMENTAL: per-message actions for assistant chat bubbles.
 *
 * Copy puts the raw markdown text on the clipboard; Retry re-sends the
 * preceding user message through the normal send path. Toggle off with:
 *   localStorage.setItem('swarm_experimental_chat_message_actions', 'off')
 */

export function ChatMessageActions({
  text,
  onRetry,
}: {
  text: string
  onRetry?: () => void
}) {
  const [copied, setCopied] = useState(false)

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      /* clipboard unavailable (permissions/insecure context) — no-op */
    }
  }

  return (
    <div className="chat-footer mt-0.5 flex items-center gap-1 opacity-70 transition-opacity hover:opacity-100">
      <button
        type="button"
        className="btn btn-ghost btn-xs gap-1"
        onClick={copy}
        aria-label="Copy message"
      >
        {copied ? (
          <>
            <Check className="h-3 w-3" aria-hidden="true" />
            Copied
          </>
        ) : (
          <>
            <Copy className="h-3 w-3" aria-hidden="true" />
            Copy
          </>
        )}
      </button>
      {onRetry && (
        <button
          type="button"
          className="btn btn-ghost btn-xs gap-1"
          onClick={onRetry}
          aria-label="Resend the previous message"
        >
          <RotateCcw className="h-3 w-3" aria-hidden="true" />
          Retry
        </button>
      )}
    </div>
  )
}
