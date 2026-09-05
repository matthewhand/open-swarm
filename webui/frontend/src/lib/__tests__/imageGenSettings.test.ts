import { describe, expect, it } from 'vitest'
import {
  defaultAvatarPrompt,
  isGeneratedStillSrc,
  isImageGenConfigured,
  parseImageGenSettings,
} from '../imageGenSettings'

describe('imageGenSettings (REQ-83)', () => {
  it('treats missing/empty payload as off and never invents a host', () => {
    const empty = parseImageGenSettings(null)
    expect(empty.configured).toBe(false)
    expect(empty.base_url).toBe('')
    expect(empty.status).toBe('off')
    expect(isImageGenConfigured(empty)).toBe(false)
    expect(isImageGenConfigured(parseImageGenSettings({ object: 'list', data: [] }))).toBe(false)
  })

  it('parses env name only and ignores live-looking keys', () => {
    const parsed = parseImageGenSettings({
      configured: true,
      base_url: 'http://127.0.0.1:9',
      model: 'still-1',
      api_key_env: 'IMAGE_GEN_API_KEY',
      api_key: 'sk-should-not-be-required',
      avatars: { codey: '/avatars/codey_still.png' },
    })
    expect(parsed.api_key_env).toBe('IMAGE_GEN_API_KEY')
    expect(parsed.base_url).toBe('http://127.0.0.1:9')
    expect(parsed.avatars).toEqual({ codey: '/avatars/codey_still.png' })
    expect(isImageGenConfigured(parsed)).toBe(true)
  })

  it('derives a still prompt from name/role and recognizes generated still paths', () => {
    expect(defaultAvatarPrompt('Codey', 'support')).toMatch(/Codey/)
    expect(defaultAvatarPrompt('Codey', 'support')).toMatch(/no animation/)
    expect(isGeneratedStillSrc('/avatars/codey_still.png')).toBe(true)
    expect(isGeneratedStillSrc('/avatars/codey_avatar.png')).toBe(false)
    expect(isGeneratedStillSrc('')).toBe(false)
  })
})
