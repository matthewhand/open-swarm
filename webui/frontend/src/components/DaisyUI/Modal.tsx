import { ReactNode, useEffect, useRef, useId, useState } from 'react';
import FocusTrap from 'focus-trap-react';
import { Alert } from './Alert';
import { LoadingButton } from './Loading';

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
  'aria-label'?: string;
}

export const Modal = ({
  isOpen,
  onClose,
  children,
  title,
  size = 'md',
  className = '',
  'aria-label': ariaLabel,
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

  // Handle backdrop clicks (clicking outside the modal-box)
  const handleBackdropClick = (e: React.MouseEvent<HTMLDialogElement>) => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    const rect = dialog.getBoundingClientRect();
    const isInDialog = (
      rect.top <= e.clientY &&
      e.clientY <= rect.top + rect.height &&
      rect.left <= e.clientX &&
      e.clientX <= rect.left + rect.width
    );

    if (!isInDialog) {
      onClose();
    }
  };

  const sizeClasses = {
    sm: 'max-w-sm',
    md: 'max-w-md',
    lg: 'max-w-lg',
    xl: 'max-w-xl',
  };

  // Keep FocusTrap mounted and toggle `active` so DaisyUI open/close
  // transitions are not interrupted by remounting the dialog tree.
  return (
    <FocusTrap
      active={isOpen}
      focusTrapOptions={{
        allowOutsideClick: true,
        escapeDeactivates: false,
        fallbackFocus: () => dialogRef.current || document.body,
      }}
    >
      <dialog
        ref={dialogRef}
        className={`modal ${isOpen ? 'modal-open' : ''}`}
        onClick={handleBackdropClick}
        aria-labelledby={title ? titleId : undefined}
        aria-label={!title ? (ariaLabel || 'Dialog') : undefined}
        aria-modal={isOpen ? true : undefined}
        tabIndex={-1}
      >
        <div
          className={`modal-box ${sizeClasses[size]} ${className}`}
          onClick={(e) => e.stopPropagation()}
        >
          {title && (
            <h3 id={titleId} className="font-bold text-lg mb-4">{title}</h3>
          )}
          <div className="modal-content">
            {children}
          </div>
        </div>
        <form method="dialog" className="modal-backdrop">
          <button
            type="button"
            onClick={onClose}
            aria-label="Close modal"
            tabIndex={-1}
          >
            close
          </button>
        </form>
      </dialog>
    </FocusTrap>
  );
};

/**
 * Confirmation Modal
 */
export interface ConfirmModalProps extends ModalProps {
  onConfirm: () => void | Promise<void>;
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
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleConfirm = async () => {
    if (isSubmitting) return;

    setIsSubmitting(true);
    setError(null);

    try {
      await onConfirm();
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      } else if (typeof err === 'string') {
        setError(err);
      } else {
        setError('An unknown error occurred');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={title} {...props}>
      <div className="mb-6">
        {children}
      </div>

      {error && (
        <Alert type="error" className="mb-4">
          {error}
        </Alert>
      )}

      <div className="modal-action flex gap-2">
        <button type="button" className="btn btn-outline" onClick={onClose} disabled={isSubmitting}>
          {cancelText}
        </button>
        <LoadingButton
          type="button"
          className={`btn btn-${confirmVariant}`}
          onClick={handleConfirm}
          loading={isSubmitting}
        >
          {confirmText}
        </LoadingButton>
      </div>
    </Modal>
  );
};

export default Modal;
