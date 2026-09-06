import { describe, expect, it } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import SupportCreatedBlueprintCard from '../SupportCreatedBlueprintCard'
import { VIEW_EDIT_CODE_LABEL, type SupportNlBlueprintCard } from '../../lib/supportNlBlueprint'

const CARD: SupportNlBlueprintCard = {
  id: 'ba_eng_tester',
  title: 'BA → Engineer → Tester',
  usable: true,
  chatHref: '/chat?blueprint=ba_eng_tester',
  graphLabel: 'BA → Engineer → Tester',
  edges: [
    ['ba', 'engineer'],
    ['engineer', 'tester'],
  ],
  userWrotePython: false,
  code: 'class BaEngTesterBlueprint:\n    pass\n',
}

function renderCard(card: SupportNlBlueprintCard = CARD) {
  return render(
    <MemoryRouter>
      <SupportCreatedBlueprintCard card={card} />
    </MemoryRouter>,
  )
}

describe('SupportCreatedBlueprintCard (REQ-158)', () => {
  it('shows a usable team and hides Python until View / edit code', () => {
    renderCard()
    expect(screen.getByTestId('support-nl-blueprint-card')).toBeInTheDocument()
    expect(screen.getByTestId('support-nl-usable')).toHaveTextContent('Usable')
    expect(screen.getByTestId('support-nl-open-chat')).toHaveAttribute(
      'href',
      '/chat?blueprint=ba_eng_tester',
    )
    expect(screen.getByTestId('support-nl-code-hidden')).toBeInTheDocument()
    expect(screen.queryByTestId('support-nl-code')).not.toBeInTheDocument()
    expect(screen.queryByText(/class BaEngTesterBlueprint/)).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: VIEW_EDIT_CODE_LABEL }))
    expect(screen.getByTestId('support-nl-code')).toHaveValue(CARD.code)
    expect(screen.queryByTestId('support-nl-code-hidden')).not.toBeInTheDocument()
  })
})
