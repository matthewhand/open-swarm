import { test, expect, type Page } from '@playwright/test'

// E2E for the Builder config panels. The preview build has no backend, so we
// route-mock the API — making the test deterministic and backend-independent.

const CONFIG_OPTIONS = {
  skills: [
    { name: 'conventional-commit', description: 'Writes a commit message.', assets: [], instructions: 'Output one Conventional Commits message.' },
    { name: 'counting-lines', description: 'Counts non-blank lines.', assets: ['count.py'], instructions: 'Run count.py and report the number.' },
  ],
  inference: {
    traits: ['intelligence', 'speed', 'cost'],
    cli_traits: {
      claude: { intelligence: 0.95, speed: 0.55, cost: 0.35 },
      gemini: { intelligence: 0.6, speed: 0.92, cost: 0.9 },
    },
    model_traits: { 'claude-opus-4-8': { intelligence: 0.98, speed: 0.45, cost: 0.2 } },
    model_flags: { gemini: '-m', claude: '--model' },
  },
  tools: {
    capabilities: ['web_search', 'browser'],
    mcp_catalog: [
      { name: 'duckduckgo', provides: ['web_search'], command: 'uvx', args: ['duckduckgo-mcp-server'], needs_auth: false, auth_env: [], note: '' },
      { name: 'brave-search', provides: ['web_search'], command: 'npx', args: [], needs_auth: true, auth_env: ['BRAVE_API_KEY'], note: '' },
      { name: 'playwright', provides: ['browser'], command: 'npx', args: ['-y', '@playwright/mcp@latest'], needs_auth: false, auth_env: [], note: '' },
    ],
  },
}

async function mockApi(page: Page) {
  await page.route('**/v1/config-options/', (r) => r.fulfill({ json: CONFIG_OPTIONS }))
  await page.route('**/v1/blueprints/', (r) =>
    r.fulfill({ json: { data: [{ id: 'cli_agent', name: 'cli_agent', description: '', tags: [] }] } }),
  )
  await page.route('**/v1/cli-agents/', (r) =>
    r.fulfill({ json: { clis: ['grok'], native_consensus: {}, catalog: {} } }),
  )
  await page.route('**/v1/blueprints/cli_agent/source*', (r) =>
    r.fulfill({ json: { id: 'cli_agent', primary: 'x.py', selected: 'x.py', files: [{ name: 'x.py', path: 'x.py' }], content: '# x' } }),
  )
}

test.beforeEach(async ({ page }) => {
  await mockApi(page)
  await page.goto('/builder')
})

test('inference profile panel resolves to a CLI', async ({ page }) => {
  const panel = page.locator('.card', { has: page.getByRole('heading', { name: 'Inference profile' }) })
  await expect(panel).toBeVisible()
  // Intelligence is active by default -> resolves to the smartest backend.
  await expect(panel.getByText('Resolves to')).toBeVisible()
  await expect(panel.getByText('claude', { exact: true })).toBeVisible()
})

test('tool capabilities panel resolves web_search to the non-auth duckduckgo', async ({ page }) => {
  const panel = page.locator('.card', { has: page.getByRole('heading', { name: 'Tool capabilities' }) })
  await expect(panel).toBeVisible()
  await panel.getByRole('group', { name: 'web_search requirement' }).getByRole('button', { name: 'mandatory' }).click()
  await panel.getByLabel('Add duckduckgo').check()
  await expect(panel.getByText('Resolves to')).toBeVisible()
  // web_search -> duckduckgo (non-auth preferred)
  await expect(panel.locator('text=/web_search/').first()).toBeVisible()
  await expect(panel.getByText('duckduckgo').last()).toBeVisible()
})

test('trait editor emits cli_agents config and resolves the sample', async ({ page }) => {
  const panel = page.locator('.card', { has: page.getByRole('heading', { name: 'Tune backend traits' }) })
  await expect(panel).toBeVisible()
  // Seeded per-model override + live sample resolution to the smartest model.
  await expect(panel.getByLabel('cli_agents traits config')).toContainText('"models"')
  await expect(panel.getByText(/claude/).first()).toBeVisible()
})

test('skills panel emits a request snippet on selection', async ({ page }) => {
  const panel = page.locator('.card', { has: page.getByRole('heading', { name: 'Skills' }) })
  await expect(panel).toBeVisible()
  await panel.getByRole('button', { name: /counting-lines/ }).click()
  await expect(panel.getByLabel('Skill request snippet')).toContainText('"skill": "counting-lines"')
  // SKILL.md preview renders the full instructions on select.
  await expect(panel.getByLabel('counting-lines SKILL.md instructions')).toContainText('Run count.py')
})
