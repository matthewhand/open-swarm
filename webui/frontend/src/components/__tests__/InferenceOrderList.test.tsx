import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import InferenceOrderList from '../InferenceOrderList'
import type { InferenceSeat } from '../../lib/inferenceList'

const catalog = [
  { id: 'orchestration', kind: 'llm' as const, label: 'orchestration' },
  { id: 'grok', kind: 'cli' as const, label: 'grok' },
]

describe('InferenceOrderList', () => {
  it('adds from catalog and reports empty default', () => {
    const onChange = vi.fn()
    const { rerender } = render(
      <InferenceOrderList
        seats={[]}
        catalog={catalog}
        defaultLabel="orchestration"
        onChange={onChange}
      />,
    )
    expect(screen.getByTestId('inference-list-empty')).toHaveTextContent('orchestration')
    fireEvent.change(screen.getByTestId('inference-list-add'), {
      target: { value: 'cli:grok' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Add inference seat' }))
    expect(onChange).toHaveBeenCalledWith([
      expect.objectContaining({ id: 'grok', kind: 'cli' }),
    ])

    const seats: InferenceSeat[] = [{ id: 'grok', kind: 'cli', label: 'grok' }]
    rerender(
      <InferenceOrderList
        seats={seats}
        catalog={catalog}
        defaultLabel="orchestration"
        onChange={onChange}
      />,
    )
    expect(screen.getByTestId('inference-list-row')).toHaveAttribute('data-seat', 'cli:grok')
  })
})
