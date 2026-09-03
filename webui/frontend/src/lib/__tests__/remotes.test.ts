import { describe, expect, it } from 'vitest'
import { botsFromOperate, looksLikeSecret, remoteLabel } from '../remotes'

describe('remotes helpers', () => {
  it('parses Rakazo oRPC bot lists', () => {
    expect(botsFromOperate({ json: [{ id: 'bot-9', name: 'alpha' }] })).toEqual([
      { id: 'bot-9', name: 'alpha' },
    ])
    expect(botsFromOperate([{ botId: 'b1' }])).toEqual([{ id: 'b1' }])
    expect(botsFromOperate(null)).toEqual([])
  })

  it('treats only env-var names as non-secrets', () => {
    expect(looksLikeSecret('RAKAZO_API_KEY')).toBe(false)
    expect(looksLikeSecret('${RAKAZO_SESSION_COOKIE}')).toBe(false)
    expect(looksLikeSecret('')).toBe(false)
    expect(looksLikeSecret('sid=abc')).toBe(true)
    expect(looksLikeSecret('rkz-live-token')).toBe(true)
  })

  it('prefers the kind label over a raw id', () => {
    expect(remoteLabel({ id: 'rakazo', kind: 'rakazo', title: 'Rakazo (Windows2)', label: 'Rakazo' })).toBe(
      'Rakazo',
    )
  })
})
