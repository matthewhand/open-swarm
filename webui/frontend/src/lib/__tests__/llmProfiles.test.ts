import { describe, expect, it } from 'vitest'
import type { LlmProfilesSettings } from '../api'
import {
  effectiveTaskProfile,
  isKnownProfile,
  missingProfileWarning,
} from '../llmProfiles'

const settings: LlmProfilesSettings = {
  object: 'llm_profiles',
  profiles: [
    { id: 'gpt-4o-mini', object: 'llm_profile', source: 'config', owned_by: 'openai' },
    { id: 'gpt-5.6-terra', object: 'llm_profile', source: 'config', owned_by: 'openai' },
    { id: 'o3', object: 'llm_profile', source: 'config', owned_by: 'openai' },
  ],
  default_llm_profile: 'gpt-5.6-terra',
  default_is_auto: false,
  override_per_task: true,
  task_llm_profiles: {
    orchestration: 'gpt-5.6-terra',
    auxiliary: 'gpt-4o-mini',
    delegation: 'o3',
  },
  auto_picks: {
    orchestration: 'gpt-5.6-terra',
    auxiliary: 'gpt-4o-mini',
    delegation: 'o3',
    default: 'gpt-5.6-terra',
  },
  warnings: [],
  routes: {},
  task_classes: ['orchestration', 'auxiliary', 'delegation'],
}

describe('llmProfiles helpers', () => {
  it('treats boring ids as known picks', () => {
    expect(isKnownProfile('gpt-5.6-terra', settings)).toBe(true)
    expect(isKnownProfile('missing-slug', settings)).toBe(false)
  })

  it('override off uses Default for every task class', () => {
    const off = { ...settings, override_per_task: false }
    expect(effectiveTaskProfile('auxiliary', off)).toBe('gpt-5.6-terra')
    expect(effectiveTaskProfile('delegation', off)).toBe('gpt-5.6-terra')
  })

  it('override on routes summary to auxiliary and design to delegation', () => {
    expect(effectiveTaskProfile('auxiliary', settings)).toBe('gpt-4o-mini')
    expect(effectiveTaskProfile('delegation', settings)).toBe('o3')
  })

  it('missing slug warns and names the default fallback', () => {
    const warning = missingProfileWarning('missing-slug', settings, 'gpt-5.6-terra')
    expect(warning).toMatch(/missing-slug/)
    expect(warning).toMatch(/gpt-5.6-terra/)
    expect(missingProfileWarning('gpt-4o-mini', settings, 'gpt-5.6-terra')).toBeNull()
  })
})
