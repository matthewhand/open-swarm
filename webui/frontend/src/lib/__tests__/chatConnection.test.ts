import { afterEach, describe, expect, it } from 'vitest'
import {
  CHAT_CONNECTION_EVENT,
  getChatConnection,
  hostnameIconTone,
  publishChatConnection,
  resetChatConnection,
} from '../chatConnection'

describe('chatConnection', () => {
  afterEach(() => {
    resetChatConnection()
  })

  it('defaults to connecting and publishes open / closed', () => {
    expect(getChatConnection()).toBe('connecting')
    const seen: string[] = []
    const onStatus = (event: Event) => {
      seen.push((event as CustomEvent<string>).detail)
    }
    window.addEventListener(CHAT_CONNECTION_EVENT, onStatus)
    publishChatConnection('open')
    expect(getChatConnection()).toBe('open')
    publishChatConnection('closed')
    expect(getChatConnection()).toBe('closed')
    window.removeEventListener(CHAT_CONNECTION_EVENT, onStatus)
    expect(seen).toEqual(['open', 'closed'])
  })

  it('keeps connected bland and paints drops red', () => {
    expect(hostnameIconTone('open')).toBe('bland')
    expect(hostnameIconTone('connecting')).toBe('bland')
    expect(hostnameIconTone('closed')).toBe('error')
    expect(hostnameIconTone('failed')).toBe('error')
    expect(hostnameIconTone('connecting', 'error')).toBe('error')
    expect(hostnameIconTone('open', 'error')).toBe('bland')
  })
})
