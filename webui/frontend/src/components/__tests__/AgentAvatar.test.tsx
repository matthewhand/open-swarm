import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import AgentAvatar, { DEFAULT_AGENT_AVATAR_SRC } from '../AgentAvatar'

describe('AgentAvatar', () => {
  it('uses the original default SVG when no custom src is set', () => {
    const { container } = render(<AgentAvatar />)
    const img = container.querySelector('img')
    expect(img).toBeTruthy()
    expect(img).toHaveAttribute('data-agent-avatar', 'default')
    expect(img).toHaveAttribute('src', DEFAULT_AGENT_AVATAR_SRC)
    expect(DEFAULT_AGENT_AVATAR_SRC).toMatch(/^data:image\/svg\+xml/)
    const svg = decodeURIComponent(
      DEFAULT_AGENT_AVATAR_SRC.includes(';base64,')
        ? atob(DEFAULT_AGENT_AVATAR_SRC.split(',')[1])
        : DEFAULT_AGENT_AVATAR_SRC.replace(/^data:image\/svg\+xml[^,]*,/, ''),
    )
    expect(svg).toContain('#3deef5')
    expect(svg).toMatch(/<circle/i)
  })

  it('uses a custom src when provided', () => {
    const { container } = render(<AgentAvatar src="/avatars/codey_avatar.png" alt="Codey" />)
    const img = container.querySelector('img')
    expect(img).toHaveAttribute('data-agent-avatar', 'custom')
    expect(img).toHaveAttribute('src', '/avatars/codey_avatar.png')
    expect(img).toHaveAttribute('alt', 'Codey')
  })

  it('treats blank custom src as the default', () => {
    const { container } = render(<AgentAvatar src="   " />)
    expect(container.querySelector('img')).toHaveAttribute('data-agent-avatar', 'default')
  })
})
