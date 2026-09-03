import { test, expect } from '@playwright/test'

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
    {
      id: 'stewie',
      object: 'blueprint',
      name: 'Stewie',
      description: 'Helpful agent',
      abbreviation: null,
      required_mcp_servers: [],
      tags: [],
      installed: true,
      compiled: true,
    },
  ],
}

async function stubAgentApis(page: import('@playwright/test').Page) {
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

test('dashboard shows four large chrome action cards', async ({ page }) => {
  const jsErrors: string[] = []
  page.on('pageerror', (e) => jsErrors.push(e.message))
  await stubAgentApis(page)
  await page.goto('/')

  const launch = page.getByRole('link', { name: /Launch Team/i })
  await expect(launch).toBeVisible()
  await expect(page.getByRole('link', { name: /Browse Blueprints/i })).toBeVisible()
  await expect(page.getByRole('link', { name: /Manage Teams/i })).toBeVisible()
  await expect(page.getByRole('link', { name: /Settings/ }).first()).toBeVisible()

  await expect(launch).toHaveClass(/os-action-card/)
  const box = await launch.boundingBox()
  expect(box, 'Launch Team card should be a large tile').toBeTruthy()
  expect(box!.height).toBeGreaterThan(120)
  expect(box!.width).toBeGreaterThan(240)

  const root = page.locator('[data-theme]').first()
  await expect(root).toHaveAttribute('data-theme', 'dark')
  expect(jsErrors, `uncaught JS errors: ${jsErrors.join(' | ')}`).toHaveLength(0)
})

test('Chat nav and /agents stay on /chat with composer', async ({ page }) => {
  const jsErrors: string[] = []
  page.on('pageerror', (e) => jsErrors.push(e.message))
  await stubAgentApis(page)

  await page.goto('/')
  await page.getByRole('navigation', { name: 'Primary' }).getByRole('link', { name: 'Chat' }).click()
  await expect(page).toHaveURL(/\/chat\/?(\?|$)/)
  await expect(page.getByRole('textbox', { name: 'Chat message' })).toBeVisible()
  await expect(page.getByLabel('Connection status')).toBeVisible()

  await page.goto('/agents?blueprint=codey')
  await expect(page).toHaveURL(/\/chat\/?\?blueprint=codey/)
  await expect(page.getByRole('textbox', { name: 'Chat message' })).toBeVisible()
  expect(jsErrors, `uncaught JS errors: ${jsErrors.join(' | ')}`).toHaveLength(0)
})

test('right-click hide from sidebar persists across reload; unhide restores', async ({ page }) => {
  const jsErrors: string[] = []
  page.on('pageerror', (e) => jsErrors.push(e.message))
  await stubAgentApis(page)
  await page.goto('/chat')

  const list = page.getByRole('navigation', { name: 'Agent list' })
  const codey = list.getByRole('link', { name: /Codey/ })
  await expect(codey).toBeVisible()
  await expect(list.getByRole('link', { name: /Stewie/ })).toBeVisible()

  await codey.click({ button: 'right' })
  await page.getByRole('menuitem', { name: /Hide from sidebar/i }).click()
  await expect(list.getByRole('link', { name: /Codey/ })).toHaveCount(0)
  await expect(list.getByRole('link', { name: /Stewie/ })).toBeVisible()

  await expect
    .poll(() => page.evaluate(() => localStorage.getItem('swarm_hidden_agents')))
    .toBe(JSON.stringify(['codey']))

  await page.reload()
  await expect(list.getByRole('link', { name: /Codey/ })).toHaveCount(0)
  await expect(list.getByRole('link', { name: /Stewie/ })).toBeVisible()

  await page.getByRole('button', { name: /Hidden/i }).click()
  await expect(list.getByRole('link', { name: /Codey/ })).toBeVisible()
  await page.getByRole('button', { name: /Unhide Codey/i }).click()
  await expect(page.getByRole('button', { name: /Hidden/i })).toHaveCount(0)
  await expect(list.getByRole('link', { name: /Codey/ })).toBeVisible()
  expect(jsErrors, `uncaught JS errors: ${jsErrors.join(' | ')}`).toHaveLength(0)
})
