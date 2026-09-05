import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, describe, expect, it, vi } from 'vitest'
import SettingsSheet from '../SettingsSheet'
import { ToastProvider } from '../DaisyUI'

function renderSheet() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  const onClose = vi.fn()
  const view = render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <SettingsSheet
          isOpen={true}
          onClose={onClose}
          initialSection="llm-profiles"
        />
      </ToastProvider>
    </QueryClientProvider>,
  )
  return { ...view, onClose, client }
}

describe('LLMProfilesSaveGuards (REQ-188B-3)', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('disables Save button when /v1/llm-profiles/ returns 500 error', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        json: async () => ({ error: 'server error' }),
      } as Response),
    )

    renderSheet()

    expect(
      await screen.findByText(/Could not load configured profiles/i, undefined, { timeout: 4000 }),
    ).toBeInTheDocument()

    const saveButton = screen.getByRole('button', { name: 'Save LLM profiles' })
    expect(saveButton).toBeDisabled()
  })

  it('disables Save button when profiles catalog is empty', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          object: 'llm_profiles',
          profiles: [],
          default_llm_profile: 'default',
          default_is_auto: true,
          override_per_task: false,
          task_llm_profiles: {},
          auto_picks: {},
          warnings: [],
          routes: {},
          task_classes: ['orchestration', 'auxiliary', 'delegation'],
        }),
      } as Response),
    )

    renderSheet()

    expect(await screen.findByText(/No connected models yet/i)).toBeInTheDocument()

    const saveButton = screen.getByRole('button', { name: 'Save LLM profiles' })
    expect(saveButton).toBeDisabled()
  })

  it('enables Save button and sends PATCH with valid profiles', async () => {
    const fetchMock = vi.fn().mockImplementation(async (input: RequestInfo, init?: RequestInit) => {
      const url = String(input)
      const method = (init?.method || 'GET').toUpperCase()
      if (url.includes('/v1/llm-profiles') && method === 'PATCH') {
        const body = JSON.parse(String(init?.body || '{}'))
        return {
          ok: true,
          status: 200,
          json: async () => ({
            object: 'llm_profiles',
            profiles: [
              { id: 'gpt-5.6-terra', object: 'llm_profile', source: 'config', owned_by: 'openai' },
            ],
            default_llm_profile: body.default_llm_profile || 'gpt-5.6-terra',
            default_is_auto: false,
            override_per_task: Boolean(body.override_per_task),
            task_llm_profiles: body.task_llm_profiles || {},
            auto_picks: { default: 'gpt-5.6-terra' },
            warnings: [],
            routes: {},
            task_classes: ['orchestration', 'auxiliary', 'delegation'],
          }),
        } as Response
      }
      return {
        ok: true,
        status: 200,
        json: async () => ({
          object: 'llm_profiles',
          profiles: [
            { id: 'gpt-5.6-terra', object: 'llm_profile', source: 'config', owned_by: 'openai' },
          ],
          default_llm_profile: 'gpt-5.6-terra',
          default_is_auto: false,
          override_per_task: false,
          task_llm_profiles: {},
          auto_picks: { default: 'gpt-5.6-terra' },
          warnings: [],
          routes: {},
          task_classes: ['orchestration', 'auxiliary', 'delegation'],
        }),
      } as Response
    })
    vi.stubGlobal('fetch', fetchMock)

    renderSheet()

    expect(await screen.findByRole('list', { name: 'Configured LLM profiles' })).toBeInTheDocument()

    const saveButton = screen.getByRole('button', { name: 'Save LLM profiles' })
    expect(saveButton).toBeEnabled()

    fireEvent.click(saveButton)

    await waitFor(() => {
      expect(screen.getByText('LLM profiles saved')).toBeInTheDocument()
    })

    const patchCall = fetchMock.mock.calls.find(
      (call) => String(call[0]).includes('/v1/llm-profiles') && call[1]?.method === 'PATCH',
    )
    expect(patchCall).toBeTruthy()
    expect(JSON.parse(String(patchCall?.[1]?.body))).toMatchObject({
      default_llm_profile: 'gpt-5.6-terra',
      override_per_task: false,
    })
  })
})
