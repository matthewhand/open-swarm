import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import AvatarStack from '../AvatarStack'

describe('REQ-215: Team stack mini-avatars — border matching bg, not grey circle', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  afterEach(() => {
    localStorage.clear()
  })

  it('renders stacked mini avatars with transparent background instead of grey/mark colored disc', () => {
    render(
      <AvatarStack
        faces={[
          { id: 'codey', name: 'Codey', startedAt: 100 },
          { id: 'stewie', name: 'Stewie', startedAt: 200 },
        ]}
      />,
    )

    const stackedAvatars = screen.getAllByTestId('os-stacked-avatar')
    expect(stackedAvatars).toHaveLength(2)

    for (const el of stackedAvatars) {
      // Must not sit on a filled grey or mark-color disc plate
      expect(el.style.backgroundColor).toBe('transparent')
      // Must have the stacked face classes for outline / border matching background
      expect(el).toHaveClass('os-stacked-avatar')
      expect(el).toHaveClass('os-avatar-stack__face')
      expect(el).toHaveClass('os-stacked-avatar--stacked')
    }
  })

  it('renders clean outline with transparent container for custom upload avatars', () => {
    render(
      <AvatarStack
        faces={[
          {
            id: 'custom-lead',
            name: 'Custom Lead',
            startedAt: 100,
            avatarSrc: 'https://example.com/lead.png',
          },
        ]}
      />,
    )

    const el = screen.getByTestId('os-stacked-avatar')
    expect(el.style.backgroundColor).toBe('transparent')

    const img = screen.getByRole('img', { hidden: true })
    expect(img).toHaveAttribute('src', 'https://example.com/lead.png')
  })

  it('renders clean outline with transparent container for Blobs avatars', () => {
    render(
      <AvatarStack
        faces={[
          { id: 'blob-bot', name: 'Blob Bot', startedAt: 150 },
        ]}
      />,
    )

    const el = screen.getByTestId('os-stacked-avatar')
    expect(el.style.backgroundColor).toBe('transparent')

    const svg = el.querySelector('svg[data-avatar-theme="blobs"]')
    expect(svg).not.toBeNull()
  })
})
