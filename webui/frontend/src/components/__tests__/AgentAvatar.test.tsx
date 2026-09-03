import { describe, it, expect, afterEach } from 'vitest'
import { act, fireEvent, render, screen } from '@testing-library/react'
import { AVATAR_THEME_STORAGE_KEY, saveAvatarTheme } from '../../lib/avatarTheme'
import AgentAvatar from '../AgentAvatar'
import AvatarThemePicker from '../AvatarThemePicker'
import BlobAvatar from '../BlobAvatar'

describe('AgentAvatar themes and eye state', () => {
  afterEach(() => {
    localStorage.removeItem(AVATAR_THEME_STORAGE_KEY)
    act(() => {
      saveAvatarTheme('default')
    })
  })

  it('renders today’s os-agent-dot on Default and a blob SVG on Blobs', () => {
    const { rerender } = render(<AgentAvatar agentId="codey" />)
    const dot = document.querySelector('.os-agent-dot')
    expect(dot).toBeInTheDocument()
    expect(dot).toHaveAttribute('data-avatar-theme', 'default')
    expect(document.querySelector('[data-avatar-theme="blobs"]')).not.toBeInTheDocument()

    act(() => {
      saveAvatarTheme('blobs')
    })
    rerender(<AgentAvatar agentId="codey" />)
    const blob = document.querySelector('[data-avatar-theme="blobs"]')
    expect(blob).toBeInTheDocument()
    expect(blob?.tagName.toLowerCase()).toBe('svg')
    expect(document.querySelector('.os-agent-dot')).not.toBeInTheDocument()
  })

  it('exposes idle vs active eye state as a data attribute', () => {
    saveAvatarTheme('blobs')
    const { rerender } = render(<BlobAvatar agentId="stewie" active={false} />)
    expect(document.querySelector('[data-eye-state="idle"]')).toBeInTheDocument()
    rerender(<BlobAvatar agentId="stewie" active />)
    expect(document.querySelector('[data-eye-state="active"]')).toBeInTheDocument()
    expect(document.querySelector('[data-eye-state="idle"]')).not.toBeInTheDocument()
  })

  it('persists the Settings picker choice', () => {
    render(<AvatarThemePicker />)
    const picker = screen.getByLabelText('Avatar theme')
    expect(picker).toHaveValue('default')
    fireEvent.change(picker, { target: { value: 'blobs' } })
    expect(localStorage.getItem(AVATAR_THEME_STORAGE_KEY)).toBe('blobs')
    expect(picker).toHaveValue('blobs')
  })
})
