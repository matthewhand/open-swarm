import { expect, test } from '@playwright/test'
import { installMockInference } from './helpers/mockInference'

for (const width of [320, 375, 401, 640, 768, 1280]) {
  for (const agent of ['codey', 'inventory_demo_with_a_very_long_agent_name']) {
    test(`navbar badge stays aligned and clear of controls: ${width}px ${agent} (#953)`, async ({ page }) => {
      await page.setViewportSize({ width, height: 720 })
      await page.route('**/v1/**', route => route.fulfill({
        json: { object: 'list', data: [], profiles: [], results: [] },
      }))
      await installMockInference(page)
      await page.goto(`/chat?blueprint=${agent}`)
      const badge = page.getByTestId('selected-agent-header')
      await expect(badge).toBeVisible()
      await expect.poll(() => badge.evaluate(element => {
        const box = element.getBoundingClientRect()
        const header = element.closest('header')!.getBoundingClientRect()
        const controls = element.closest('header')!.querySelector('.os-chat-header__controls')!.getBoundingClientRect()
        return Math.abs(box.top + box.height / 2 - (controls.top + controls.height / 2)) <= 1
          && box.left >= header.left
          && box.right <= controls.left - 4
          && box.left + box.width / 2 < header.left + header.width / 2
          && controls.right <= header.right + 1
          && box.top >= header.top - 1
          && box.bottom <= header.bottom + 1
      })).toBe(true)
      // The full agent identity remains usable even when its label truncates.
      await badge.locator('.os-chat-header__avatar-btn').click()
      await expect(page.getByRole('dialog', { name: 'Agent configuration', exact: true })).toBeVisible()
    })
  }
}
