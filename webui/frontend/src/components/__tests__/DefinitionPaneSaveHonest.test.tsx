import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, describe, expect, it, vi } from 'vitest'
import DefinitionPane from '../DefinitionPane'
import { ToastProvider } from '../DaisyUI'

function renderPane(kind: 'role' | 'blueprint' | 'team' = 'role', id = 'support') {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <DefinitionPane kind={kind} definitionId={id} />
      </ToastProvider>
    </QueryClientProvider>,
  )
}

function jsonResponse(body: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response
}

describe('REQ-188A-2: Definition Save must not swallow 404 as draft stored', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('fails honestly on 404 when saving blueprint/role without claiming draft stored', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation(async (input: RequestInfo) => {
        const url = String(input)
        if (url.includes('/blueprints/custom/')) {
          return {
            ok: false,
            status: 404,
            statusText: 'Not Found',
            json: async () => ({ error: 'Custom blueprint not found' }),
          } as Response
        }
        return jsonResponse({
          kind: 'role',
          id: 'support',
          title: 'Support',
          role: 'support',
          explanation: 'Support role explanation.',
          source: 'ORIGINAL_IMMUTABLE_SOURCE',
          injected: {
            system_prompt: 'Support prompt',
            tools: {},
            metadata: {},
            handoff: '',
            extra: '',
          },
          default_llm: { configured: true, model: 'stub-llm' },
        })
      }),
    )

    renderPane('role', 'support')

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /edit code/i })).toBeInTheDocument()
    })

    fireEvent.click(screen.getByRole('button', { name: /edit code/i }))
    const editor = screen.getByLabelText('Definition source')
    fireEvent.change(editor, { target: { value: 'TRYING_TO_OVERWRITE_ROLE' } })

    fireEvent.click(screen.getByRole('button', { name: /^Save$/ }))

    // Verify it does NOT claim draft stored
    await waitFor(() => {
      expect(screen.queryByText(/Draft stored/i)).not.toBeInTheDocument()
    })

    // Verify honest failure message is shown
    expect(screen.getByText(/Failed to save definition/i)).toBeInTheDocument()
    expect(screen.getByText(/Custom blueprint not found/i)).toBeInTheDocument()

    // Verify "Source changed" notice is NOT shown
    expect(screen.queryByText(/Source changed/i)).not.toBeInTheDocument()
  })

  it('persists and shows success when PATCH succeeds with 200', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation(async (input: RequestInfo) => {
        const url = String(input)
        if (url.includes('/blueprints/custom/')) {
          return jsonResponse({ id: 'my-custom', code: 'NEW_CODE' }, 200)
        }
        return jsonResponse({
          kind: 'blueprint',
          id: 'my-custom',
          title: 'My Custom Blueprint',
          role: 'custom',
          explanation: 'Custom blueprint explanation.',
          source: 'INITIAL_SOURCE',
          injected: {
            system_prompt: 'Custom prompt',
            tools: {},
            metadata: {},
            handoff: '',
            extra: '',
          },
          default_llm: { configured: true, model: 'stub-llm' },
        })
      }),
    )

    renderPane('blueprint', 'my-custom')

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /edit code/i })).toBeInTheDocument()
    })

    fireEvent.click(screen.getByRole('button', { name: /edit code/i }))
    const editor = screen.getByLabelText('Definition source')
    fireEvent.change(editor, { target: { value: 'NEW_CODE' } })

    fireEvent.click(screen.getByRole('button', { name: /^Save$/ }))

    await waitFor(() => {
      expect(screen.getByText(/Saved\. Re-summarise to refresh/i)).toBeInTheDocument()
    })
    expect(screen.getByText(/Source changed/i)).toBeInTheDocument()
  })
})
