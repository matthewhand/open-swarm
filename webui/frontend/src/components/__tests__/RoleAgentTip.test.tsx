import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { RoleAgentTip } from '../RoleAgentTip'
import { ROLE_AGENT_TIP_BODY, ROLE_AGENT_TIP_TITLE } from '../../lib/roleAgentTip'

describe('RoleAgentTip', () => {
  it('renders Mode A vs Mode B copy and dismisses on click', () => {
    const onDismiss = vi.fn()
    render(<RoleAgentTip onDismiss={onDismiss} />)
    const tip = screen.getByTestId('role-agent-tip')
    expect(tip).toHaveTextContent(ROLE_AGENT_TIP_TITLE)
    expect(tip).toHaveTextContent(ROLE_AGENT_TIP_BODY)
    expect(tip).toHaveTextContent(/handoff|as-tool|latest message/i)
    fireEvent.click(screen.getByTestId('role-agent-tip-dismiss'))
    expect(onDismiss).toHaveBeenCalledTimes(1)
  })

  it('is an inline status banner, not a dialog', () => {
    render(<RoleAgentTip onDismiss={() => undefined} />)
    expect(screen.getByRole('status')).toBeInTheDocument()
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })
})
