import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import ThemeToggle from '../ThemeToggle'
import {
  dispatchSetNavbarThemeVisible,
  THEME_NAVBAR_STORAGE_KEY,
  THEME_STORAGE_KEY,
} from '../../lib/theme'

describe('ThemeToggle component (REQ-110)', () => {
  afterEach(() => {
    localStorage.removeItem(THEME_STORAGE_KEY)
    localStorage.removeItem(THEME_NAVBAR_STORAGE_KEY)
    vi.unstubAllGlobals()
  })

  it('renders with accessible label and cycles theme on click', () => {
    render(<ThemeToggle />)
    const button = screen.getByRole('button', { name: 'Switch to light theme' })
    expect(button).toBeInTheDocument()

    // Click 1: dark -> light
    fireEvent.click(button)
    expect(screen.getByRole('button', { name: 'Switch to system theme' })).toBeInTheDocument()
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe('light')

    // Click 2: light -> system
    fireEvent.click(button)
    expect(screen.getByRole('button', { name: 'Switch to dark theme' })).toBeInTheDocument()
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe('system')

    // Click 3: system -> dark
    fireEvent.click(button)
    expect(screen.getByRole('button', { name: 'Switch to light theme' })).toBeInTheDocument()
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe('dark')
  })

  it('hides when navbar theme control is toggled off, and reappears when toggled on', () => {
    render(<ThemeToggle />)
    expect(screen.getByRole('button', { name: /Switch to (light|dark|system) theme/ })).toBeInTheDocument()

    // Dispatch hide wrapped in act
    act(() => {
      dispatchSetNavbarThemeVisible(false)
    })
    expect(screen.queryByRole('button', { name: /Switch to (light|dark|system) theme/ })).not.toBeInTheDocument()

    // Dispatch show wrapped in act
    act(() => {
      dispatchSetNavbarThemeVisible(true)
    })
    expect(screen.getByRole('button', { name: /Switch to (light|dark|system) theme/ })).toBeInTheDocument()
  })

  it('respects initial persisted hidden state', () => {
    localStorage.setItem(THEME_NAVBAR_STORAGE_KEY, 'false')
    render(<ThemeToggle />)
    expect(screen.queryByRole('button', { name: /Switch to (light|dark|system) theme/ })).not.toBeInTheDocument()
  })
})
