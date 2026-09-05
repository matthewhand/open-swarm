import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, describe, expect, it, vi } from 'vitest'
import DefinitionPane from '../DefinitionPane'
import { ToastProvider } from '../DaisyUI'

function renderPane(definitionId = '', kind: 'role' | 'blueprint' | 'team' = 'role') {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <DefinitionPane kind={kind} definitionId={definitionId} />
      </ToastProvider>
    </QueryClientProvider>,
  )
}

describe('REQ-188A-1: Settings Definition — empty untitled pane needs identity or honest empty', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('renders honest empty state with no fake worker recipe and no Save/Edit button when definitionId is empty', () => {
    renderPane('')

    expect(screen.getByTestId('definition-empty')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Definition' })).toBeInTheDocument()
    expect(screen.getByText('No definition selected.')).toBeInTheDocument()
    expect(
      screen.getByText(/Select an agent, role, or team from the sidebar/i),
    ).toBeInTheDocument()

    // Must not show fake worker blueprint recipe
    expect(screen.queryByText(/This is a worker blueprint/i)).not.toBeInTheDocument()
    expect(screen.queryByTestId('definition-explanation')).not.toBeInTheDocument()

    // Must not show Edit code or Save button
    expect(screen.queryByRole('button', { name: /edit code/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /^Save$/i })).not.toBeInTheDocument()
  })

  it('renders normal definition view when a valid definitionId is provided', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          kind: 'role',
          id: 'gate',
          title: 'Gate',
          role: 'gate',
          explanation: 'Gate is a classifier.',
          source: 'GATE_SOURCE',
          injected: {
            system_prompt: 'Gate prompt',
            tools: {},
            metadata: {},
            handoff: '',
            extra: '',
          },
          default_llm: { configured: false, model: null },
        }),
      } as Response),
    )

    renderPane('gate', 'role')

    expect(screen.queryByTestId('definition-empty')).not.toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: 'Gate' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /edit code/i })).not.toBeInTheDocument()
    expect(screen.getByTestId('definition-readonly')).toBeInTheDocument()
  })
})
