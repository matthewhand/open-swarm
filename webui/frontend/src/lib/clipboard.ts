/**
 * Copy helpers for chat message actions (REQ-103).
 *
 * Prefer the async Clipboard API, then textarea + execCommand. Callers must
 * toast on 'empty' / 'failed' — never swallow the result.
 */

export type CopyTextResult = 'copied' | 'empty' | 'failed'

export const COPY_EMPTY_TITLE = 'Nothing to copy'
export const COPY_EMPTY_MESSAGE = 'This message has no text.'
export const COPY_FAILED_TITLE = 'Copy failed'
export const COPY_FAILED_MESSAGE = 'Could not copy the message to the clipboard.'

export function messageHasCopyableText(text: string | null | undefined): boolean {
  return Boolean(text?.trim())
}

export function copyButtonLabel(copied: boolean, canCopy: boolean): string {
  if (!canCopy) return COPY_EMPTY_TITLE
  if (copied) return 'Copied'
  return 'Copy message'
}

export async function copyTextToClipboard(text: string): Promise<CopyTextResult> {
  if (!messageHasCopyableText(text)) return 'empty'

  try {
    if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text)
      return 'copied'
    }
  } catch {
    // Permissions, insecure context, or missing clipboard — try fallback.
  }

  return copyTextViaExecCommand(text) ? 'copied' : 'failed'
}

function copyTextViaExecCommand(text: string): boolean {
  if (typeof document === 'undefined') return false
  const parent = document.body || document.documentElement
  if (!parent) return false

  const textarea = document.createElement('textarea')
  textarea.value = text
  textarea.setAttribute('readonly', '')
  textarea.setAttribute('aria-hidden', 'true')
  textarea.style.position = 'fixed'
  textarea.style.top = '0'
  textarea.style.left = '-9999px'
  textarea.style.opacity = '0'
  parent.appendChild(textarea)
  textarea.focus()
  textarea.select()
  try {
    textarea.setSelectionRange(0, text.length)
  } catch {
    /* jsdom / older engines may omit setSelectionRange */
  }

  let ok = false
  try {
    ok = typeof document.execCommand === 'function' && document.execCommand('copy')
  } catch {
    ok = false
  }
  parent.removeChild(textarea)
  return Boolean(ok)
}
