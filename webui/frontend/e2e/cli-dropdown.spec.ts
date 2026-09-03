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
      id: 'cli_agent',
      object: 'blueprint',
      name: 'CLI Agent',
      description: 'Single CLI',
      abbreviation: null,
      required_mcp_servers: [],
      tags: ['cli'],
      installed: true,
      compiled: true,
    },
  ],
}

const CLI_AGENTS = {
  clis: ['claude', 'codex', 'gemini', 'grok', 'opencode'],
  installed: ['grok'],
  configured: ['grok'],
  native_consensus: {},
  catalog: {},
}

async function stubChatApis(page: import('@playwright/test').Page) {
  await page.route('**/v1/blueprints**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(BLUEPRINTS),
    })
  })
  await page.route('**/v1/cli-agents**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(CLI_AGENTS),
    })
  })
}

test('CLI-agent chat lists discovered CLIs and Manage Cli, not blueprints', async ({
  page,
}) => {
  await stubChatApis(page)
  await page.goto('/chat?blueprint=cli_agent')

  const select = page.getByRole('combobox', { name: 'CLI' })
  await expect(select).toBeVisible()
  await expect(page.getByRole('combobox', { name: 'Blueprint' })).toHaveCount(0)
  await expect(page.getByText('Blueprint', { exact: true })).toHaveCount(0)
  await expect(page.getByRole('option', { name: 'Codey' })).toHaveCount(0)

  const labels = await select.locator('option').allTextContents()
  expect(labels).toContain('grok')
  expect(labels.at(-1)?.trim()).toBe('Manage Cli')
  expect(labels.some((label) => label.includes('Codey'))).toBe(false)
})

test('blueprint-mode chat still lists blueprints', async ({ page }) => {
  await stubChatApis(page)
  await page.goto('/chat?blueprint=codey')

  const select = page.getByRole('combobox', { name: 'Blueprint' })
  await expect(select).toBeVisible()
  await expect(page.getByText('Blueprint', { exact: true })).toBeVisible()
  await expect(page.getByRole('combobox', { name: 'CLI' })).toHaveCount(0)
  await expect(select).toHaveValue('codey')
  await expect(page.getByRole('option', { name: 'Codey' })).toHaveCount(1)
  await expect(page.getByRole('option', { name: 'Manage Cli' })).toHaveCount(0)
})
