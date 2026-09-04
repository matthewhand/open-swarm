import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  COPY_EMPTY_TITLE,
  copyButtonLabel,
  copyTextToClipboard,
  messageHasCopyableText,
} from '../clipboard'

/** jsdom does not implement document.execCommand. */
function stubExecCommand(ok: boolean) {
  const exec = vi.fn().mockReturnValue(ok)
  Object.defineProperty(document, 'execCommand', {
    configurable: true,
    writable: true,
    value: exec,
  })
  return exec
}

describe('messageHasCopyableText / copyButtonLabel', () => {
  it('treats empty and whitespace as nothing to copy', () => {
    expect(messageHasCopyableText('')).toBe(false)
    expect(messageHasCopyableText('   \n')).toBe(false)
    expect(messageHasCopyableText('hi')).toBe(true)
    expect(copyButtonLabel(false, false)).toBe(COPY_EMPTY_TITLE)
    expect(copyButtonLabel(true, true)).toBe('Copied')
    expect(copyButtonLabel(false, true)).toBe('Copy message')
  })
})

describe('copyTextToClipboard', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('writes the full raw text via the Clipboard API', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.assign(navigator, { clipboard: { writeText } })
    await expect(copyTextToClipboard('full **markdown**')).resolves.toBe('copied')
    expect(writeText).toHaveBeenCalledWith('full **markdown**')
  })

  it('returns empty without touching the clipboard', async () => {
    const writeText = vi.fn()
    Object.assign(navigator, { clipboard: { writeText } })
    await expect(copyTextToClipboard('   ')).resolves.toBe('empty')
    expect(writeText).not.toHaveBeenCalled()
  })

  it('falls back to textarea + execCommand when writeText rejects', async () => {
    const writeText = vi.fn().mockRejectedValue(new Error('denied'))
    Object.assign(navigator, { clipboard: { writeText } })
    const exec = stubExecCommand(true)

    await expect(copyTextToClipboard('fallback body')).resolves.toBe('copied')
    expect(writeText).toHaveBeenCalledWith('fallback body')
    expect(exec).toHaveBeenCalledWith('copy')
    expect(document.querySelector('textarea')).toBeNull()
  })

  it('falls back when Clipboard API is missing', async () => {
    Object.assign(navigator, { clipboard: undefined })
    const exec = stubExecCommand(true)
    await expect(copyTextToClipboard('no api')).resolves.toBe('copied')
    expect(exec).toHaveBeenCalledWith('copy')
  })

  it('returns failed when Clipboard API and execCommand both fail', async () => {
    Object.assign(navigator, {
      clipboard: { writeText: vi.fn().mockRejectedValue(new Error('denied')) },
    })
    stubExecCommand(false)
    await expect(copyTextToClipboard('still stuck')).resolves.toBe('failed')
  })
})
