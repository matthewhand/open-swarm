import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, describe, expect, it, vi } from 'vitest'
import AgentEditor from '../AgentEditor'
import { ToastProvider } from '../DaisyUI'
import { resetGeneratedAvatars, loadGeneratedAvatar } from '../../lib/agentAvatars'

const catalog = [
  {
    id: 'codey',
    object: 'blueprint' as const,
    name: 'Codey',
    description: 'Code assistant',
    abbreviation: null,
    required_mcp_servers: [] as string[],
    tags: [] as string[],
    installed: true,
    compiled: true,
  },
]

function stubFetch(options: { configured: boolean }) {
  let generatePayload: Record<string, unknown> | null = null
  const fetchMock = vi.fn().mockImplementation(async (input: RequestInfo, init?: RequestInit) => {
    const url = String(input)
    if (url.includes('/v1/image-gen/')) {
      return {
        ok: true,
        status: 200,
        json: async () => ({
          object: 'image_gen',
          configured: options.configured,
          base_url: options.configured ? 'http://127.0.0.1:9' : '',
          model: options.configured ? 'still-1' : '',
          api_key_env: options.configured ? 'IMAGE_GEN_API_KEY' : '',
          status: options.configured ? 'ok' : 'off',
          detail: options.configured
            ? 'Image generation endpoint answered HTTP 200.'
            : 'Image generation is off. No host is used until you set a base URL.',
          avatars: {},
        }),
      } as Response
    }
    if (url.includes('/avatar/generate') && init?.method === 'POST') {
      generatePayload = JSON.parse(String(init.body))
      return {
        ok: true,
        status: 200,
        json: async () => ({
          object: 'agent_avatar',
          agent_id: 'codey',
          avatar_path: '/avatars/codey_still.png',
          still: true,
          prompt: generatePayload?.prompt,
        }),
      } as Response
    }
    if (url.includes('/v1/models')) {
      return {
        ok: true,
        status: 200,
        json: async () => ({ object: 'list', data: [] }),
      } as Response
    }
    return {
      ok: true,
      status: 200,
      json: async () => ({ object: 'list', data: catalog }),
    } as Response
  })
  vi.stubGlobal('fetch', fetchMock)
  return {
    fetchMock,
    getGeneratePayload: () => generatePayload,
  }
}

function renderEditor() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <AgentEditor isOpen={true} onClose={vi.fn()} agentId="codey" />
      </ToastProvider>
    </QueryClientProvider>,
  )
}

describe('AgentEditor Generate avatar (REQ-83)', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    resetGeneratedAvatars()
  })

  it('disables Generate when image-gen is unset and points at Settings', async () => {
    const { fetchMock } = stubFetch({ configured: false })
    renderEditor()
    const dialog = await screen.findByRole('dialog', { name: /Edit /i, hidden: true })
    const generate = await within(dialog).findByRole('button', { name: 'Generate avatar' })
    expect(generate).toBeDisabled()
    expect(within(dialog).getByTestId('generate-avatar-disabled-hint')).toHaveTextContent(
      /Settings → Image generation/i,
    )
    expect(
      fetchMock.mock.calls.some(([input, init]) => {
        const url = String(input)
        return url.includes('/v1/images/generations') || (init as RequestInit | undefined)?.method === 'POST'
      }),
    ).toBe(false)
  })

  it('posts a still prompt and stores the generated avatar path', async () => {
    const { getGeneratePayload } = stubFetch({ configured: true })
    renderEditor()
    const dialog = await screen.findByRole('dialog', { name: /Edit /i, hidden: true })
    const generate = await within(dialog).findByRole('button', { name: 'Generate avatar' })
    await waitFor(() => {
      expect(generate).not.toBeDisabled()
    })
    fireEvent.click(generate)
    await waitFor(() => {
      expect(getGeneratePayload()).not.toBeNull()
    })
    expect(String(getGeneratePayload()?.prompt || '')).toMatch(/still|Codey/i)
    expect(loadGeneratedAvatar('codey')).toBe('/avatars/codey_still.png')
  })
})
