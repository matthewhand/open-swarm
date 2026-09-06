import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { ChatBubbleBody } from '../ChatMessageBubble'

const TEXT = `Created **BA → Engineer → Tester**. You did not write Python.

\`\`\`swarm-nl-blueprint
{
  "id": "ba_eng_tester",
  "title": "BA → Engineer → Tester",
  "usable": true,
  "chatHref": "/chat?blueprint=ba_eng_tester",
  "graphLabel": "BA → Engineer → Tester",
  "edges": [["ba", "engineer"], ["engineer", "tester"]],
  "userWrotePython": false,
  "code": "class Hidden:\\n    pass\\n"
}
\`\`\`
`

describe('ChatBubbleBody REQ-158 card', () => {
  it('renders the usable card and keeps generated Python out of the markdown', () => {
    render(
      <MemoryRouter>
        <ChatBubbleBody text={TEXT} streaming={false} />
      </MemoryRouter>,
    )
    expect(screen.getByTestId('support-nl-blueprint-card')).toBeInTheDocument()
    expect(screen.getByTestId('support-nl-code-hidden')).toBeInTheDocument()
    expect(screen.getByTestId('chat-md').textContent).toMatch(/did not write Python/)
    expect(screen.getByTestId('chat-md').textContent).not.toMatch(/class Hidden/)
  })
})
