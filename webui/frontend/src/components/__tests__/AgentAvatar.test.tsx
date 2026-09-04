import { describe, it, expect } from 'vitest'
import { fireEvent, render } from '@testing-library/react'
import AgentAvatar, {
  DEFAULT_AGENT_AVATAR_SRC,
  agentAvatarKind,
  resolveAgentAvatarSrc,
} from '../AgentAvatar'

describe('AgentAvatar', () => {
  it('uses the bland default when no custom src is set', () => {
    const { container } = render(<AgentAvatar />)
    const face = container.querySelector('[data-agent-avatar]')
    expect(face).toHaveAttribute('data-agent-avatar', 'default')
    expect(container.querySelector('img')).toHaveAttribute('src', DEFAULT_AGENT_AVATAR_SRC)
    expect(DEFAULT_AGENT_AVATAR_SRC).toMatch(/^data:image\/svg\+xml/)
    expect(agentAvatarKind(null)).toBe('default')
    expect(resolveAgentAvatarSrc('')).toBe(DEFAULT_AGENT_AVATAR_SRC)
  })

  it('paints a custom src', () => {
    const { container } = render(
      <AgentAvatar src="/avatars/codey_avatar.png" alt="Codey" />,
    )
    const img = container.querySelector('img')
    expect(container.querySelector('[data-agent-avatar]')).toHaveAttribute(
      'data-agent-avatar',
      'custom',
    )
    expect(img).toHaveAttribute('src', '/avatars/codey_avatar.png')
    expect(img).toHaveAttribute('alt', 'Codey')
    expect(agentAvatarKind('/avatars/codey_avatar.png')).toBe('custom')
  })

  it('treats blank custom src as the default', () => {
    const { container } = render(<AgentAvatar src="   " />)
    expect(container.querySelector('[data-agent-avatar]')).toHaveAttribute(
      'data-agent-avatar',
      'default',
    )
  })

  it('falls back to the default when a custom src errors', () => {
    const { container } = render(<AgentAvatar src="/avatars/missing.png" />)
    const img = container.querySelector('img')!
    expect(img).toHaveAttribute('src', '/avatars/missing.png')
    fireEvent.error(img)
    expect(container.querySelector('[data-agent-avatar]')).toHaveAttribute(
      'data-agent-avatar',
      'default',
    )
    expect(container.querySelector('img')).toHaveAttribute('src', DEFAULT_AGENT_AVATAR_SRC)
  })
})
