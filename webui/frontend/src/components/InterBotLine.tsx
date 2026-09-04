import { LoadingDots } from './DaisyUI'
import { agentMarkColor, agentMarkIndex } from '../lib/hiddenAgents'
import type { InterBotHop, InterBotLine as InterBotLineData } from '../lib/interBot'

function HopAvatar({ hop, stacked }: { hop: InterBotHop; stacked: boolean }) {
  const color = agentMarkColor(hop.agentId || hop.name)
  return (
    <span
      className={`os-interbot-avatar ${stacked ? 'os-interbot-avatar--stacked' : ''}`}
      data-mark={String(agentMarkIndex(hop.agentId || hop.name))}
      data-agent={hop.agentId}
      title={hop.name}
      aria-hidden="true"
      style={{ backgroundColor: color }}
    />
  )
}

export default function InterBotLine({ line }: { line: InterBotLineData }) {
  if (line.kind === 'progress') {
    return (
      <div className="os-interbot-line" data-pending="true" role="status">
        <LoadingDots size="sm" aria-label="Inter-bot communication in progress" />
      </div>
    )
  }

  if (line.kind === 'single') {
    return (
      <div className="os-interbot-line" data-kind="single" role="status">
        <span>Message from</span>
        <HopAvatar hop={line.hop} stacked={false} />
        <span className="os-interbot-name">{line.hop.name}</span>
      </div>
    )
  }

  return (
    <div className="os-interbot-line" data-kind="multi" role="status">
      <span>Messaged</span>
      <span className="os-interbot-avatars" aria-hidden="true">
        {line.hops.map((hop) => (
          <HopAvatar key={hop.id} hop={hop} stacked />
        ))}
      </span>
      <span>
        {line.hops.length} {line.hops.length === 1 ? 'Bot' : 'Bots'}
      </span>
    </div>
  )
}
