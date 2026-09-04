import { describe, expect, it } from 'vitest'
import {
  BLUEPRINT_BRIEF,
  REQ42_INJECTED_FIXTURE,
  ROLE_BRIEFS,
  TEAM_BRIEF,
  buildSummarizePrompt,
  localDefinitionContext,
  staticExplanation,
  summarizeWithLlm,
} from '../definitionExplain'

describe('definitionExplain', () => {
  it('returns human briefs for roles, teams, and blueprints without an LLM', () => {
    expect(staticExplanation('role', 'gate')).toMatch(/YES\/NO/)
    expect(staticExplanation('role', 'skeptic')).toMatch(/retry/)
    expect(staticExplanation('role', 'support')).toMatch(/Socratic/)
    expect(staticExplanation('role', 'cos')).toMatch(/talks to any team/i)
    expect(staticExplanation('team', 'default')).toBe(TEAM_BRIEF)
    expect(staticExplanation('blueprint', 'default')).toBe(BLUEPRINT_BRIEF)
    expect(ROLE_BRIEFS.gate).not.toMatch(/def classify/)
  })

  it('includes the distinctive injected fixture string in the summarise prompt', () => {
    const ctx = localDefinitionContext('role', 'gate', {
      extra: REQ42_INJECTED_FIXTURE,
    })
    ctx.default_llm = { configured: true, model: 'stub-llm' }
    const prompt = buildSummarizePrompt(ctx)
    expect(prompt).toContain(REQ42_INJECTED_FIXTURE)
    expect(prompt).toContain('YES/NO')
    expect(prompt).not.toMatch(/sk-[a-zA-Z0-9]|api[_-]?key\s*[:=]/i)
  })

  it('stub LLM summary includes the injected fixture; missing model skips inference', async () => {
    const ctx = localDefinitionContext('role', 'support', {
      extra: REQ42_INJECTED_FIXTURE,
    })
    ctx.default_llm = { configured: true, model: 'stub-llm' }
    const withLlm = await summarizeWithLlm(ctx, async (prompt) => `Summary:${prompt}`)
    expect(withLlm.summary).toContain(REQ42_INJECTED_FIXTURE)

    ctx.default_llm = { configured: false, model: null }
    const without = await summarizeWithLlm(ctx, async () => 'should-not-run')
    expect(without.configured).toBe(false)
    expect(without.summary).toBeNull()
  })
})
