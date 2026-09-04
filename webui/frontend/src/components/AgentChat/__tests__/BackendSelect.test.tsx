import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, within } from '@testing-library/react'
import { BackendSelect, backendRouteParams } from '../BackendSelect'
import type { Agent } from '../../../types/agent'

const grokAgent: Agent = {
  agent_id: 'grok',
  name: 'Grok',
  specialty: 'CLI',
  color: '#22c55e',
  icon: '⚡',
  type: 'specialist',
  kind: 'cli',
  agent_type: 'cli',
  cli: 'grok',
}

const clis = [
  {
    name: 'grok',
    executable: 'grok',
    installed: true,
    model_flag: '-m',
    models: ['grok-4.6', 'grok-4.5'],
  },
]

describe('CLI model dropdown', () => {
  it('includes cli_model on route params only when set', () => {
    expect(backendRouteParams('cli:grok')).toEqual({ backend: 'cli', cli: 'grok' })
    expect(backendRouteParams('cli:grok', undefined, 'grok-4.5')).toEqual({
      backend: 'cli',
      cli: 'grok',
      cli_model: 'grok-4.5',
    })
  })

  it('shows a blueprint dropdown only for API agents', () => {
    const apiAgent: Agent = { ...grokAgent, agent_id: 'router', kind: 'api', agent_type: 'api', cli: undefined }
    render(
      <BackendSelect
        agent={apiAgent}
        value="api"
        clis={clis}
        onChange={() => undefined}
        llmProfiles={[{ name: 'auxiliary', provider: 'openai', model: 'aux', base_url: '', description: '' }]}
        llmValue=""
        defaultLlm="auxiliary"
        onLlmChange={() => undefined}
        blueprints={[{ id: 'codey', name: 'Codey' }]}
        blueprintValue=""
        onBlueprintChange={() => undefined}
      />,
    )
    expect(screen.getByLabelText('Blueprint')).toBeInTheDocument()
    expect(screen.getByLabelText('LLM profile')).toBeInTheDocument()
    expect(screen.queryByLabelText('CLI model')).not.toBeInTheDocument()
    expect(screen.queryByRole('option', { name: 'CLI · grok' })).not.toBeInTheDocument()
  })

  it('shows CLI model only for CLI agents', () => {
    render(
      <BackendSelect
        agent={grokAgent}
        value="cli:grok"
        clis={clis}
        onChange={() => undefined}
        llmProfiles={[{ name: 'auxiliary', provider: 'openai', model: 'aux', base_url: '', description: '' }]}
        llmValue=""
        defaultLlm="auxiliary"
        onLlmChange={() => undefined}
        cliModel=""
        onCliModelChange={() => undefined}
      />,
    )
    expect(screen.getByLabelText('CLI model')).toBeInTheDocument()
    expect(screen.queryByLabelText('LLM profile')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Blueprint')).not.toBeInTheDocument()
  })

  it('shows remote members and puts remote_id on route params', () => {
    const omb: Agent = {
      ...grokAgent,
      agent_id: 'openmausbot',
      name: 'OpenMausBot',
      kind: 'remote',
      agent_type: 'remote',
      framework: 'openmausbot',
      cli: undefined,
    }
    const onRemote = vi.fn()
    render(
      <BackendSelect
        agent={omb}
        value="remote"
        clis={clis}
        onChange={() => undefined}
        remoteMembers={[
          { id: 'night', name: 'Night editor' },
          { id: 'cos-1', name: 'Chief of Staff' },
        ]}
        remoteMember="cos-1"
        onRemoteMemberChange={onRemote}
      />,
    )
    const select = screen.getByLabelText('Remote member')
    expect(select).toHaveValue('cos-1')
    fireEvent.change(select, { target: { value: 'night' } })
    expect(onRemote).toHaveBeenCalledWith('night')
    expect(backendRouteParams('remote', undefined, undefined, 'cos-1')).toEqual({
      backend: 'remote',
      remote_id: 'cos-1',
      target: 'cos-1',
      model: 'cos-1',
    })
    expect(backendRouteParams('remote', undefined, undefined, 'cos-1', undefined, 'hermes')).toEqual({
      backend: 'remote',
      remote_id: 'cos-1',
      target: 'cos-1',
      model: 'cos-1',
      framework: 'hermes',
    })
  })

  it('always offers grok and agy on the CLI dropdown', () => {
    render(
      <BackendSelect
        agent={grokAgent}
        value="cli:grok"
        clis={clis}
        onChange={() => undefined}
        cliModel=""
        onCliModelChange={() => undefined}
      />,
    )
    const select = screen.getByLabelText('Model backend')
    expect(within(select).getByRole('option', { name: 'CLI · grok' })).toBeInTheDocument()
    expect(within(select).getByRole('option', { name: 'CLI · agy (not installed)' })).toBeInTheDocument()
  })

  it('lets you pick a remote framework', () => {
    const onFramework = vi.fn()
    const omb: Agent = {
      ...grokAgent,
      agent_id: 'starter-remote',
      name: 'Remote agent',
      kind: 'remote',
      agent_type: 'remote',
      framework: 'openmausbot',
      cli: undefined,
    }
    render(
      <BackendSelect
        agent={omb}
        value="remote"
        clis={clis}
        onChange={() => undefined}
        remoteMembers={[{ id: 'cos-1', name: 'Chief of Staff' }]}
        remoteMember="cos-1"
        onRemoteMemberChange={() => undefined}
        remoteFrameworks={[
          { id: 'openmausbot', name: 'OpenMausBot' },
          { id: 'hermes', name: 'Hermes' },
          { id: 'dsh', name: 'DeepSeek Harness' },
        ]}
        remoteFramework="openmausbot"
        onRemoteFrameworkChange={onFramework}
      />,
    )
    const select = screen.getByLabelText('Remote framework')
    expect(select).toHaveValue('openmausbot')
    fireEvent.change(select, { target: { value: 'hermes' } })
    expect(onFramework).toHaveBeenCalledWith('hermes')
  })

  it('lets you pick a catalog model or type a custom id', () => {
    const onCliModelChange = vi.fn()
    const { rerender } = render(
      <BackendSelect
        agent={grokAgent}
        value="cli:grok"
        clis={clis}
        onChange={() => undefined}
        cliModel=""
        onCliModelChange={onCliModelChange}
      />,
    )
    const modelSelect = screen.getByLabelText('CLI model')
    expect(modelSelect).toHaveDisplayValue('grok default')
    fireEvent.change(modelSelect, { target: { value: 'grok-4.5' } })
    expect(onCliModelChange).toHaveBeenCalledWith('grok-4.5')

    rerender(
      <BackendSelect
        agent={grokAgent}
        value="cli:grok"
        clis={clis}
        onChange={() => undefined}
        cliModel="grok-4.5"
        onCliModelChange={onCliModelChange}
      />,
    )
    fireEvent.change(screen.getByLabelText('CLI model'), { target: { value: '__custom__' } })
    expect(onCliModelChange).toHaveBeenCalledWith('')

    rerender(
      <BackendSelect
        agent={grokAgent}
        value="cli:grok"
        clis={clis}
        onChange={() => undefined}
        cliModel=""
        onCliModelChange={onCliModelChange}
      />,
    )
    fireEvent.change(screen.getByLabelText('CLI model'), { target: { value: '__custom__' } })
    const custom = screen.getByLabelText('Custom CLI model')
    fireEvent.change(custom, { target: { value: 'my-local-model' } })
    expect(onCliModelChange).toHaveBeenCalledWith('my-local-model')
  })
})
