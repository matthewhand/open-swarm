import { afterEach, describe, expect, it } from 'vitest'
import {
  nextInferenceIndex,
  normalizeInferenceList,
  pickScaleOut,
  serializeInferenceList,
} from '../inferenceList'
import {
  AGENT_EDITS_KEY,
  loadInferenceList,
  saveInferenceList,
} from '../agentEdits'

afterEach(() => {
  localStorage.clear()
  sessionStorage.clear()
})

describe('REQ-69 inference list', () => {
  it('persists order on the agent', () => {
    saveInferenceList('support', [
      { id: 'orchestration', kind: 'llm' },
      { id: 'grok', kind: 'cli' },
    ])
    const loaded = loadInferenceList('support')
    expect(loaded.map((s) => `${s.kind}:${s.id}`)).toEqual(['llm:orchestration', 'cli:grok'])
    const raw = JSON.parse(localStorage.getItem(AGENT_EDITS_KEY) || '{}')
    expect(raw.support.inferenceList[0]).toBe('llm:orchestration')
  })

  it('empty list is Settings default', () => {
    expect(normalizeInferenceList([])).toEqual([])
    expect(loadInferenceList('nobody')).toEqual([])
    expect(serializeInferenceList([])).toEqual([])
  })

  it('scale-out two tasks hit two different seats', () => {
    const seats = [
      { id: 'a', kind: 'llm' as const },
      { id: 'b', kind: 'llm' as const },
    ]
    const i0 = nextInferenceIndex('worker', 2)
    const i1 = nextInferenceIndex('worker', 2)
    expect(pickScaleOut(seats, i0)?.id).not.toBe(pickScaleOut(seats, i1)?.id)
    expect(new Set([pickScaleOut(seats, i0)?.id, pickScaleOut(seats, i1)?.id])).toEqual(
      new Set(['a', 'b']),
    )
  })
})
