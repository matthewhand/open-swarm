import { Button, Modal } from '../DaisyUI'
import { notifyOverlayClosed } from '../../lib/chromeOverlay'
import RoleDefinitionPane, { DEFAULT_ROLE_ID } from './RoleDefinitionPane'

export interface RolePaneSheetProps {
  isOpen: boolean
  onClose: () => void
  roleId?: string
}

/** Standalone role-definition overlay over Chat (REQ-48 / #356 host). */
export default function RolePaneSheet({
  isOpen,
  onClose,
  roleId = DEFAULT_ROLE_ID,
}: RolePaneSheetProps) {
  const handleClose = () => {
    onClose()
    notifyOverlayClosed()
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="Role"
      placement="end"
      size="sheet"
      className="flex min-h-0 flex-col"
    >
      <RoleDefinitionPane roleId={roleId} />
      <div className="modal-action mt-4">
        <Button type="button" variant="ghost" size="sm" onClick={handleClose}>
          Close
        </Button>
      </div>
    </Modal>
  )
}
