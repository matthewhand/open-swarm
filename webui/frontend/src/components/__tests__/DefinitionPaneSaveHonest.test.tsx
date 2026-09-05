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

describe('REQ-211 / REQ-188A-2: Definition Save is honest', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('does not offer Edit/Save for a bundled role recipe', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation(async (input: RequestInfo) => {
        const url = String(input)
        if (url.includes('/source')) {
          return jsonResponse({
            id: 'support',
            files: [{ name: 'blueprint_support.py', path: 'blueprint_support.py' }],
            primary: 'blueprint_support.py',
            selected: 'blueprint_support.py',
            content: 'ORIGINAL_IMMUTABLE_SOURCE',
            editable: false,
            origin: 'bundled',
            readonly_reason: 'Bundled checkout recipe — not writable from Settings or the library.',
          })
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
      expect(screen.getByTestId('definition-readonly')).toHaveTextContent(
        /Bundled checkout recipe/i,
      )
    })
    expect(screen.queryByRole('button', { name: /edit code/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /^Save$/ })).not.toBeInTheDocument()
  })

  it('persists and shows success when PUT source succeeds', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation(async (input: RequestInfo, init?: RequestInit) => {
        const url = String(input)
        if (url.includes('/source')) {
          if (String(init?.method || 'GET') === 'PUT') {
            return jsonResponse({
              id: 'my-custom',
              files: [{ name: 'blueprint_my-custom.py', path: 'blueprint_my-custom.py' }],
              primary: 'blueprint_my-custom.py',
              selected: 'blueprint_my-custom.py',
              content: 'NEW_CODE',
              editable: true,
              origin: 'custom',
              readonly_reason: null,
            })
          }
          return jsonResponse({
            id: 'my-custom',
            files: [{ name: 'blueprint_my-custom.py', path: 'blueprint_my-custom.py' }],
            primary: 'blueprint_my-custom.py',
            selected: 'blueprint_my-custom.py',
            content: 'INITIAL_SOURCE',
            editable: true,
            origin: 'custom',
            readonly_reason: null,
          })
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
      expect(screen.getByText(/Saved\. Reloaded as the updated blueprint/i)).toBeInTheDocument()
    })
    expect(screen.getByText(/Source changed/i)).toBeInTheDocument()
  })
})
