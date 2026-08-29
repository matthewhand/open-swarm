import { ReactNode } from 'react';

/**
 * Alert component using DaisyUI classes
 * Docs: https://daisyui.com/components/alert/
 */
export interface AlertProps {
  children: ReactNode;
  type?: 'info' | 'success' | 'warning' | 'error';
  icon?: ReactNode;
  className?: string;
  role?: string;
}

/** Interruptive roles for urgent types; polite status for info/success. */
function defaultRoleForType(type: NonNullable<AlertProps['type']>): string {
  return type === 'error' || type === 'warning' ? 'alert' : 'status';
}

export const Alert = ({
  children,
  type = 'info',
  icon,
  className = '',
  role,
}: AlertProps) => {
  const resolvedRole = role ?? defaultRoleForType(type);
  const alertClasses = [
    'alert',
    `alert-${type}`,
    // Keep body text at full opacity on tinted DaisyUI alert surfaces
    // (nested muted utilities can otherwise fail WCAG contrast).
    '[&>:last-child]:text-base-content',
    className
  ].filter(Boolean);

  return (
    <div role={resolvedRole} className={alertClasses.join(' ')}>
      {icon && <div data-testid="alert-icon-wrapper" className="mr-2 shrink-0" aria-hidden="true">{icon}</div>}
      <div className="min-w-0">{children}</div>
    </div>
  );
};

/**
 * Success Alert
 */
export const SuccessAlert = (props: Omit<AlertProps, 'type'>) => (
  <Alert type="success" {...props} />
);

/**
 * Warning Alert
 */
export const WarningAlert = (props: Omit<AlertProps, 'type'>) => (
  <Alert type="warning" {...props} />
);

/**
 * Error Alert
 */
export const ErrorAlert = (props: Omit<AlertProps, 'type'>) => (
  <Alert type="error" {...props} />
);

/**
 * Info Alert (default)
 */
export const InfoAlert = (props: Omit<AlertProps, 'type'>) => (
  <Alert type="info" {...props} />
);

export default Alert;
