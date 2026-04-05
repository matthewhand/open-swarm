import React, { ReactNode, useEffect, useRef } from 'react';

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
  const modalRef = useRef<HTMLDivElement>(null);

  // Close modal when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (modalRef.current && !modalRef.current.contains(event.target as Node)) {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen, onClose]);

  // Close modal on Escape key
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
    }

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const sizeClasses = {
    sm: 'max-w-sm',
    md: 'max-w-md',
    lg: 'max-w-lg',
    xl: 'max-w-xl',
  };

  return (
    <div className="modal modal-open">
      <div 
        ref={modalRef}
        className={`modal-box ${sizeClasses[size]} ${className}`}
      >
        {title && (
          <h3 className="font-bold text-lg mb-4">{title}</h3>
        )}
        <div className="modal-content">
          {children}
        </div>
      </div>
    </div>
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
