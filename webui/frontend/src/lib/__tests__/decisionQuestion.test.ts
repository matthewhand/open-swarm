import { describe, expect, it } from 'vitest'
import { parseDecisionQuestion, stripDecisionQuestion } from '../decisionQuestion'

const FENCE = `\`\`\`question
{"id":"configure-agent","ask":"Configure which agent?","choices":["hybrid_team","skeptic"],"other":"Name an agent"}
\`\`\``

describe('parseDecisionQuestion', () => {
  it('parses a question fence', () => {
    expect(parseDecisionQuestion(FENCE)).toEqual({
      id: 'configure-agent',
      ask: 'Configure which agent?',
      choices: ['hybrid_team', 'skeptic'],
      other: 'Name an agent',
    })
    expect(stripDecisionQuestion(`note\n${FENCE}`)).toBe('note')
  })

  it('rejects prose and empty choices', () => {
    expect(parseDecisionQuestion('Please pick an agent at length…')).toBeNull()
    expect(
      parseDecisionQuestion('```question\n{"ask":"x","choices":[]}\n```'),
    ).toBeNull()
  })
})
