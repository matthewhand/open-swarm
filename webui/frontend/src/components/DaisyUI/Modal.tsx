import { ReactNode, useEffect, useRef, useId } from 'react';

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

  // Sync open state with native dialog methods and toggle body scroll lock
  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    if (isOpen) {
      if (!dialog.open) {
        dialog.showModal();
      }
      document.body.style.overflow = 'hidden';
    } else {
      if (dialog.open) {
        dialog.close();
      }
      document.body.style.overflow = '';
    }

    return () => {
      document.body.style.overflow = '';
    };
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

  return (
    <dialog
      ref={dialogRef}
      aria-modal="true"
      className={`modal ${isOpen ? 'modal-open' : ''}`}
      onClick={handleBackdropClick}
      aria-labelledby={title ? titleId : undefined}
    >
      <div 
        className={`modal-box ${sizeClasses[size]} ${className}`}
        onClick={(e) => e.stopPropagation()} // Prevent clicks inside from closing
      >
        {title && (
          <h3 id={titleId} className="font-bold text-lg mb-4">{title}</h3>
        )}
        <div className="modal-content">
          {children}
        </div>
      </div>
      <form method="dialog" className="modal-backdrop">
        <button onClick={onClose}>close</button>
      </form>
    </dialog>
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
