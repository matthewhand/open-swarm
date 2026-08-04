import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { ApiAccessPanel, buildSnippets } from '../ApiAccessPanel'

describe('buildSnippets', () => {
  it('embeds base url, model, and token in every snippet', () => {
    const s = buildSnippets('http://host:8000/v1', 'sk-secret', 'cli_fusion')
    expect(s.curl).toContain('http://host:8000/v1/chat/completions')
    expect(s.curl).toContain('Bearer sk-secret')
    expect(s.curl).toContain('"model":"cli_fusion"')
    expect(s.python).toContain('base_url="http://host:8000/v1"')
    expect(s.python).toContain('model="cli_fusion"')
    expect(s.openWebUI).toContain('Base URL: http://host:8000/v1')
    expect(s.responses).toContain('http://host:8000/v1/responses')
    expect(s.responses).toContain('"input":"ping"')
  })

  it('uses a placeholder key when auth is disabled (no token)', () => {
    const s = buildSnippets('http://host/v1', null, 'm')
    expect(s.curl).toContain('Bearer not-needed')
    expect(s.python).toContain('api_key="not-needed"')
  })
})

describe('ApiAccessPanel', () => {
  it('renders the base URL, model options, and copy blocks', () => {
    render(
      <ApiAccessPanel
        baseUrl="http://localhost:8000/v1"
        token={null}
        models={['cli_fusion', 'cli_agent']}
      />,
    )
    expect(screen.getByText('http://localhost:8000/v1')).toBeInTheDocument()
    expect(screen.getByText(/any key works/i)).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'cli_fusion' })).toBeInTheDocument()
    expect(screen.getAllByText('Copy').length).toBe(4)
  })

  it('shows the token suffix when a token is set', () => {
    render(<ApiAccessPanel baseUrl="http://x/v1" token="sk-12345678" models={['cli_fusion']} />)
    expect(screen.getByText('…5678')).toBeInTheDocument()
  })
})
