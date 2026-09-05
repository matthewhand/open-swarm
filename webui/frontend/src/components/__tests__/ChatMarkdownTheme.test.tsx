import { afterEach, describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import fs from 'node:fs'
import path from 'node:path'
import { ChatBubbleBody } from '../ChatMessageBubble'

const cssPath = path.resolve(__dirname, '../../index.css')
const css = fs.readFileSync(cssPath, 'utf8')

const SAMPLE_MD = [
  'Prose with `inline` and a [link](https://example.com/docs).',
  '',
  '> quoted note',
  '',
  '| Col | Val |',
  '| --- | --- |',
  '| a | 1 |',
  '',
  '```python',
  'def hello():',
  '    return "ok"',
  '```',
  '',
  '---',
].join('\n')

function markdownCssContract(source: string): string {
  const start = source.indexOf('/* REQ-804: in-bubble markdown')
  expect(start).toBeGreaterThanOrEqual(0)
  const end = source.indexOf('/* Large dashboard action cards', start)
  expect(end).toBeGreaterThan(start)
  return source.slice(start, end)
}

function chromeCssContract(source: string): string {
  const start = source.indexOf('/* REQ-804: in-bubble chrome')
  expect(start).toBeGreaterThanOrEqual(0)
  return source.slice(start)
}

function applyResolvedTheme(theme: 'light' | 'dark') {
  document.documentElement.setAttribute('data-theme', theme)
  if (theme === 'dark') {
    document.documentElement.style.setProperty('--os-grok-code-inline', '#ff5667')
    document.documentElement.style.setProperty('--os-grok-link', '#4194eb')
    document.documentElement.style.setProperty('--color-primary', '#4a6fa5')
    document.documentElement.style.setProperty('--color-error', '#7a4040')
    document.documentElement.style.setProperty('--color-base-200', '#101010')
    document.documentElement.style.setProperty('--color-base-300', '#242424')
    document.documentElement.style.setProperty('--color-base-content', '#e6e6e6')
  } else {
    document.documentElement.style.setProperty('--os-grok-code-inline', '#c43d4e')
    document.documentElement.style.setProperty('--os-grok-link', '#3d5a80')
    document.documentElement.style.setProperty('--color-primary', '#3d5a80')
    document.documentElement.style.setProperty('--color-error', '#7a4040')
    document.documentElement.style.setProperty('--color-base-200', '#e8e8ea')
    document.documentElement.style.setProperty('--color-base-300', '#d4d4d8')
    document.documentElement.style.setProperty('--color-base-content', '#1a1a1a')
  }
}

describe('REQ-804: chat markdown follows data-theme tokens', () => {
  afterEach(() => {
    document.documentElement.removeAttribute('data-theme')
    document.documentElement.removeAttribute('style')
    document.getElementById('os-md-theme-contract')?.remove()
  })

  it('keeps #464 Grok tokens and adds light variants on the same names', () => {
    expect(css).toContain('--os-grok-code-inline: #ff5667')
    expect(css).toContain('--os-grok-link: #4194eb')
    const lightBlock = css.match(/\[data-theme="light"\]\s*\{([^}]+)\}/)
    expect(lightBlock?.[1]).toContain('--os-grok-code-inline: #c43d4e')
    expect(lightBlock?.[1]).toContain('--os-grok-link: var(--color-primary)')
  })

  it('styles markdown chrome with DaisyUI / Grok variables, not bare #fff/#000', () => {
    const mdCss = markdownCssContract(css)
    expect(mdCss).toContain('.chat-md a')
    expect(mdCss).toContain('.os-chat-md a')
    expect(mdCss).toContain('var(--os-grok-link')
    expect(mdCss).toContain('.chat-md code:not(pre code)')
    expect(mdCss).toContain('var(--os-grok-code-inline')
    expect(mdCss).toContain('.chat-md pre')
    expect(mdCss).toContain('var(--color-base-300)')
    expect(mdCss).toContain('.chat-md blockquote')
    expect(mdCss).toContain('.chat-md table')
    expect(mdCss).toContain('.chat-md th')
    expect(mdCss).toContain('.chat-md hr')
    expect(mdCss).not.toMatch(/#fff(?:fff)?\b/i)
    expect(mdCss).not.toMatch(/#000(?:000)?\b/i)
    expect(css).not.toMatch(/\.os-code-python\s*\{[^}]*#101218/)
    expect(css).not.toMatch(/\.os-code-python\s*\{[^}]*#d6deeb/)
  })

  it('themes status, prior-history, suggestion, and support chrome with DaisyUI tokens', () => {
    expect(css).toContain('.os-chat-status')
    expect(css).toMatch(/\.os-chat-status[\s\S]*?var\(--color-base-content\)/)
    expect(css).toContain('.os-suggestion-chip')
    expect(css).toMatch(/\.os-suggestion-chip[\s\S]*?var\(--color-base-content\)/)
    const chrome = chromeCssContract(css)
    expect(chrome).toContain('.os-handoff-chip')
    expect(chrome).toContain('.os-briefing-popover')
    expect(chrome).toContain('.os-question-card')
    expect(chrome).toContain('.os-question-choice')
    expect(chrome).toContain('.os-attach-chip')
    expect(chrome).toContain('.os-chat-gap')
    expect(chrome).toContain('.os-chat-new')
    expect(chrome).toContain('var(--color-base-content)')
    expect(chrome).not.toMatch(/#fff(?:fff)?\b/i)
    expect(chrome).not.toMatch(/#000(?:000)?\b/i)
  })

  it('renders themed markdown nodes and flips link/code tokens with data-theme', () => {
    const style = document.createElement('style')
    style.id = 'os-md-theme-contract'
    style.textContent = markdownCssContract(css)
    document.head.appendChild(style)

    const { container, unmount } = render(<ChatBubbleBody text={SAMPLE_MD} streaming={false} />)
    const root = screen.getByTestId('chat-md')
    expect(root).toHaveClass('chat-md')
    expect(root.querySelector('code:not(pre code)')).toBeTruthy()
    expect(root.querySelector('a')).toBeTruthy()
    expect(root.querySelector('blockquote')).toBeTruthy()
    expect(root.querySelector('table')).toBeTruthy()
    expect(root.querySelector('hr')).toBeTruthy()
    expect(root.querySelector('pre.os-code-python')).toBeTruthy()

    applyResolvedTheme('dark')
    const darkLink = getComputedStyle(root.querySelector('a')!).color
    const darkCode = getComputedStyle(root.querySelector('code:not(pre code)')!).color

    applyResolvedTheme('light')
    const lightLink = getComputedStyle(root.querySelector('a')!).color
    const lightCode = getComputedStyle(root.querySelector('code:not(pre code)')!).color

    expect(darkLink).not.toBe(lightLink)
    expect(darkCode).not.toBe(lightCode)
    expect(container.querySelector('[data-testid="chat-md"]')).toBeInTheDocument()
    unmount()
  })
})
