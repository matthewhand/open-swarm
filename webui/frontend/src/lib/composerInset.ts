/** Live bottom inset so the sticky composer never covers transcript content. */

export const COMPOSER_INSET_VAR = '--os-chat-composer-inset'

/** Slack used when deciding whether the user is still pinned to the bottom. */
export const COMPOSER_PIN_SLACK_PX = 48

export function measureComposerDockInset(dock: Element | null): number {
  if (!dock) return 0
  const box = dock.getBoundingClientRect()
  const height = box.height || (dock instanceof HTMLElement ? dock.offsetHeight : 0)
  return Math.max(0, Math.ceil(height))
}

export function composerInsetCustomProperty(insetPx: number): {
  [COMPOSER_INSET_VAR]: string
} {
  return { [COMPOSER_INSET_VAR]: `${Math.max(0, insetPx)}px` }
}

export function isPinnedToTranscriptBottom(
  el: { scrollHeight: number; scrollTop: number; clientHeight: number },
  insetPx: number,
  slackPx = COMPOSER_PIN_SLACK_PX,
): boolean {
  const threshold = Math.max(slackPx, insetPx)
  return el.scrollHeight - el.scrollTop - el.clientHeight < threshold
}

export function scrollTranscriptToBottom(box: HTMLElement | null, listEnd?: HTMLElement | null) {
  if (box) {
    box.scrollTop = box.scrollHeight
    return
  }
  listEnd?.scrollIntoView({ block: 'end' })
}
