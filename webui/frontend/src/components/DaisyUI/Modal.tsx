import { ReactNode, useEffect, useRef, useId } from 'react';
import FocusTrap from 'focus-trap-react';

/**
 * Modal component using DaisyUI classes
 * Docs: https://daisyui.com/components/modal/
 */
export interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  children: ReactNode;
  title?: string;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  className?: string;
}

export const Modal = ({
  isOpen,
  onClose,
  children,
  title,
  size = 'md',
  className = '',
}: ModalProps) => {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  const triggerElementRef = useRef<HTMLElement | null>(null);

  // Sync open state with native dialog methods and manage focus
  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    if (isOpen) {
      if (!dialog.open) {
        triggerElementRef.current = document.activeElement as HTMLElement | null;
        dialog.showModal();
      }
    } else {
      if (dialog.open) {
        dialog.close();
        if (triggerElementRef.current) {
          triggerElementRef.current.focus();
        }
      }
    }
  }, [isOpen]);

  // Handle native cancel event (e.g. Escape key)
  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    const handleCancel = (e: Event) => {
      e.preventDefault(); // Prevent native close to keep React state in sync
      onClose();
    };

    dialog.addEventListener('cancel', handleCancel);
    return () => dialog.removeEventListener('cancel', handleCancel);
  }, [onClose]);

  const sizeClasses = {
    sm: 'max-w-sm',
    md: 'max-w-md',
    lg: 'max-w-lg',
    xl: 'max-w-xl',
  };

  const dialogContent = (
    <dialog
      ref={dialogRef}
      className={`modal ${isOpen ? 'modal-open' : ''}`}
      aria-labelledby={title ? titleId : undefined}
      aria-modal="true"
      onClose={onClose}
    >
      <div 
        className={`modal-box ${sizeClasses[size]} ${className}`}
      >
        {title && (
          <h3 id={titleId} className="font-bold text-lg mb-4">{title}</h3>
        )}
        <div className="modal-content">
          {children}
        </div>
      </div>
      {/* DaisyUI modal-backdrop covers the whole screen outside the modal-box.
          Using a button instead of an un-focusable <form> ensures keyboard operability
          and correct semantics for closing the dialog by clicking outside. */}
      <div className="modal-backdrop">
        <button type="button" onClick={onClose} aria-label="Close dialog">
          <span className="sr-only">Close dialog</span>
        </button>
      </div>
    </dialog>
  );

  return isOpen ? (
    <FocusTrap focusTrapOptions={{ fallbackFocus: () => dialogRef.current || document.body }}>
      {dialogContent}
    </FocusTrap>
  ) : (
    dialogContent
  );
};

/**
 * Confirmation Modal
 */
export interface ConfirmModalProps extends ModalProps {
  onConfirm: () => void;
  confirmText?: string;
  cancelText?: string;
  confirmVariant?: 'primary' | 'secondary' | 'accent' | 'success' | 'warning' | 'error';
}

export const ConfirmModal = ({
  isOpen,
  onClose,
  onConfirm,
  children,
  title = 'Confirm Action',
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  confirmVariant = 'primary',
  ...props
}: ConfirmModalProps) => {
  return (
    <Modal isOpen={isOpen} onClose={onClose} title={title} {...props}>
      <div className="mb-6">
        {children}
      </div>
      <div className="modal-action flex gap-2">
        <button className="btn btn-outline" onClick={onClose}>
          {cancelText}
        </button>
        <button className={`btn btn-${confirmVariant}`} onClick={onConfirm}>
          {confirmText}
        </button>
      </div>
    </Modal>
  );
};

export default Modal;
