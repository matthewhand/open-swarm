import type { Agent } from '../types/agent'
import type { CliCatalogEntry, LlmProfileEntry } from './agent-api'
import { agentTypeOf } from './agent-types'
import { isSupportAgent } from './starter-agents'

export function inferenceConfigured(opts: {
  llmProfiles: LlmProfileEntry[]
  defaultLlm: string
  clis: CliCatalogEntry[]
}): boolean {
  if (opts.llmProfiles.some((p) => p.name || p.model)) return true
  if (opts.clis.some((c) => c.installed)) return true
  return Boolean((opts.defaultLlm || '').trim()) && opts.llmProfiles.length > 0
}

export function supportQuickstarts(inferenceOk: boolean): { key: string; label: string; prompt: string }[] {
  return [
    {
      key: 'A',
      label: 'Explain Open Swarm',
      prompt:
        'Explain Open Swarm: what it is, how agents, teams, and blueprints fit together, and how I talk to them here.',
    },
    {
      key: 'B',
      label: 'Build my first team',
      prompt:
        'Walk me through building my first agent team in this UI: New agent, CLI vs API vs remote, then Save as team.',
    },
    {
      key: 'C',
      label: 'Code a blueprint',
      prompt:
        'Help me code a BlueprintBase Python class for a small team. Show a complete module in a python fenced block.',
    },
    inferenceOk
      ? {
          key: 'D',
          label: 'Customise experience',
          prompt:
            'Help me customise this experience: hide extra agents, pick CLI vs API vs remote, and set a default LLM.',
        }
      : {
          key: 'D',
          label: 'Configure inference',
          prompt:
            'Inference is not configured. How do I set LiteLLM (http://10.0.0.30:8000, model auxiliary) or install grok/agy?',
        },
  ]
}

export function buildSupportBriefing(opts: {
  agents: Agent[]
  llmProfiles: LlmProfileEntry[]
  defaultLlm: string
  clis: CliCatalogEntry[]
}): string {
  const inferenceOk = inferenceConfigured(opts)
  const roster = opts.agents.filter((a) => !isSupportAgent(a))
  const lines = roster.map((a) => {
    const name = a.customName || a.name
    const type = agentTypeOf(a)
    return `- **${name}** (\`${a.agent_id}\`, ${type})`
  })
  const installed = opts.clis.filter((c) => c.installed).map((c) => c.name)
  const profiles = opts.llmProfiles.map((p) => p.model || p.name).filter(Boolean)
  const inferenceLines = inferenceOk
    ? [
        opts.defaultLlm ? `- Default LiteLLM: **${opts.defaultLlm}**` : '',
        profiles.length ? `- Profiles: ${profiles.join(', ')}` : '',
        installed.length ? `- Host CLIs: ${installed.join(', ')}` : '',
      ].filter(Boolean)
    : [
        '- **No inference configured yet.**',
        '- Open [Settings](/settings/) and set LiteLLM (`http://10.0.0.30:8000`, model `auxiliary`, provider `litellm`).',
        '- Or install **grok** / **agy** and pick them on the CLI agent.',
      ]

  return [
    'I am **Support**. I help you learn Open Swarm, configure inference, and build your first agent team.',
    '',
    '### Agents on this desk',
    lines.length ? lines.join('\n') : '- (catalog hidden — CLI, API, and Remote starters are in the sidebar)',
    '',
    '### Inference',
    ...inferenceLines,
    '',
    '### Next',
    'Build a first team with **New agent**, then **Save as team**. I can also **code a BlueprintBase** module in a Python block for an API agent.',
    '',
    'Shortcuts: [Teams](/teams/launch/) · [Blueprint creator](/blueprint-library/creator/) · [Settings](/settings/)',
  ].join('\n')
}
