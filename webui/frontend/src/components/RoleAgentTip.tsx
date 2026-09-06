import { X } from 'lucide-react'
import { Alert } from './DaisyUI'
import { ROLE_AGENT_TIP_BODY, ROLE_AGENT_TIP_TITLE } from '../lib/roleAgentTip'

export interface RoleAgentTipProps {
  onDismiss: () => void
}

/** Chat-pane explainer for role seats (REQ-191). Not a modal — Chat stays mounted. */
export function RoleAgentTip({ onDismiss }: RoleAgentTipProps) {
  return (
    <div className="os-role-agent-tip" data-testid="role-agent-tip">
      <Alert type="info" className="os-role-agent-tip__alert" role="status">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="font-medium">{ROLE_AGENT_TIP_TITLE}</p>
            <p className="mt-0.5 text-sm text-base-content/80">{ROLE_AGENT_TIP_BODY}</p>
          </div>
          <button
            type="button"
            className="btn btn-ghost btn-xs btn-square shrink-0"
            aria-label="Dismiss role tip"
            data-testid="role-agent-tip-dismiss"
            onClick={onDismiss}
          >
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>
      </Alert>
    </div>
  )
}

export default RoleAgentTip
