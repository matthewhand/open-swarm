import { afterEach, describe, expect, it } from 'vitest'
import {
  LAST_READ_STORAGE_KEY,
  loadLastRead,
  saveLastRead,
} from '../chatLastRead'

describe('chat last-read cursor', () => {
  afterEach(() => {
    localStorage.removeItem(LAST_READ_STORAGE_KEY)
  })

  it('persists per agent conversation and ignores a mismatched conversation', () => {
    expect(loadLastRead('jeeves', 'conv-1')).toBeNull()
    expect(saveLastRead('jeeves', 'conv-1', 3)).toEqual({
      conversationId: 'conv-1',
      messageCount: 3,
    })
    expect(loadLastRead('jeeves', 'conv-1')).toEqual({
      conversationId: 'conv-1',
      messageCount: 3,
    })
    expect(loadLastRead('jeeves', 'other')).toBeNull()
    expect(loadLastRead('codey', 'conv-1')).toBeNull()
  })
})
