import { FileText, X } from 'lucide-react'
import { formatFileSize, isImageFile, type PendingAttachment } from '../lib/chatAttachments'

interface ComposerAttachChipsProps {
  attachments: PendingAttachment[]
  onRemove: (localId: string) => void
}

export default function ComposerAttachChips({
  attachments,
  onRemove,
}: ComposerAttachChipsProps) {
  if (attachments.length === 0) return null
  return (
    <ul className="os-attach-chips" aria-label="Attached files">
      {attachments.map((item) => {
        const image = isImageFile(item)
        return (
          <li key={item.localId} className="os-attach-chip group">
            {image ? (
              <img
                className="os-attach-chip__thumb"
                src={item.previewUrl || ''}
                alt={item.name}
              />
            ) : (
              <span className="os-attach-chip__meta">
                <FileText className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                <span className="os-attach-chip__name">{item.name}</span>
                <span className="os-attach-chip__size">{formatFileSize(item.size)}</span>
              </span>
            )}
            {item.status === 'uploading' ? (
              <span className="os-attach-chip__status">Uploading…</span>
            ) : null}
            {item.status === 'error' ? (
              <span className="os-attach-chip__status os-attach-chip__status--error">
                Failed
              </span>
            ) : null}
            <button
              type="button"
              className="os-attach-chip__remove"
              aria-label={`Remove ${item.name}`}
              onClick={() => onRemove(item.localId)}
            >
              <X className="h-3 w-3" aria-hidden="true" />
            </button>
          </li>
        )
      })}
    </ul>
  )
}
