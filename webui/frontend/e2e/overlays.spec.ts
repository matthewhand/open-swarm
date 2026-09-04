import { test, expect } from '@playwright/test'

const FIXTURE = 'REQ-48 fixture stays mounted'

async function stubApis(page: import('@playwright/test').Page) {
  await page.route('**/chat/thread/**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        agent_id: 'support',
        conversation_id: 'agt-req48',
        messages: [{ role: 'user', content: FIXTURE }],
      }),
    })
  })
  await page.route('**/v1/blueprints**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        object: 'list',
        data: [{ id: 'support', name: 'Support', description: 'Helper' }],
      }),
    })
  })
  await page.route('**/v1/models**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ object: 'list', data: [] }),
    })
  })
  await page.route('**/v1/teams**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        object: 'list',
        data: [{ id: 'lab', object: 'team', description: 'Lab', llm_profile: 'default' }],
      }),
    })
  })
}

test('Settings and Teams sheets open over a fixture chat message', async ({ page }) => {
  const jsErrors: string[] = []
  page.on('pageerror', (e) => jsErrors.push(e.message))
  await stubApis(page)
  await page.goto('/chat')

  await expect(page.getByText(FIXTURE)).toBeVisible()
  await page.getByRole('button', { name: 'Add' }).click()
  await page.getByRole('menuitem', { name: 'Settings' }).click()

  const settings = page.getByRole('dialog', { name: 'Settings' })
  await expect(settings).toBeVisible()
  await expect(settings).toHaveClass(/modal-end/)
  await expect(page.getByText(FIXTURE)).toBeVisible()
  await expect(page).toHaveURL(/\/chat/)

  await settings.getByRole('button', { name: /^Close$/ }).click()
  await expect(settings).toBeHidden()
  await expect(page.getByRole('textbox', { name: 'Chat message' })).toBeVisible()

  await page.getByRole('button', { name: 'Add' }).click()
  await page.getByRole('menuitem', { name: 'Teams' }).click()
  const teams = page.getByRole('dialog', { name: 'Teams' })
  await expect(teams).toBeVisible()
  await expect(page.getByText(FIXTURE)).toBeVisible()
  await teams.getByRole('button', { name: /^Close$/ }).click()
  await expect(page.getByRole('textbox', { name: 'Chat message' })).toBeVisible()

  expect(jsErrors, `uncaught JS errors: ${jsErrors.join(' | ')}`).toHaveLength(0)
})
