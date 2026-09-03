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
  const configured: Array<Record<string, unknown>> = []
  await page.route('**/v1/remotes**', async (route) => {
    const url = route.request().url()
    const method = route.request().method()
    if (method === 'POST' && url.includes('/operate')) {
      const body = route.request().postDataJSON() as { op?: string }
      if (body?.op === 'send') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            remote: 'omb',
            op: 'send',
            ok: true,
            detail: 'started OpenMousBot turn via POST /api/bots/bot-1/messages',
          }),
        })
        return
      }
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          remote: 'omb',
          op: 'list',
          ok: true,
          detail: 'OpenMousBot listed 1 bot(s) via GET /api/bots',
          data: { bots: [{ id: 'bot-1' }] },
        }),
      })
      return
    }
    if (method === 'POST' && url.includes('/health')) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          remote: 'omb',
          ok: false,
          state: 'DOWN',
          detail: 'tcp 127.0.0.1:9 refused/timed out',
        }),
      })
      return
    }
    if (method === 'POST') {
      configured.splice(0, configured.length, {
        id: 'omb',
        label: 'OpenMousBot',
        title: 'OpenMousBot',
        base_url: 'http://127.0.0.1:9',
      })
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify(configured[0]),
      })
      return
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        object: 'list',
        kinds: [
          { id: 'hermes', label: 'Hermes' },
          { id: 'omb', label: 'OpenMousBot' },
          { id: 'rakazo', label: 'Rakazo' },
        ],
        data: configured,
      }),
    })
  })
  await page.route('**/health**', async (route) => {
    if (route.request().url().includes('/v1/remotes/')) {
      await route.fallback()
      return
    }
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

  await expect(page.getByRole('navigation', { name: 'Primary' })).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Open settings' })).toBeVisible()
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
  await expect(sections.getByRole('button', { name: 'Add remote' })).toBeVisible()
  await expect(sections.getByRole('button', { name: 'Hermes' })).toHaveCount(0)
  await expect(sections.getByRole('button', { name: 'OMB' })).toHaveCount(0)
  await expect(sections.getByRole('button', { name: 'OpenMousBot' })).toHaveCount(0)
  await expect(sections.getByRole('button', { name: 'Rakazo' })).toHaveCount(0)
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

test('Settings Remotes add OpenMousBot then health, list bots, send', async ({ page }) => {
  const jsErrors: string[] = []
  page.on('pageerror', (e) => jsErrors.push(e.message))
  await stubApis(page)
  await page.goto('/chat')
  await page.getByRole('button', { name: 'Open settings' }).click()
  const dialog = page.getByRole('dialog', { name: 'Settings' })
  await expect(dialog).toBeVisible()

  await page.getByRole('button', { name: 'Add remote' }).first().click()
  await expect(dialog.getByRole('heading', { name: 'Add remote' })).toBeVisible()
  await dialog.getByRole('combobox', { name: 'Kind' }).selectOption('omb')
  await expect(dialog.getByRole('combobox', { name: 'Kind' })).toContainText('OpenMousBot')
  await expect(dialog.getByRole('combobox', { name: 'Kind' })).not.toContainText('OMB')
  await dialog.getByRole('textbox', { name: 'Base URL' }).fill('http://127.0.0.1:9')
  await dialog.getByRole('textbox', { name: 'API key env (optional)' }).fill('OMB_API_KEY')
  await dialog.locator('form').getByRole('button', { name: 'Add remote' }).click()

  await expect(dialog.getByRole('button', { name: 'OpenMousBot' })).toBeVisible()
  await expect(dialog.getByRole('button', { name: 'OMB' })).toHaveCount(0)
  await expect(dialog.getByRole('heading', { name: 'OpenMousBot' })).toBeVisible()

  await dialog.getByRole('button', { name: 'Health' }).click()
  await expect(dialog.getByText('DOWN')).toBeVisible()
  await expect(dialog.getByText(/not a crash/i)).toBeVisible()

  await dialog.getByRole('button', { name: 'List bots' }).click()
  await expect(dialog.getByText('bot-1')).toBeVisible()

  await dialog.getByRole('textbox', { name: 'Bot id' }).fill('bot-1')
  await dialog.getByRole('textbox', { name: 'Message' }).fill('hello')
  await dialog.getByRole('button', { name: /^Send$/ }).click()
  await expect(dialog.getByText(/started OpenMousBot turn/i)).toBeVisible()
  await expect(dialog.getByText(/\bOMB\b/)).toHaveCount(0)

  expect(jsErrors, `uncaught JS errors: ${jsErrors.join(' | ')}`).toHaveLength(0)
})
