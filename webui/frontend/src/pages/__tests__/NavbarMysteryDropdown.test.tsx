import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import ChatPage from '../ChatPage'
import { ToastProvider } from '../../components/DaisyUI'

describe('REQ-186 / Fixes #744: No mystery navbar You / Default dropdown', () => {
  let client: QueryClient

  beforeEach(() => {
    Element.prototype.scrollIntoView = vi.fn()
    client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation(async (input: RequestInfo) => {
        const url = String(input)
        if (url.includes('/v1/blueprints')) {
          return {
            ok: true,
            status: 200,
            json: async () => ({
              object: 'list',
              data: [
                { id: 'api_agent', name: 'api_agent', object: 'blueprint' },
                { id: 'codey', name: 'Codey', object: 'blueprint' },
              ],
            }),
          } as Response
        }
        if (url.includes('/v1/cli-agents')) {
          return {
            ok: true,
            status: 200,
            json: async () => ({
              clis: ['grok', 'agy'],
              native_consensus: {},
              catalog: {},
            }),
          } as Response
        }
        if (url.includes('/v1/remotes')) {
          return {
            ok: true,
            status: 200,
            json: async () => ({
              object: 'list',
              kinds: [],
            }),
          } as Response
        }
        return {
          ok: true,
          status: 200,
          json: async () => ({}),
        } as Response
      }),
    )
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('does not render api-select or api-model-select when api_agent is active', async () => {
    render(
      <QueryClientProvider client={client}>
        <ToastProvider>
          <MemoryRouter initialEntries={['/chat?blueprint=api_agent']}>
            <Routes>
              <Route path="/chat" element={<ChatPage />} />
            </Routes>
          </MemoryRouter>
        </ToastProvider>
      </QueryClientProvider>,
    )

    expect(screen.queryByTestId('api-select')).not.toBeInTheDocument()
    expect(screen.queryByTestId('api-model-select')).not.toBeInTheDocument()
    expect(screen.queryByRole('combobox', { name: 'API' })).not.toBeInTheDocument()
  })
})
