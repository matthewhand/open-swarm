import { describe, it, expect } from 'vitest'
import {
  buildChatWsUrl,
  buildChatWsFrame,
  parseChatWsMessage,
} from '../chatWs'

describe('buildChatWsUrl', () => {
  it('builds a ws:// URL on the current host for the conversation', () => {
    // jsdom serves http://localhost -> ws scheme.
    const url = buildChatWsUrl('conv1')
    expect(url).toMatch(/^ws:\/\/[^/]+\/ws\/ai-demo\/conv1\/$/)
  })

  it('appends the blueprint query param when given', () => {
    expect(buildChatWsUrl('conv1', 'bp-7')).toMatch(/\/ws\/ai-demo\/conv1\/\?blueprint=bp-7$/)
  })

  it('URL-encodes both the conversation id and blueprint id', () => {
    const url = buildChatWsUrl('a/b c', 'x&y')
    expect(url).toContain('/ws/ai-demo/a%2Fb%20c/')
    expect(url).toContain('blueprint=x%26y')
  })
})

describe('buildChatWsFrame', () => {
  it('emits a bare message frame', () => {
    expect(buildChatWsFrame('hello')).toBe('{"message":"hello"}')
  })

  it('includes the blueprint field when selected', () => {
    expect(buildChatWsFrame('hi', 'bp-2')).toBe('{"message":"hi","blueprint":"bp-2"}')
  })

  it('omits blueprint when empty/undefined', () => {
    expect(buildChatWsFrame('hi', '')).toBe('{"message":"hi"}')
    expect(buildChatWsFrame('hi', undefined)).toBe('{"message":"hi"}')
  })

  it('round-trips back to the original message via JSON.parse', () => {
    expect(JSON.parse(buildChatWsFrame('quote " and \\ slash')).message).toBe(
      'quote " and \\ slash',
    )
  })
})

describe('parseChatWsMessage', () => {
  it('parses a user echo append', () => {
    const raw =
      '<div id="message-list" hx-swap-oob="beforeend"><div class="user-message foo"> hi there </div></div>'
    expect(parseChatWsMessage(raw)).toEqual({ kind: 'user_echo', text: 'hi there' })
  })

  it('parses an assistant-start append', () => {
    const raw =
      '<div id="message-list" hx-swap-oob="beforeend"><div id="message-response-abc123" class="assistant-message"></div></div>'
    expect(parseChatWsMessage(raw)).toEqual({
      kind: 'assistant_start',
      id: 'message-response-abc123',
    })
  })

  it('parses a streaming chunk targeted at an assistant container', () => {
    const raw = '<div hx-swap-oob="beforeend:#message-response-abc123">partial</div>'
    expect(parseChatWsMessage(raw)).toEqual({
      kind: 'assistant_chunk',
      id: 'message-response-abc123',
      text: 'partial',
    })
  })

  it('parses the final assistant replacement', () => {
    const raw =
      '<div id="message-response-abc123" hx-swap-oob="true" class="assistant-message"> full answer </div>'
    expect(parseChatWsMessage(raw)).toEqual({
      kind: 'assistant_final',
      id: 'message-response-abc123',
      text: 'full answer',
    })
  })

  it('falls back to unknown for empty or unrecognized frames', () => {
    expect(parseChatWsMessage('')).toEqual({ kind: 'unknown', raw: '' })
    const weird = '<div id="something-else" hx-swap-oob="beforeend"><span>x</span></div>'
    expect(parseChatWsMessage(weird)).toEqual({ kind: 'unknown', raw: weird })
  })
})
