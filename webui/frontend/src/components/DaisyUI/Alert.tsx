import React, { ReactNode } from 'react';

/**
 * Alert component using DaisyUI classes
 * Docs: https://daisyui.com/components/alert/
 */
export interface AlertProps {
  children: ReactNode;
  type?: 'info' | 'success' | 'warning' | 'error';
  icon?: ReactNode;
  className?: string;
}

export const Alert = ({
  children,
  type = 'info',
  icon,
  className = '',
}: AlertProps) => {
  const alertClasses = [
    'alert',
    `alert-${type}`,
    className
  ].filter(Boolean);

  return (
    <div role="alert" className={alertClasses.join(' ')}>
      {icon && <div className="mr-2">{icon}</div>}
      <div>{children}</div>
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
