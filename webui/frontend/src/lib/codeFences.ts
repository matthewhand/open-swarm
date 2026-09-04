import { copyTextToClipboard } from './clipboard'

/** Threshold in lines to determine whether a fenced block should collapse by default (REQ-117). */
export const CODE_LINE_THRESHOLD = 10

/**
 * Augment rendered markdown code fences with:
 * 1. Always-available Copy button
 * 2. If > CODE_LINE_THRESHOLD lines: collapsed by default with hover-revealed Expand button,
 *    sticky per-message expand, and re-collapse.
 */
export function setupCodeFenceControls(
  root: HTMLElement,
  expandedIndices: Set<number>,
  onToggle?: (index: number, expanded: boolean) => void,
) {
  const pres = root.querySelectorAll('pre')
  pres.forEach((pre, index) => {
    const code = pre.querySelector('code')
    const fullText = code?.textContent ?? pre.textContent ?? ''
    const lines = fullText.split('\n')
    const effectiveLines =
      lines.length > 1 && lines[lines.length - 1] === '' ? lines.length - 1 : lines.length
    const isLong = effectiveLines > CODE_LINE_THRESHOLD

    // Check or create the actions chrome
    let actions = pre.querySelector<HTMLDivElement>('.os-code-actions')
    if (!actions) {
      actions = document.createElement('div')
      actions.className = 'os-code-actions'
      pre.insertBefore(actions, pre.firstChild)
    }

    // Always-available Copy button
    let copyBtn = actions.querySelector<HTMLButtonElement>('[data-testid="code-copy"]')
    if (!copyBtn) {
      copyBtn = document.createElement('button')
      copyBtn.type = 'button'
      copyBtn.className = 'btn btn-ghost btn-xs os-code-copy'
      copyBtn.dataset.testid = 'code-copy'
      copyBtn.setAttribute('aria-label', 'Copy code')
      copyBtn.textContent = 'Copy'
      copyBtn.addEventListener('click', (event) => {
        event.preventDefault()
        event.stopPropagation()
        void copyTextToClipboard(fullText)
      })
      actions.appendChild(copyBtn)
    }

    if (!isLong) {
      pre.classList.remove('os-code--collapsible', 'os-code--collapsed', 'os-code--expanded')
      pre.removeAttribute('data-collapsed')
      pre.removeAttribute('data-expanded')
      const expandBtn = actions.querySelector(
        '[data-testid="code-expand"], [data-testid="code-collapse"]',
      )
      if (expandBtn) expandBtn.remove()
      return
    }

    pre.classList.add('os-code--collapsible')
    const isExpanded = expandedIndices.has(index)

    let expandBtn = actions.querySelector<HTMLButtonElement>(
      '[data-testid="code-expand"], [data-testid="code-collapse"]',
    )
    if (!expandBtn) {
      expandBtn = document.createElement('button')
      expandBtn.type = 'button'
      expandBtn.className = 'btn btn-ghost btn-xs os-code-expand'
      actions.insertBefore(expandBtn, copyBtn)
    }

    if (isExpanded) {
      pre.classList.remove('os-code--collapsed')
      pre.classList.add('os-code--expanded')
      pre.dataset.expanded = 'true'
      delete pre.dataset.collapsed
      expandBtn.dataset.testid = 'code-collapse'
      expandBtn.setAttribute('aria-label', 'Collapse code')
      expandBtn.textContent = 'Collapse'
    } else {
      pre.classList.add('os-code--collapsed')
      pre.classList.remove('os-code--expanded')
      pre.dataset.collapsed = 'true'
      delete pre.dataset.expanded
      expandBtn.dataset.testid = 'code-expand'
      expandBtn.setAttribute('aria-label', 'Expand code')
      expandBtn.textContent = 'Expand'
    }

    expandBtn.onclick = (event) => {
      event.preventDefault()
      event.stopPropagation()
      if (expandedIndices.has(index)) {
        expandedIndices.delete(index)
        onToggle?.(index, false)
        setupCodeFenceControls(root, expandedIndices, onToggle)
      } else {
        expandedIndices.add(index)
        onToggle?.(index, true)
        setupCodeFenceControls(root, expandedIndices, onToggle)
      }
    }
  })
}
