import { describe, it, expect } from 'vitest'
import {
  attachmentCaption,
  createPendingAttachment,
  dataTransferHasFiles,
  filesFromList,
  formatFileSize,
  isImageFile,
  readyAttachmentIds,
} from '../chatAttachments'

describe('chatAttachments helpers', () => {
  it('classifies images and formats size', () => {
    expect(isImageFile({ type: 'image/png' })).toBe(true)
    expect(isImageFile({ type: 'text/plain' })).toBe(false)
    expect(formatFileSize(12)).toBe('12 B')
    expect(formatFileSize(2048)).toBe('2.0 KB')
  })

  it('reads files from a list and detects a Files drag', () => {
    const file = new File(['hello'], 'notes.txt', { type: 'text/plain' })
    expect(filesFromList([file])).toHaveLength(1)
    expect(dataTransferHasFiles(['Files'])).toBe(true)
    expect(dataTransferHasFiles(['text/plain'])).toBe(false)
  })

  it('creates a pending chip and collects ready ids', () => {
    const file = new File(['hello'], 'notes.txt', { type: 'text/plain' })
    const pending = createPendingAttachment(file)
    expect(pending.name).toBe('notes.txt')
    expect(pending.status).toBe('uploading')
    expect(pending.previewUrl).toBeNull()
    expect(readyAttachmentIds([{ ...pending, uploadId: 'att-1' }])).toEqual(['att-1'])
    expect(attachmentCaption(['notes.txt'])).toBe('Attached notes.txt')
  })
})
