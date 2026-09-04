import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import AddAgentWizard from '../AddAgentWizard'
import * as api from '../../lib/api'
import { OPENMOUSBOT_LABEL } from '../../lib/remotesCatalog'

function renderWizard(props: Partial<Parameters<typeof AddAgentWizard>[0]> = {}) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
  const onClose = vi.fn()
  const onCreated = vi.fn()

  const view = render(
    <QueryClientProvider client={queryClient}>
      <AddAgentWizard
        isOpen={true}
        onClose={onClose}
        onCreated={onCreated}
        {...props}
      />
    </QueryClientProvider>,
  )

  return { ...view, onClose, onCreated, queryClient }
}

describe('AddAgentWizard (REQ-109)', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('renders three agent kinds on step 1 with OpenMousBot copy for remote', () => {
    renderWizard()

    expect(screen.getByTestId('add-agent-wizard')).toBeInTheDocument()
    expect(screen.getByTestId('kind-option-cli')).toBeInTheDocument()
    expect(screen.getByTestId('kind-option-api')).toBeInTheDocument()
    expect(screen.getByTestId('kind-option-remote')).toBeInTheDocument()

    // Must use OpenMousBot copy (not OMB)
    expect(screen.getByText(new RegExp(OPENMOUSBOT_LABEL, 'i'))).toBeInTheDocument()
    expect(screen.queryByText(/^OMB$/)).not.toBeInTheDocument()
  })

  it('closes wizard when Cancel button is clicked without creating', () => {
    const { onClose, onCreated } = renderWizard()

    // Select CLI kind to see form
    fireEvent.click(screen.getByTestId('kind-option-cli'))
    expect(screen.getByTestId('add-agent-form')).toBeInTheDocument()

    // Click Cancel
    fireEvent.click(screen.getByRole('button', { name: /cancel/i }))
    expect(onClose).toHaveBeenCalledTimes(1)
    expect(onCreated).not.toHaveBeenCalled()
  })

  it('creates a CLI agent on happy-path submit', async () => {
    const createSpy = vi.spyOn(api, 'createCustomBlueprint').mockResolvedValue({
      id: 'custom_cli_agent',
      name: 'My CLI Tool',
      description: 'CLI: custom-tool',
      category: 'cli',
      tags: ['cli'],
      requirements: '',
      code: '# CLI agent: My CLI Tool\n',
      required_mcp_servers: [],
      env_vars: [],
    })

    const { onCreated, onClose } = renderWizard()

    // Select CLI
    fireEvent.click(screen.getByTestId('kind-option-cli'))
    expect(screen.getByTestId('input-cli-name')).toBeInTheDocument()

    // Fill in inputs
    fireEvent.change(screen.getByTestId('input-cli-name'), {
      target: { value: 'My CLI Tool' },
    })
    fireEvent.change(screen.getByTestId('input-cli-command'), {
      target: { value: 'custom-tool' },
    })

    // Submit
    fireEvent.click(screen.getByTestId('submit-create-agent'))

    await waitFor(() => {
      expect(createSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          name: 'My CLI Tool',
          category: 'cli',
        }),
      )
      expect(onCreated).toHaveBeenCalledWith({
        id: 'custom_cli_agent',
        name: 'My CLI Tool',
        kind: 'cli',
      })
      expect(onClose).toHaveBeenCalled()
    })
  })

  it('creates an API agent on happy-path submit', async () => {
    const createSpy = vi.spyOn(api, 'createCustomBlueprint').mockResolvedValue({
      id: 'api_researcher',
      name: 'Researcher',
      description: 'Deep market research',
      category: 'ai_assistants',
      tags: ['api'],
      requirements: '',
      code: 'You are a researcher',
      required_mcp_servers: [],
      env_vars: [],
    })

    const { onCreated, onClose } = renderWizard()

    // Select API
    fireEvent.click(screen.getByTestId('kind-option-api'))
    expect(screen.getByTestId('input-api-name')).toBeInTheDocument()

    // Fill in inputs
    fireEvent.change(screen.getByTestId('input-api-name'), {
      target: { value: 'Researcher' },
    })
    fireEvent.change(screen.getByTestId('input-api-prompt'), {
      target: { value: 'You are a researcher' },
    })

    // Submit
    fireEvent.click(screen.getByTestId('submit-create-agent'))

    await waitFor(() => {
      expect(createSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          name: 'Researcher',
          category: 'ai_assistants',
        }),
      )
      expect(onCreated).toHaveBeenCalledWith({
        id: 'api_researcher',
        name: 'Researcher',
        kind: 'api',
      })
      expect(onClose).toHaveBeenCalled()
    })
  })

  it('connects a Remote agent on happy-path submit', async () => {
    const createRemoteSpy = vi.spyOn(api, 'createRemote').mockResolvedValue({
      id: 'omb-remote-1',
      kind: 'omb',
      base_url: 'http://localhost:8000',
      agents: [],
      configured: true,
      created: 123456,
      object: 'remote',
    } as any)

    const { onCreated, onClose } = renderWizard()

    // Select Remote
    fireEvent.click(screen.getByTestId('kind-option-remote'))
    expect(screen.getByTestId('input-remote-url')).toBeInTheDocument()

    // Fill in URL
    fireEvent.change(screen.getByTestId('input-remote-url'), {
      target: { value: 'http://localhost:8000' },
    })

    // Submit
    fireEvent.click(screen.getByTestId('submit-create-agent'))

    await waitFor(() => {
      expect(createRemoteSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          kind: 'omb',
          base_url: 'http://localhost:8000',
        }),
      )
      expect(onCreated).toHaveBeenCalledWith({
        id: 'omb-remote-1',
        name: OPENMOUSBOT_LABEL,
        kind: 'remote',
      })
      expect(onClose).toHaveBeenCalled()
    })
  })
})
