import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, describe, expect, it, vi } from 'vitest'
import DefinitionPane from '../DefinitionPane'
import { ToastProvider } from '../DaisyUI'
import { REQ42_INJECTED_FIXTURE } from '../../lib/definitionExplain'

function renderPane(kind: 'role' | 'blueprint' | 'team' = 'role', id = 'gate') {
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

describe('DefinitionPane', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('shows the human explanation without an LLM', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse({
          kind: 'role',
          id: 'gate',
          title: 'Gate',
          role: 'gate',
          explanation: 'Gate is a YES/NO classifier.',
          source: 'GATE_INSTRUCTIONS = "YES or NO"',
          injected: {
            system_prompt: 'YES or NO',
            tools: {},
            metadata: { id: 'gate', role: 'gate' },
            handoff: 'as_tool',
            extra: 'runtime',
          },
          default_llm: { configured: false, model: null },
        }),
      ),
    )
    renderPane('role', 'gate')
    const pane = await screen.findByRole('region', { name: /gate/i })
    expect(pane).toHaveAttribute('data-definition-id', 'gate')
    expect(screen.getByTestId('definition-explanation').textContent).toMatch(/YES\/NO/)
    expect(screen.getByTestId('missing-model-hint').textContent).toMatch(/No default LLM/)
    expect(screen.getByRole('button', { name: /re-summarise/i })).toBeDisabled()
  })

  it('shows a stub/default LLM summary that includes the injected fixture string', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation(async (input: RequestInfo, init?: RequestInit) => {
        const url = String(input)
        if (url.includes('/summarize')) {
          const body = JSON.parse(String(init?.body || '{}')) as { extra?: string; source?: string }
          return jsonResponse({
            kind: 'role',
            id: 'gate',
            configured: true,
            model: 'stub-llm',
            summary: `LLM summary includes ${body.extra || REQ42_INJECTED_FIXTURE}`,
            injected_extra: body.extra,
          })
        }
        return jsonResponse({
          kind: 'role',
          id: 'gate',
          title: 'Gate',
          role: 'gate',
          explanation: 'Gate is a YES/NO classifier.',
          source: 'GATE_INSTRUCTIONS = "YES or NO"',
          injected: {
            system_prompt: 'YES or NO',
            tools: {},
            metadata: { id: 'gate', role: 'gate' },
            handoff: 'as_tool',
            extra: REQ42_INJECTED_FIXTURE,
          },
          default_llm: { configured: true, model: 'stub-llm' },
        })
      }),
    )
    renderPane('role', 'gate')
    await waitFor(() => {
      expect(screen.getByTestId('definition-summary').textContent).toContain(
        REQ42_INJECTED_FIXTURE,
      )
    })
  })

  it('edit + re-summarise updates the shown text', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation(async (input: RequestInfo, init?: RequestInit) => {
        const url = String(input)
        if (url.includes('/summarize')) {
          const body = JSON.parse(String(init?.body || '{}')) as { source?: string }
          return jsonResponse({
            kind: 'role',
            id: 'support',
            configured: true,
            model: 'stub-llm',
            summary: `Summarised source: ${body.source || ''}`,
          })
        }
        if (url.includes('/blueprints/custom/')) {
          return jsonResponse({ id: 'support', code: 'edited' }, 404)
        }
        return jsonResponse({
          kind: 'role',
          id: 'support',
          title: 'Support',
          role: 'support',
          explanation: 'Support is Socratic.',
          source: 'ORIGINAL_SOURCE_TEXT',
          injected: {
            system_prompt: 'Socratic',
            tools: {},
            metadata: {},
            handoff: '',
            extra: REQ42_INJECTED_FIXTURE,
          },
          default_llm: { configured: true, model: 'stub-llm' },
        })
      }),
    )
    renderPane('role', 'support')
    await waitFor(() => {
      expect(screen.getByTestId('definition-summary').textContent).toContain(
        'ORIGINAL_SOURCE_TEXT',
      )
    })

    fireEvent.click(screen.getByRole('button', { name: /edit code/i }))
    const editor = screen.getByLabelText('Definition source')
    fireEvent.change(editor, { target: { value: 'UPDATED_SOURCE_AFTER_EDIT' } })
    fireEvent.click(screen.getByRole('button', { name: /^Save$/ }))

    expect(await screen.findByText(/Source changed/i)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /re-summarise/i }))
    await waitFor(() => {
      expect(screen.getByTestId('definition-summary').textContent).toContain(
        'UPDATED_SOURCE_AFTER_EDIT',
      )
    })
  })
})
