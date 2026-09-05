import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import EnvOverrideBadge from '../EnvOverrideBadge'

describe('EnvOverrideBadge', () => {
  it('renders ADR-002 override copy and no secret values', () => {
    render(
      <EnvOverrideBadge
        badge={{
          kind: 'overrides_env',
          label: 'Overrides env DEFAULT_LLM',
          env_var: 'DEFAULT_LLM',
          helper: '.env still has DEFAULT_LLM; this instance uses Settings.',
        }}
      />,
    )
    expect(screen.getByText('Overrides env DEFAULT_LLM')).toBeInTheDocument()
    expect(screen.getByText(/this instance uses Settings/)).toBeInTheDocument()
    expect(screen.queryByText(/sk-/)).not.toBeInTheDocument()
  })

  it('renders forced read-only badge', () => {
    render(
      <EnvOverrideBadge
        badge={{
          kind: 'forced',
          label: 'Forced by env HERMES_BASE_URL (read-only)',
          env_var: 'HERMES_BASE_URL',
          forced: true,
          editable: false,
        }}
      />,
    )
    expect(screen.getByText('Forced by env HERMES_BASE_URL (read-only)')).toBeInTheDocument()
  })

  it('renders secret env-only badge', () => {
    render(
      <EnvOverrideBadge
        badge={{
          kind: 'secret',
          label: 'Secret · env-only',
          env_var: 'OPENAI_API_KEY',
          set: true,
        }}
      />,
    )
    expect(screen.getByText('Secret · env-only')).toBeInTheDocument()
  })
})
