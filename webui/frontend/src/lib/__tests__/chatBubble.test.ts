import { describe, expect, it } from 'vitest'
import {
  CHAT_BUBBLE_COMPLETE,
  CHAT_BUBBLE_STREAMING,
  chatBubbleClassName,
  workingLabel,
} from '../chatBubble'

describe('chatBubbleClassName', () => {
  it('keeps a near-square bottom-left only while an assistant bubble streams', () => {
    const streaming = chatBubbleClassName('assistant', true)
    expect(streaming.split(' ')).toContain(CHAT_BUBBLE_STREAMING)
    expect(streaming.split(' ')).not.toContain(CHAT_BUBBLE_COMPLETE)
    expect(streaming).toContain('chat-bubble')
  })

  it('rounds all four corners once the assistant stream completes', () => {
    const complete = chatBubbleClassName('assistant', false)
    expect(complete.split(' ')).toContain(CHAT_BUBBLE_COMPLETE)
    expect(complete.split(' ')).not.toContain(CHAT_BUBBLE_STREAMING)
  })

  it('names typing-dot progress Working / {Agent} is working', () => {
    expect(workingLabel(undefined)).toBe('Working')
    expect(workingLabel('')).toBe('Working')
    expect(workingLabel('Support')).toBe('Support is working')
  })

  it('keeps user chat-end bubbles fully rounded even if streaming is true', () => {
    expect(chatBubbleClassName('user', true).split(' ')).toContain(CHAT_BUBBLE_COMPLETE)
    expect(chatBubbleClassName('user', false).split(' ')).toContain(CHAT_BUBBLE_COMPLETE)
    expect(chatBubbleClassName('user', true).split(' ')).not.toContain(CHAT_BUBBLE_STREAMING)
  })
})
