import { expect, test } from '@playwright/test'
import { installMockInference } from './helpers/mockInference'

for (const width of [320, 375, 401, 768, 1280]) {
  test(`API composer encloses Send and expands usage at ${width}px (#955)`, async ({ page }) => {
    await page.setViewportSize({ width, height: 720 })
    await page.route('**/v1/**', route => route.fulfill({ json: { object: 'list', data: [], results: [], profiles: [] } }))
    await installMockInference(page, { reply: 'Inventory checked.', envelope: 'spa' })
    await page.route('**/chat/context-usage/**', route => {
      const url = new URL(route.request().url())
      return route.fulfill({ json: {
        type: 'context_usage', conversation_id: url.searchParams.get('conversation_id'),
        agent_id: url.searchParams.get('agent'), tokens: 16000, window: 128000,
        pct: 12.5, estimate: true, last_output: 320,
        breakdown: { messages: 12000, summaries: 2000, system: 1500, tools: 500 },
      } })
    })
    await page.goto('/chat?blueprint=support')
    const input = page.getByRole('textbox', { name: 'Chat message' })
    await input.fill('Check inventory')
    await input.press('Shift+Enter')
    await expect(input).toHaveValue('Check inventory\n')
    await expect.poll(() => page.getByRole('log', { name: 'Conversation' }).evaluate(element => element.scrollWidth - element.clientWidth)).toBeLessThanOrEqual(1)
    await input.press('Enter')
    await expect(page.getByRole('log', { name: 'Conversation' }).getByText('Inventory checked.')).toBeVisible()
    const frame = page.getByTestId('api-composer')
    await expect(frame).toBeVisible()
    await expect(page.getByTestId('context-usage-badge')).toContainText('16k tokens')
    await expect(page.getByRole('region', { name: 'Token usage details' })).toHaveCount(0)
    await expect(page.getByRole('button', { name: 'Context window usage' })).toHaveText('')
    await expect(page.getByRole('button', { name: 'Context window usage' })).toHaveAttribute('aria-expanded', 'false')
    await expect.poll(() => frame.locator('.os-api-usage__summary').evaluate(element => element.getBoundingClientRect().height)).toBeLessThanOrEqual(28)
    await page.getByRole('button', { name: 'Context window usage' }).click()
    const panel = page.getByRole('region', { name: 'Token usage details' })
    await expect(panel).toContainText('Context used')
    await expect(panel).toContainText('Last reply')
    await expect(panel).toContainText('320 tokens')
    await expect(panel.getByRole('progressbar')).toHaveAttribute('aria-valuemax', '128000')
    await expect.poll(() => frame.evaluate(element => {
      const box = element.getBoundingClientRect()
      const sendButton = element.querySelector('.os-composer__send')
      if (!sendButton) return false
      const send = sendButton.getBoundingClientRect()
      return box.left >= 0 && box.right <= innerWidth && box.bottom <= innerHeight &&
        send.left >= box.left && send.right <= box.right && send.bottom <= box.bottom
    })).toBe(true)
    await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1)
    await panel.getByRole('button', { name: 'More details' }).focus()
    await page.keyboard.press('Escape')
    await expect(panel).toHaveCount(0)
    await expect(page.getByRole('button', { name: 'Context window usage' })).toBeFocused()
    await input.fill('Still usable')
    await frame.locator('.os-composer__send').click()
    await expect(input).toHaveValue('')
  })
}
