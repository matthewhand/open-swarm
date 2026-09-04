import { createContext, useCallback, useContext, useState, useEffect, useRef, ReactNode } from 'react';
import { CheckCircle2, AlertTriangle, AlertCircle, Info, X } from 'lucide-react';

/**
 * Toast types
 */
export type ToastType = 'success' | 'error' | 'warning' | 'info';

/** Chat websocket drop / handshake failure / auth-gate outage (REQ-112). */
export const TOAST_KIND_WS_DISCONNECT = 'ws-disconnect';

/**
 * Toast interface
 */
export interface Toast {
  id: string;
  type: ToastType;
  title: string;
  message: ReactNode;
  duration?: number;
  position?: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left';
  /** When set, addToast replaces any existing toast with the same kind. */
  kind?: string;
}

/**
 * Toast context
 */
interface ToastContextType {
  toasts: Toast[];
  addToast: (toast: Omit<Toast, 'id'>) => void;
  removeToast: (id: string) => void;
  dismissByKind: (kind: string) => void;
  success: (title: string, message: ReactNode, duration?: number) => void;
  error: (title: string, message: ReactNode, duration?: number) => void;
  warning: (title: string, message: ReactNode, duration?: number) => void;
  info: (title: string, message: ReactNode, duration?: number) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

/**
 * Toast Provider
 */
export const ToastProvider = ({ children }: { children: ReactNode }) => {
  const [toasts, setToasts] = useState<Toast[]>([]);

  // Monotonic counter avoids same-millisecond id collisions (duplicate keys).
  const toastIdRef = useRef(0);

  const addToast = useCallback((toast: Omit<Toast, 'id'>) => {
    setToasts(prev => {
      if (toast.kind) {
        const others = prev.filter(existing => existing.kind !== toast.kind);
        const existing = prev.find(candidate => candidate.kind === toast.kind);
        if (existing) {
          return [...others, { ...existing, ...toast }];
        }
      }
      toastIdRef.current += 1;
      const id = `toast-${Date.now()}-${toastIdRef.current}`;
      return [...prev, { ...toast, id }];
    });
  }, []);

  const removeToast = useCallback((id: string) => {
    setToasts(prev => prev.filter(toast => toast.id !== id));
  }, []);

  const dismissByKind = useCallback((kind: string) => {
    setToasts(prev => prev.filter(toast => toast.kind !== kind));
  }, []);

  const success = useCallback((title: string, message: ReactNode, duration = 5000) => {
    addToast({ type: 'success', title, message, duration, position: 'top-right' });
  }, [addToast]);

  const error = useCallback((title: string, message: ReactNode, duration = 5000) => {
    addToast({ type: 'error', title, message, duration, position: 'top-right' });
  }, [addToast]);

  const warning = useCallback((title: string, message: ReactNode, duration = 5000) => {
    addToast({ type: 'warning', title, message, duration, position: 'top-right' });
  }, [addToast]);

  const info = useCallback((title: string, message: ReactNode, duration = 5000) => {
    addToast({ type: 'info', title, message, duration, position: 'top-right' });
  }, [addToast]);

  return (
    <ToastContext.Provider value={{ toasts, addToast, removeToast, dismissByKind, success, error, warning, info }}>
      {children}
      <ToastContainer toasts={toasts} removeToast={removeToast} />
    </ToastContext.Provider>
  );
};

/**
 * Toast Container - renders all toasts
 */
interface ToastContainerProps {
  toasts: Toast[];
  removeToast: (id: string) => void;
}

const ToastContainer = ({ toasts, removeToast }: ToastContainerProps) => {
  // Group toasts by position
  const groupedToasts = toasts.reduce((acc, toast) => {
    const position = toast.position || 'top-right';
    if (!acc[position]) {
      acc[position] = [];
    }
    acc[position].push(toast);
    return acc;
  }, {} as Record<string, Toast[]>);

  return (
    <>
      {Object.entries(groupedToasts).map(([position, positionToasts]) => (
        <div key={position} className={`fixed ${getPositionClasses(position)} z-50 space-y-2`}>
          {positionToasts.map(toast => (
            <ToastItem key={toast.id} toast={toast} removeToast={removeToast} />
          ))}
        </div>
      ))}
    </>
  );
};

/**
 * Get position classes for toast container
 */
const getPositionClasses = (position: string) => {
  switch (position) {
    case 'top-right': return 'top-20 right-4';
    case 'top-left': return 'top-20 left-4';
    case 'bottom-right': return 'bottom-4 right-4';
    case 'bottom-left': return 'bottom-4 left-4';
    default: return 'top-4 right-4';
  }
};

/**
 * Individual Toast Item
 */
interface ToastItemProps {
  toast: Toast;
  removeToast: (id: string) => void;
}

const ToastItem = ({ toast, removeToast }: ToastItemProps) => {
  // Auto-remove toast after duration
  useEffect(() => {
    if (toast.duration) {
      const timer = setTimeout(() => {
        removeToast(toast.id);
      }, toast.duration);

      return () => clearTimeout(timer);
    }
  }, [toast.id, toast.duration, removeToast]);

  // Get toast colors and icons
  const { icon: Icon, bgColor, textColor } = getToastStyle(toast.type);

  const live = toast.type === 'error' || toast.type === 'warning' ? 'assertive' : 'polite';

  return (
    <div
      className={`alert ${bgColor} ${textColor} shadow-lg max-w-sm w-full`}
      role="status"
      aria-live={live}
      aria-atomic="true"
      data-toast-kind={toast.kind}
    >
      <div className="flex items-start gap-3">
        <div className="mt-1">
          <Icon className="h-5 w-5 flex-shrink-0" aria-hidden="true" />
        </div>
        <div className="flex-1">
          <h3 className="font-bold">{toast.title}</h3>
          <div className="text-sm mt-1">{toast.message}</div>
        </div>
      </div>
      <button
        type="button"
        className="btn btn-sm btn-ghost btn-circle ml-2"
        onClick={() => removeToast(toast.id)}
        aria-label="Dismiss notification"
      >
        <X className="h-4 w-4" aria-hidden="true" />
      </button>
    </div>
  );
};

/**
 * Get toast style based on type
 */
const getToastStyle = (type: ToastType) => {
  switch (type) {
    case 'success':
      return {
        icon: CheckCircle2,
        bgColor: 'bg-success text-success-content',
        textColor: 'text-success-content'
      };
    case 'error':
      return {
        icon: AlertCircle,
        bgColor: 'bg-error text-error-content',
        textColor: 'text-error-content'
      };
    case 'warning':
      return {
        icon: AlertTriangle,
        bgColor: 'bg-warning text-warning-content',
        textColor: 'text-warning-content'
      };
    case 'info':
      return {
        icon: Info,
        bgColor: 'bg-info text-info-content',
        textColor: 'text-info-content'
      };
    default:
      return {
        icon: Info,
        bgColor: 'bg-info text-info-content',
        textColor: 'text-info-content'
      };
  }
};

/**
 * Custom hook for using toast
 */
export const useToast = () => {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
};

/**
 * Convenience hooks for specific toast types
 */
export const useSuccessToast = () => {
  const { success } = useToast();
  return success;
};

export const useErrorToast = () => {
  const { error } = useToast();
  return error;
};

export const useWarningToast = () => {
  const { warning } = useToast();
  return warning;
};

export const useInfoToast = () => {
  const { info } = useToast();
  return info;
};

const ToastComponents = {
  ToastProvider,
  useToast,
  useSuccessToast,
  useErrorToast,
  useWarningToast,
  useInfoToast,
};

export default ToastComponents;
