import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  createAgentSession,
  djangoSessionToPicker,
  fetchAgentSessions,
  mergePickerSessions,
  parseDjangoSession,
  sessionRelativeLabel,
} from '../agentSessions'
import { saveAgentSessions, SCALE_OUT_SESSIONS_STORAGE_KEY } from '../scaleOutSessions'

describe('agentSessions (REQ-105)', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    localStorage.removeItem(SCALE_OUT_SESSIONS_STORAGE_KEY)
  })

  it('parses Django rows and maps them for the shared picker', () => {
    const row = parseDjangoSession(
      {
        id: 'sess-a',
        conversation_id: 'sess-a',
        agent_id: 'codey',
        title: 'Notes',
        snippet: 'later notes',
        created_at: '2026-09-05T00:00:00Z',
        updated_at: '2026-09-05T00:30:00Z',
        labels: ['keep'],
        cli_session_id: 'cli-1',
        status: 'finished',
      },
      'codey',
    )
    expect(row?.title).toBe('Notes')
    expect(row?.cli_session_id).toBe('cli-1')
    const picker = djangoSessionToPicker(row!)
    expect(picker.id).toBe('sess-a')
    expect(picker.snippet).toBe('later notes')
    expect(sessionRelativeLabel({ updatedAt: Date.now() - 2 * 60 * 1000 })).toBe('2 min ago')
  })

  it('lists Django sessions and merges leftover scale-out rows without duplicating ids', async () => {
    saveAgentSessions('codey', [
      {
        id: 'sess-a',
        agentId: 'codey',
        title: 'dup',
        snippet: '',
        status: 'finished',
        startedAt: 1,
        updatedAt: 1,
      },
      {
        id: 'scale-1',
        agentId: 'codey',
        title: 'Scale task',
        snippet: 'worker',
        status: 'running',
        startedAt: 2,
        updatedAt: 2,
      },
    ])
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          object: 'agent_session_list',
          agent_id: 'codey',
          sessions: [
            {
              id: 'sess-a',
              conversation_id: 'sess-a',
              agent_id: 'codey',
              title: 'Notes',
              snippet: 'from django',
              created_at: '2026-09-05T00:00:00Z',
              updated_at: '2026-09-05T00:00:00Z',
              labels: [],
              cli_session_id: null,
            },
          ],
        }),
      } as Response),
    )
    const listed = await fetchAgentSessions('codey')
    expect(listed).toHaveLength(1)
    const merged = mergePickerSessions('codey', listed)
    expect(merged.map((row) => row.id).sort()).toEqual(['scale-1', 'sess-a'])
    expect(merged.find((row) => row.id === 'sess-a')?.title).toBe('Notes')
  })

  it('creates an empty Django session via POST { new: true }', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        object: 'agent_session',
        id: 'sess-new',
        conversation_id: 'sess-new',
        agent_id: 'codey',
        title: 'New session',
        snippet: '',
        empty: true,
      }),
    } as Response)
    vi.stubGlobal('fetch', fetchMock)
    const created = await createAgentSession('codey')
    expect(created?.id).toBe('sess-new')
    expect(created?.empty).toBe(true)
    expect(String(fetchMock.mock.calls[0][0])).toContain('/v1/agents/codey/sessions/')
    expect(JSON.parse(String(fetchMock.mock.calls[0][1].body))).toMatchObject({
      new: true,
      empty: true,
    })
  })
})
