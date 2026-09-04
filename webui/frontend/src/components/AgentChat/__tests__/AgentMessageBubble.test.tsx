import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { AgentMessageBubble } from '../AgentMessageBubble'
import type { ChatMessage } from '../../../types/agent'

const userMsg: ChatMessage = {
  key: 'u1',
  role: 'user',
  text: 'Ship a demo',
  timestamp: new Date(0),
}

const summaryMsg: ChatMessage = {
  key: 's1',
  role: 'assistant',
  text: 'We agreed to ship a demo.',
  kind: 'summary',
  compacted: [
    { role: 'user', text: 'Ship a demo' },
    { role: 'assistant', text: 'Will do' },
  ],
  timestamp: new Date(0),
}

describe('AgentMessageBubble', () => {
  beforeEach(() => {
    Object.assign(navigator, {
      clipboard: { writeText: vi.fn().mockResolvedValue(undefined) },
    })
  })

  it('reveals copy and compact actions for a chat turn', async () => {
    const onCompact = vi.fn()
    render(
      <AgentMessageBubble
        message={userMsg}
        canCompact
        onCompactToHere={onCompact}
      />,
    )
    expect(screen.getByText('Ship a demo')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Copy message' }))
    await waitFor(() => {
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith('Ship a demo')
    })
    fireEvent.click(screen.getByRole('button', { name: 'Compact to here' }))
    expect(onCompact).toHaveBeenCalled()
  })

  it('renders a rectangular summary with regenerate and original popup', async () => {
    const onRegen = vi.fn()
    render(
      <AgentMessageBubble
        message={summaryMsg}
        onRegenerateSummary={onRegen}
      />,
    )
    expect(screen.getByText('Conversation summary')).toBeInTheDocument()
    const card = screen.getByText('We agreed to ship a demo.').parentElement
    expect(card?.className).toContain('rounded-none')

    fireEvent.click(screen.getByRole('button', { name: 'View original messages' }))
    const dialog = await screen.findByRole('dialog', { name: 'Original messages' })
    expect(dialog).toHaveTextContent('Ship a demo')
    expect(dialog).toHaveTextContent('Will do')
    fireEvent.click(screen.getByRole('button', { name: 'Close dialog' }))
    expect(screen.queryByRole('dialog', { name: 'Original messages' })).not.toBeInTheDocument()

    fireEvent.change(screen.getByLabelText('Steer next regenerate'), {
      target: { value: 'keep API names' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Regenerate summary' }))
    expect(onRegen).toHaveBeenCalledWith('keep API names')
  })

  it('renders Python fenced blocks with pretty-print tokens', () => {
    const msg: ChatMessage = {
      key: 'py1',
      role: 'assistant',
      text: '```python\ndef greet():\n    return "hi"\n```',
      agent: 'Support',
      timestamp: new Date(0),
    }
    const { container } = render(<AgentMessageBubble message={msg} />)
    const pre = container.querySelector('pre.os-code')
    expect(pre).toBeTruthy()
    expect(pre?.getAttribute('data-lang')).toBe('python')
    expect(pre?.className).toContain('os-code-python')
    expect(container.querySelector('.os-py-kw')).toBeTruthy()
    expect(container.querySelector('.os-py-str')).toBeTruthy()
  })
})
