import { describe, expect, it } from 'vitest'
import { parseOpenaiAgentPersonas, personaInitials } from '../personaParse'

const THREE = `
from agents import Agent
researcher = Agent(name="Researcher", instructions="Look things up.")
writer = Agent(name="Writer", instructions="Draft the answer.")
reviewer = Agent(name="Reviewer", instructions="Check the draft.")
`

const ONE = `from agents import Agent\nsolo = Agent(name="Solo", instructions="Work alone.")\n`

const GARBAGE = `this is not python at all !!!\nAgent(name="FakeInvented")\n{{{\n`

const MAKE_AGENT = `
engineer = self._make_agent("engineer", "Implement", [])
skeptic = self._make_agent("skeptic", "Review", [])
cos = self._make_agent("coding-requirements-gate", "Quote", [])
`

describe('parseOpenaiAgentPersonas (REQ-81)', () => {
  it('counts three Agent(...) names', () => {
    const parsed = parseOpenaiAgentPersonas(THREE)
    expect(parsed.count).toBe(3)
    expect(parsed.personas.map((p) => p.name)).toEqual(['Researcher', 'Writer', 'Reviewer'])
    expect(parsed.parsed).toBe(true)
  })

  it('counts one Agent as a single named face', () => {
    const parsed = parseOpenaiAgentPersonas(ONE)
    expect(parsed.count).toBe(1)
    expect(parsed.personas).toEqual([{ name: 'Solo' }])
  })

  it('garbage source is one generic seat with no invented names', () => {
    const parsed = parseOpenaiAgentPersonas(GARBAGE)
    expect(parsed.count).toBe(1)
    expect(parsed.personas).toEqual([])
    expect(parsed.parsed).toBe(false)
  })

  it('parses software-dev style _make_agent helpers', () => {
    const parsed = parseOpenaiAgentPersonas(MAKE_AGENT)
    expect(parsed.personas.map((p) => p.name)).toEqual([
      'engineer',
      'skeptic',
      'coding-requirements-gate',
    ])
  })

  it('does not invent a name from a variable', () => {
    const parsed = parseOpenaiAgentPersonas('Agent(name=name, instructions="x")')
    expect(parsed.count).toBe(1)
    expect(parsed.personas).toEqual([])
  })

  it('initials come from the declared name', () => {
    expect(personaInitials('Researcher')).toBe('RE')
    expect(personaInitials('coding-requirements-gate')).toBe('CR')
  })
})
