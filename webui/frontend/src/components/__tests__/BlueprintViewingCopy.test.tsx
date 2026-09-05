import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, expect, it } from 'vitest'
import { BlueprintEditorPane } from '../SettingsSheet'
import { ToastProvider } from '../DaisyUI'

describe('REQ-188A-3: Blueprints must not claim Editing on read-only pre', () => {
  it('renders honest Viewing copy instead of claiming Editing on read-only recipe', () => {
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })

    render(
      <QueryClientProvider client={client}>
        <ToastProvider>
          <BlueprintEditorPane blueprintId="support" />
        </ToastProvider>
      </QueryClientProvider>,
    )

    // Should NOT claim "Editing Support"
    expect(screen.queryByText(/Editing Support/i)).toBeNull()

    // Should display honest "Viewing Support"
    const desc = screen.getByText(/Viewing/i)
    expect(desc).toHaveTextContent('Viewing Support')
    expect(desc).toHaveTextContent('This view displays the Python/API recipe')
  })
})
