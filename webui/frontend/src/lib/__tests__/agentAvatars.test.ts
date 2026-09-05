import { afterEach, describe, expect, it } from 'vitest'
import {
  GENERATED_AVATARS_KEY,
  loadGeneratedAvatar,
  rememberGeneratedAvatar,
  resetGeneratedAvatars,
} from '../agentAvatars'

describe('agentAvatars store (REQ-83)', () => {
  afterEach(() => {
    resetGeneratedAvatars()
  })

  it('remembers a still path per agent without storing a token', () => {
    rememberGeneratedAvatar('codey', '/avatars/codey_still.png')
    expect(loadGeneratedAvatar('codey')).toBe('/avatars/codey_still.png')
    const raw = localStorage.getItem(GENERATED_AVATARS_KEY) || ''
    expect(raw).toContain('/avatars/codey_still.png')
    expect(raw).not.toMatch(/sk-/)
  })
})
