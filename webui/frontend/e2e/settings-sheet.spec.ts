import { test, expect } from '@playwright/test'

async function stubApis(page: import('@playwright/test').Page) {
  await page.route('**/v1/blueprints**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ object: 'list', data: [] }),
    })
  })
  await page.route('**/v1/models**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        object: 'list',
        data: [{ id: 'default', object: 'model', created: 0, owned_by: 'swarm' }],
      }),
    })
  })
  await page.route('**/v1/teams**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ object: 'list', data: [] }),
    })
  })
  await page.route('**/health**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ status: 'ok' }),
    })
  })
}

test('gear opens a DaisyUI modal-end settings sheet over chat', async ({ page }) => {
  const jsErrors: string[] = []
  page.on('pageerror', (e) => jsErrors.push(e.message))
  await stubApis(page)
  await page.goto('/chat')

  await expect(page.getByRole('heading', { name: 'Chat' })).toBeVisible()
  await page.getByRole('button', { name: 'Open settings' }).click()

  const dialog = page.getByRole('dialog', { name: 'Settings' })
  await expect(dialog).toBeVisible()
  await expect(dialog).toHaveClass(/modal-end/)
  // DaisyUI modal-end slides in from the right; wait until the box is on-screen.
  await expect
    .poll(async () =>
      page.locator('dialog.modal-open .modal-box').evaluate((el) => el.getBoundingClientRect().x),
    )
    .toBeLessThan(1200)
  await expect(dialog).not.toHaveClass(/drawer/)

  const sections = page.getByRole('navigation', { name: 'Settings sections' })
  await expect(sections.getByRole('button', { name: 'Remotes' })).toBeVisible()
  await expect(sections.getByRole('button', { name: 'Hermes' })).toBeVisible()
  await expect(sections.getByRole('button', { name: 'OMB' })).toBeVisible()
  await expect(sections.getByRole('button', { name: 'Rakazo' })).toBeVisible()
  await expect(sections.getByRole('button', { name: 'Retention' })).toBeVisible()
  await expect(sections.getByRole('button', { name: 'Hostname' })).toBeVisible()
  await expect(sections.getByRole('button', { name: 'LLM profiles' })).toBeVisible()

  await expect(page.getByRole('radiogroup', { name: 'Retention mode' })).toHaveClass(/join/)
  await page.getByRole('radio', { name: 'Trash' }).click()
  await page.getByRole('button', { name: 'Save retention' }).click()
  await expect(page.getByText('Retention saved')).toBeVisible()
  await expect
    .poll(() => page.evaluate(() => localStorage.getItem('swarm_retention_mode')))
    .toBe('trash')

  await page.getByRole('button', { name: 'Hostname' }).click()
  await page.getByRole('textbox', { name: 'Hostname override' }).fill('swarm.example.com')
  await page.getByRole('button', { name: 'Save hostname' }).click()
  await expect(page.getByText('Hostname saved')).toBeVisible()
  await expect
    .poll(() => page.evaluate(() => localStorage.getItem('swarm_hostname_override')))
    .toBe('swarm.example.com')

  await page.keyboard.press('Escape')
  await expect(dialog).toBeHidden()

  expect(jsErrors, `uncaught JS errors: ${jsErrors.join(' | ')}`).toHaveLength(0)
})
