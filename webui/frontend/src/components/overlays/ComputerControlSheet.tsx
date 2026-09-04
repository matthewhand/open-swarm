import { Button, Modal } from '../DaisyUI'
import { notifyOverlayClosed } from '../../lib/chromeOverlay'
import ComputerControlPane from './ComputerControlPane'

export interface ComputerControlSheetProps {
  isOpen: boolean
  onClose: () => void
}

/** Standalone computer-control overlay over Chat (REQ-48 / #341/#361 host). */
export default function ComputerControlSheet({ isOpen, onClose }: ComputerControlSheetProps) {
  const handleClose = () => {
    onClose()
    notifyOverlayClosed()
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="Computer control"
      placement="end"
      size="sheet"
      className="flex min-h-0 flex-col"
    >
      <ComputerControlPane />
      <div className="modal-action mt-4">
        <Button type="button" variant="ghost" size="sm" onClick={handleClose}>
          Close
        </Button>
      </div>
    </Modal>
  )
}
