import { test, expect } from '@playwright/test'

const REQ42_INJECTED_FIXTURE = 'REQ42_INJECTED_FIXTURE_MARKER'

const BLUEPRINTS = {
  object: 'list',
  data: [
    {
      id: 'codey',
      object: 'blueprint',
      name: 'Codey',
      description: 'Code assistant',
      abbreviation: null,
      required_mcp_servers: [],
      tags: [],
      installed: true,
      compiled: true,
    },
  ],
}

async function stubApis(page: import('@playwright/test').Page) {
  await page.route('**/v1/definitions/**/summarize*', async (route) => {
    const post = route.request().postDataJSON() as { source?: string; extra?: string }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        kind: 'role',
        id: 'support',
        configured: true,
        model: 'stub-llm',
        summary: `LLM summary includes ${post?.extra || REQ42_INJECTED_FIXTURE} source=${post?.source || ''}`,
      }),
    })
  })
  await page.route('**/v1/definitions/**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        kind: 'role',
        id: 'support',
        title: 'Support',
        role: 'support',
        explanation: 'Support is Socratic.',
        source: 'ORIGINAL_SUPPORT_SOURCE',
        injected: {
          system_prompt: 'Socratic',
          tools: {},
          metadata: {},
          handoff: '',
          extra: REQ42_INJECTED_FIXTURE,
        },
        default_llm: { configured: true, model: 'stub-llm' },
      }),
    })
  })
  await page.route('**/v1/blueprints**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(BLUEPRINTS),
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

test('role badge opens the explained definition pane with stub LLM summary', async ({ page }) => {
  await stubApis(page)
  await page.addInitScript(() => {
    window.localStorage.setItem('swarm_hidden_agents', JSON.stringify([]))
  })
  await page.goto('/')

  const rail = page.getByRole('navigation', { name: 'Agent list' })
  await expect(rail.getByRole('link', { name: /Support/ })).toBeVisible()
  await rail.getByRole('button', { name: 'Open support settings' }).click()

  const sheet = page.getByRole('dialog', { name: 'Settings' })
  await expect(sheet).toBeVisible()
  await expect(sheet).toHaveClass(/modal-end/)
  await expect(sheet.getByRole('button', { name: 'Definition' })).toHaveClass(/menu-active/)
  const pane = sheet.locator('#os-definition-pane')
  await expect(pane).toHaveAttribute('data-definition-id', 'support')
  await expect(sheet.getByTestId('definition-explanation')).toContainText('Socratic')
  await expect(sheet.getByTestId('definition-summary')).toContainText(REQ42_INJECTED_FIXTURE)

  await sheet.getByRole('button', { name: /Edit code/ }).click()
  await sheet.getByLabel('Definition source').fill('UPDATED_SUPPORT_SOURCE')
  await sheet.getByRole('button', { name: /^Save$/ }).click()
  await sheet.getByRole('button', { name: /Re-summarise/ }).click()
  await expect(sheet.getByTestId('definition-summary')).toContainText('UPDATED_SUPPORT_SOURCE')
})
