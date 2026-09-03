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
  await page.route('**/v1/remotes**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        object: 'list',
        data: [],
        kinds: [
          {
            id: 'rakazo',
            label: 'Rakazo',
            fields: ['base_url', 'ui_url', 'api_key_env', 'session_cookie_env'],
            ops: ['health', 'list', 'send'],
          },
        ],
      }),
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
  await expect(sections.getByRole('button', { name: /add remote/i })).toBeVisible()
  await expect(sections.getByRole('button', { name: 'Hermes' })).toHaveCount(0)
  await expect(sections.getByRole('button', { name: 'OMB' })).toHaveCount(0)
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

test('adds a Rakazo remote then health, list (auth-needed), and send', async ({ page }) => {
  const jsErrors: string[] = []
  page.on('pageerror', (e) => jsErrors.push(e.message))

  const kind = {
    id: 'rakazo',
    label: 'Rakazo',
    fields: ['base_url', 'ui_url', 'api_key_env', 'session_cookie_env'],
    ops: ['health', 'list', 'send'],
  }
  const remote = {
    id: 'rakazo',
    kind: 'rakazo',
    title: 'Rakazo',
    label: 'Rakazo',
    host_label: '',
    base_url: 'http://127.0.0.1:9',
    ui_url: 'http://127.0.0.1:9',
    api_key_env: 'RAKAZO_API_KEY',
    session_cookie_env: 'RAKAZO_SESSION_COOKIE',
    api_key_set: false,
    cookie_set: false,
    configured: true,
    notes: '',
    source: 'config',
  }
  let configured = false

  await stubApis(page)
  await page.unroute('**/v1/remotes**')
  await page.route('**/v1/remotes**', async (route) => {
    const req = route.request()
    const url = req.url()
    const method = req.method()
    if (url.includes('/health') && method === 'POST') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          remote: 'rakazo',
          ok: true,
          state: 'UP',
          detail: 'tcp 1ms · http 200 on /health',
          http_status: 200,
        }),
      })
      return
    }
    if (url.includes('/operate') && method === 'POST') {
      const body = req.postDataJSON() as { op?: string }
      if (body.op === 'send') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            remote: 'rakazo',
            op: 'send',
            ok: true,
            detail: 'sent Rakazo thread via POST /rpc/threads/send (bot bot-9)',
            http_status: 200,
          }),
        })
        return
      }
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          remote: 'rakazo',
          op: 'list',
          ok: false,
          detail: 'Rakazo /rpc/bots/list requires a Better Auth session.',
          http_status: 401,
          gap: 'rakazo_rpc_requires_better_auth_session',
        }),
      })
      return
    }
    if (method === 'POST' && url.endsWith('/v1/remotes/')) {
      configured = true
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(remote),
      })
      return
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        object: 'list',
        data: configured ? [remote] : [],
        kinds: [kind],
      }),
    })
  })

  await page.goto('/chat')
  await page.getByRole('button', { name: 'Open settings' }).click()
  const dialog = page.getByRole('dialog', { name: 'Settings' })
  await expect(dialog).toBeVisible()
  await dialog.getByRole('button', { name: /add remote/i }).click()
  await expect(dialog.getByRole('heading', { name: 'Add remote' })).toBeVisible()
  await dialog.getByRole('textbox', { name: 'API base URL' }).fill('http://127.0.0.1:9')
  await dialog.getByRole('textbox', { name: 'UI URL (optional)' }).fill('http://127.0.0.1:9')
  await dialog.getByRole('textbox', { name: 'API key env' }).fill('RAKAZO_API_KEY')
  await dialog.getByRole('textbox', { name: 'Session cookie env' }).fill('RAKAZO_SESSION_COOKIE')
  await dialog.getByRole('button', { name: 'Save remote' }).click()

  await expect(dialog.getByRole('heading', { name: 'Rakazo' })).toBeVisible()
  await expect(dialog.getByText('RAKAZO_API_KEY')).toBeVisible()
  await expect(dialog.getByText(/sid=/i)).toHaveCount(0)

  await dialog.getByRole('button', { name: 'Check health' }).click()
  await expect(dialog.getByText(/Health UP/i)).toBeVisible()
  await dialog.getByRole('button', { name: 'List bots' }).click()
  await expect(dialog.getByText('rakazo_rpc_requires_better_auth_session')).toBeVisible()
  await dialog.getByRole('textbox', { name: 'Bot id' }).fill('bot-9')
  await dialog.getByRole('textbox', { name: 'Message' }).fill('go')
  await dialog.getByRole('button', { name: /^Send$/ }).click()
  await expect(dialog.getByText(/sent Rakazo thread/i)).toBeVisible()

  expect(jsErrors, `uncaught JS errors: ${jsErrors.join(' | ')}`).toHaveLength(0)
})
