import { describe, it, expect, beforeEach } from 'vitest'
import { isExperimentalEnabled } from '../flags'

describe('isExperimentalEnabled', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('defaults command palette OFF and other experiments ON when no preference is stored', () => {
    expect(isExperimentalEnabled('command_palette')).toBe(false)
    expect(isExperimentalEnabled('chat_message_actions')).toBe(true)
  })

  it('honours explicit off values', () => {
    localStorage.setItem('swarm_experimental_command_palette', 'off')
    expect(isExperimentalEnabled('command_palette')).toBe(false)

    localStorage.setItem('swarm_experimental_chat_message_actions', 'false')
    expect(isExperimentalEnabled('chat_message_actions')).toBe(false)
  })

  it('honours explicit on values', () => {
    localStorage.setItem('swarm_experimental_command_palette', 'on')
    expect(isExperimentalEnabled('command_palette')).toBe(true)
  })

  it('treats unknown command-palette values as OFF and other unknown values as ON', () => {
    localStorage.setItem('swarm_experimental_command_palette', 'maybe')
    expect(isExperimentalEnabled('command_palette')).toBe(false)
    localStorage.setItem('swarm_experimental_chat_message_actions', 'maybe')
    expect(isExperimentalEnabled('chat_message_actions')).toBe(true)
  })
})
