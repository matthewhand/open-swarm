import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ChatMessageBubble } from '../ChatMessageBubble'
import * as clipboard from '../../lib/clipboard'

describe('REQ-117: Fenced code blocks collapse, hover expand, copy, re-collapse', () => {
  const shortCode = '```typescript\nconst a = 1\nconst b = 2\nconsole.log(a + b)\n```'
  const longCode = [
    '```typescript',
    'const line1 = 1',
    'const line2 = 2',
    'const line3 = 3',
    'const line4 = 4',
    'const line5 = 5',
    'const line6 = 6',
    'const line7 = 7',
    'const line8 = 8',
    'const line9 = 9',
    'const line10 = 10',
    'const line11 = 11',
    'const line12 = 12',
    '```',
  ].join('\n')

  let copySpy: ReturnType<typeof vi.spyOn>

  beforeEach(() => {
    copySpy = vi.spyOn(clipboard, 'copyTextToClipboard').mockResolvedValue('copied')
  })

  it('short code blocks (<=10 lines) are never clipped and have copy button', () => {
    const { container } = render(
      <ChatMessageBubble
        role="assistant"
        agentName="Codey"
        text={shortCode}
        streaming={false}
        canEdit={false}
        editing={false}
        onStartEdit={() => {}}
        onCancelEdit={() => {}}
        onSaveEdit={() => {}}
      />,
    )

    const pre = container.querySelector('pre')
    expect(pre).toBeInTheDocument()
    expect(pre).not.toHaveClass('os-code--collapsible')
    expect(pre).not.toHaveClass('os-code--collapsed')
    expect(pre?.querySelector('[data-testid="code-expand"]')).toBeNull()
    expect(pre?.querySelector('[data-testid="code-copy"]')).toBeInTheDocument()
  })

  it('long code blocks (>10 lines) start collapsed with copy and expand buttons', () => {
    const { container } = render(
      <ChatMessageBubble
        role="assistant"
        agentName="Codey"
        text={longCode}
        streaming={false}
        canEdit={false}
        editing={false}
        onStartEdit={() => {}}
        onCancelEdit={() => {}}
        onSaveEdit={() => {}}
      />,
    )

    const pre = container.querySelector('pre')
    expect(pre).toBeInTheDocument()
    expect(pre).toHaveClass('os-code--collapsible')
    expect(pre).toHaveClass('os-code--collapsed')
    expect(pre).toHaveAttribute('data-collapsed', 'true')
    expect(pre?.querySelector('[data-testid="code-copy"]')).toBeInTheDocument()

    const expandBtn = pre?.querySelector('[data-testid="code-expand"]')
    expect(expandBtn).toBeInTheDocument()
    expect(expandBtn).toHaveTextContent('Expand')
  })

  it('hovering over the collapsed block does NOT auto-expand it', () => {
    const { container } = render(
      <ChatMessageBubble
        role="assistant"
        agentName="Codey"
        text={longCode}
        streaming={false}
        canEdit={false}
        editing={false}
        onStartEdit={() => {}}
        onCancelEdit={() => {}}
        onSaveEdit={() => {}}
      />,
    )

    const pre = container.querySelector('pre')!
    fireEvent.mouseEnter(pre)
    fireEvent.mouseOver(pre)

    expect(pre).toHaveClass('os-code--collapsed')
    expect(pre?.querySelector('[data-testid="code-expand"]')).toBeInTheDocument()
    expect(pre?.querySelector('[data-testid="code-collapse"]')).toBeNull()
  })

  it('clicking Expand expands the block and sticks across re-renders', () => {
    const { container, rerender } = render(
      <ChatMessageBubble
        role="assistant"
        agentName="Codey"
        text={longCode}
        streaming={false}
        canEdit={false}
        editing={false}
        onStartEdit={() => {}}
        onCancelEdit={() => {}}
        onSaveEdit={() => {}}
      />,
    )

    const pre = container.querySelector('pre')!
    const expandBtn = pre.querySelector('[data-testid="code-expand"]')!
    fireEvent.click(expandBtn)

    expect(pre).not.toHaveClass('os-code--collapsed')
    expect(pre).toHaveClass('os-code--expanded')
    expect(pre).toHaveAttribute('data-expanded', 'true')

    const collapseBtn = pre.querySelector('[data-testid="code-collapse"]')
    expect(collapseBtn).toBeInTheDocument()
    expect(collapseBtn).toHaveTextContent('Collapse')

    // Rerender (scrolling/props update) -> stays expanded (sticky)
    rerender(
      <ChatMessageBubble
        role="assistant"
        agentName="Codey"
        text={longCode}
        streaming={false}
        canEdit={false}
        editing={false}
        onStartEdit={() => {}}
        onCancelEdit={() => {}}
        onSaveEdit={() => {}}
      />,
    )

    const preAfterRerender = container.querySelector('pre')!
    expect(preAfterRerender).toHaveClass('os-code--expanded')
    expect(preAfterRerender?.querySelector('[data-testid="code-collapse"]')).toBeInTheDocument()
  })

  it('clicking Collapse returns the block to the collapsed state', () => {
    const { container } = render(
      <ChatMessageBubble
        role="assistant"
        agentName="Codey"
        text={longCode}
        streaming={false}
        canEdit={false}
        editing={false}
        onStartEdit={() => {}}
        onCancelEdit={() => {}}
        onSaveEdit={() => {}}
      />,
    )

    const pre = container.querySelector('pre')!
    const expandBtn = pre.querySelector('[data-testid="code-expand"]')!
    fireEvent.click(expandBtn)
    expect(pre).toHaveClass('os-code--expanded')

    const collapseBtn = pre.querySelector('[data-testid="code-collapse"]')!
    fireEvent.click(collapseBtn)
    expect(pre).toHaveClass('os-code--collapsed')
    expect(pre).not.toHaveClass('os-code--expanded')
    expect(pre.querySelector('[data-testid="code-expand"]')).toBeInTheDocument()
  })

  it('copy button copies full code text even when collapsed', () => {
    const { container } = render(
      <ChatMessageBubble
        role="assistant"
        agentName="Codey"
        text={longCode}
        streaming={false}
        canEdit={false}
        editing={false}
        onStartEdit={() => {}}
        onCancelEdit={() => {}}
        onSaveEdit={() => {}}
      />,
    )

    const pre = container.querySelector('pre')!
    expect(pre).toHaveClass('os-code--collapsed')
    const copyBtn = pre.querySelector('[data-testid="code-copy"]')!
    fireEvent.click(copyBtn)

    expect(copySpy).toHaveBeenCalledTimes(1)
    const copiedText = copySpy.mock.calls[0][0]
    expect(copiedText).toContain('const line1 = 1')
    expect(copiedText).toContain('const line12 = 12')
  })

  it('also collapses long code blocks in user bubbles', () => {
    const { container } = render(
      <ChatMessageBubble
        role="user"
        agentName="User"
        text={longCode}
        streaming={false}
        canEdit={false}
        editing={false}
        onStartEdit={() => {}}
        onCancelEdit={() => {}}
        onSaveEdit={() => {}}
      />,
    )

    const pre = container.querySelector('pre')
    expect(pre).toHaveClass('os-code--collapsible')
    expect(pre).toHaveClass('os-code--collapsed')
    expect(pre?.querySelector('[data-testid="code-expand"]')).toBeInTheDocument()
  })
})
