import {
  memo,
  useEffect,
  useRef,
  useState,
  type KeyboardEvent,
  type MouseEvent,
  type ReactNode,
} from 'react'
import { Pencil } from 'lucide-react'
import { Textarea, LoadingDots } from './DaisyUI'
import { renderSafeMarkdown } from '../lib/markdown'

export interface ChatMessageBubbleProps {
  role: 'user' | 'assistant'
  agentName: string
  text: string
  streaming: boolean
  edited?: boolean
  canEdit: boolean
  editing: boolean
  onStartEdit: () => void
  onCancelEdit: () => void
  onSaveEdit: (text: string) => void
  children?: ReactNode
}

function selectionIsActive(): boolean {
  try {
    const sel = window.getSelection()
    return Boolean(sel && !sel.isCollapsed)
  } catch {
    return false
  }
}

/**
 * One chat bubble. On API-agent threads, hover reveals Edit and clicking
 * the bubble (or the control) enters in-place edit. CLI/remote pass
 * ``canEdit={false}`` so neither control nor click-to-edit is offered.
 */
export const ChatBubbleBody = memo(
  function ChatBubbleBody({
    text,
    streaming,
  }: {
    text: string
    streaming: boolean
  }) {
    if (text.length === 0) {
      return streaming ? (
        <LoadingDots size="sm" />
      ) : (
        <span className="opacity-60">(empty response)</span>
      )
    }
    return (
      <div
        data-testid="chat-md"
        className="chat-md break-words [&_p]:my-1 [&_p:first-child]:mt-0 [&_p:last-child]:mb-0 [&_pre]:my-2 [&_pre]:overflow-x-auto [&_pre]:rounded [&_pre]:bg-base-300/40 [&_pre]:p-2 [&_code]:text-sm [&_ul]:my-1 [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:my-1 [&_ol]:list-decimal [&_ol]:pl-5 [&_a]:underline"
        dangerouslySetInnerHTML={{ __html: renderSafeMarkdown(text) }}
      />
    )
  },
  (prev, next) => prev.text === next.text && prev.streaming === next.streaming,
)

export function ChatMessageBubble({
  role,
  agentName,
  text,
  streaming,
  edited,
  canEdit,
  editing,
  onStartEdit,
  onCancelEdit,
  onSaveEdit,
  children,
}: ChatMessageBubbleProps) {
  const [draft, setDraft] = useState(text)
  const textareaRef = useRef<HTMLTextAreaElement | null>(null)

  useEffect(() => {
    if (editing) {
      setDraft(text)
      const id = window.setTimeout(() => textareaRef.current?.focus(), 0)
      return () => window.clearTimeout(id)
    }
    return undefined
  }, [editing, text])

  const handleBubbleClick = (event: MouseEvent<HTMLDivElement>) => {
    if (!canEdit || streaming || editing) return
    const target = event.target as HTMLElement | null
    if (target?.closest('a, button, textarea, input')) return
    if (selectionIsActive()) return
    onStartEdit()
  }

  const handleEditorKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Escape') {
      event.preventDefault()
      event.stopPropagation()
      onCancelEdit()
      return
    }
    if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) {
      event.preventDefault()
      onSaveEdit(draft)
    }
  }

  return (
    <div
      className={`chat group ${role === 'user' ? 'chat-end' : 'chat-start'}`}
      data-message-role={role}
    >
      <div className="chat-header text-xs opacity-60">
        {role === 'user' ? 'You' : agentName}
        {edited ? (
          <span className="ml-1 font-normal opacity-70" data-testid="edited-hint">
            edited
          </span>
        ) : null}
      </div>
      {editing ? (
        <div className="chat-bubble bg-base-200 text-base-content w-full max-w-xl">
          <Textarea
            ref={textareaRef}
            aria-label="Edit message"
            size="sm"
            className="w-full min-h-24"
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={handleEditorKeyDown}
          />
          <div className="mt-2 flex justify-end gap-1">
            <button type="button" className="btn btn-ghost btn-xs" onClick={onCancelEdit}>
              Cancel
            </button>
            <button
              type="button"
              className="btn btn-primary btn-xs"
              onClick={() => onSaveEdit(draft)}
            >
              Save
            </button>
          </div>
        </div>
      ) : (
        <div
          className={`chat-bubble ${
            role === 'user' ? 'bg-neutral text-neutral-content' : 'bg-base-200 text-base-content'
          } ${canEdit && !streaming ? 'cursor-pointer' : ''}`}
          data-testid="chat-bubble"
          onClick={handleBubbleClick}
        >
          <ChatBubbleBody text={text} streaming={streaming} />
          {children}
        </div>
      )}
      {canEdit && !streaming && !editing ? (
        <button
          type="button"
          className="btn btn-ghost btn-xs mt-0.5 gap-1 opacity-0 group-hover:opacity-100 focus-visible:opacity-100"
          aria-label="Edit message"
          onClick={onStartEdit}
        >
          <Pencil className="h-3 w-3" aria-hidden="true" />
          Edit
        </button>
      ) : null}
    </div>
  )
}
