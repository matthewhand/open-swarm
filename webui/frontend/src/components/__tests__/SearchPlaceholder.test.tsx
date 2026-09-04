import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { SearchBar } from '../AgentSidebar/SearchBar'

describe('Search Placeholder (REQ-185)', () => {
  it('renders search input with placeholder exactly "Search"', () => {
    render(<SearchBar value="" onChange={vi.fn()} />)
    const input = screen.getByRole('searchbox')
    expect(input).toHaveAttribute('placeholder', 'Search')
    expect(input.getAttribute('placeholder')).not.toMatch(/Ctrl|⌘|Cmd/i)
  })
})
