import { useState } from 'react'
import { Check, Copy, RotateCcw } from 'lucide-react'
import { useToast } from '../components/DaisyUI'
import {
  COPY_EMPTY_MESSAGE,
  COPY_EMPTY_TITLE,
  COPY_FAILED_MESSAGE,
  COPY_FAILED_TITLE,
  copyButtonLabel,
  copyTextToClipboard,
  messageHasCopyableText,
} from '../lib/clipboard'

/**
 * EXPERIMENTAL: per-message actions for assistant chat bubbles.
 *
 * Copy puts the raw markdown text on the clipboard; Retry re-sends the
 * preceding user message through the normal send path. Toggle off with:
 *   localStorage.setItem('swarm_experimental_chat_message_actions', 'off')
 *
 * React / reply / more are not mounted here — hide-until-ready, not stubs.
 */

export function ChatMessageActions({
  text,
  onRetry,
}: {
  text: string
  onRetry?: () => void
}) {
  const [copied, setCopied] = useState(false)
  const { error } = useToast()
  const canCopy = messageHasCopyableText(text)

  const copy = async () => {
    const result = await copyTextToClipboard(text)
    if (result === 'copied') {
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
      return
    }
    if (result === 'empty') {
      error(COPY_EMPTY_TITLE, COPY_EMPTY_MESSAGE)
      return
    }
    error(COPY_FAILED_TITLE, COPY_FAILED_MESSAGE)
  }

  return (
    <div className="chat-footer mt-0.5 flex items-center gap-1 opacity-70 transition-opacity hover:opacity-100">
      <button
        type="button"
        className="btn btn-ghost btn-xs gap-1"
        onClick={copy}
        disabled={!canCopy}
        aria-label={copyButtonLabel(copied, canCopy)}
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
