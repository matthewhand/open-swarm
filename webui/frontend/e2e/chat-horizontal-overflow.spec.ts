import { expect, test } from '@playwright/test'
import { installMockInference } from './helpers/mockInference'

for (const width of [320, 375, 401, 768, 1280]) {
  test(`message actions fit a ${width}px chat without horizontal scrolling (#951)`, async ({ page }) => {
    await page.setViewportSize({ width, height: 720 })
    // No credentials, external services or real model calls in a layout test.
    await page.route('**/v1/**', route => route.fulfill({
      json: { object: 'list', data: [], results: [], profiles: [] },
    }))
    await installMockInference(page, { reply: 'The fictional inventory reorder costs $54.', envelope: 'spa' })
    await page.goto('/chat')
    const composer = page.getByRole('textbox', { name: 'Chat message' })
    await composer.fill('What should we reorder, and what will it cost?')
    await composer.press('Enter')
    const conversation = page.getByRole('log', { name: 'Conversation' })
    await expect(conversation.getByText('The fictional inventory reorder costs $54.')).toBeVisible()
    const actions = conversation.getByTestId('os-message-row-actions')
    await expect(actions).toHaveCount(2)
    await expect.poll(() => conversation.evaluate(element => element.scrollWidth - element.clientWidth)).toBeLessThanOrEqual(1)
    // Wrapping must keep every control within its row, rather than clip it or
    // hide the scrollbar while the Read aloud/Compress controls stay offscreen.
    for (const row of await actions.all()) {
      await expect.poll(() => row.evaluate(element => {
        const bounds = element.getBoundingClientRect()
        return [...element.children].every(child => {
          const box = child.getBoundingClientRect()
          return box.left >= bounds.left - 1 && box.right <= bounds.right + 1
        })
      })).toBe(true)
    }
    // A closed reaction palette must not intercept the message or its controls.
    await conversation.getByText('The fictional inventory reorder costs $54.').hover()
    await conversation.getByTestId('message-reply-action').last().click()
    await expect(page.getByTestId('composer-reply-strip')).toContainText('fictional inventory')
    const reactions = conversation.getByTestId('message-add-reaction').last()
    await reactions.click()
    await expect(conversation.getByRole('button', { name: 'React with 👍' }).last()).toBeVisible()
  })
}
