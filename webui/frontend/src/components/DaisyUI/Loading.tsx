import React from 'react';

/**
 * Loading Spinner component
 * Docs: https://daisyui.com/components/loading/
 */
export interface LoadingSpinnerProps {
  size?: 'xs' | 'sm' | 'md' | 'lg';
  color?: 'primary' | 'secondary' | 'accent' | 'info' | 'success' | 'warning' | 'error';
  className?: string;
}

export const LoadingSpinner = ({
  size = 'md',
  color = 'primary',
  className = '',
}: LoadingSpinnerProps) => {
  const sizeClasses = {
    xs: 'loading-xs',
    sm: 'loading-sm',
    md: 'loading-md',
    lg: 'loading-lg',
  };

  const colorClasses = {
    primary: 'text-primary',
    secondary: 'text-secondary',
    accent: 'text-accent',
    info: 'text-info',
    success: 'text-success',
    warning: 'text-warning',
    error: 'text-error',
  };

  return (
    <span 
      className={`loading loading-spinner ${sizeClasses[size]} ${colorClasses[color]} ${className}`}
    />
  );
};

/**
 * Loading Dots component
 */
export const LoadingDots = ({
  size = 'md',
  color = 'primary',
  className = '',
}: LoadingSpinnerProps) => {
  const sizeClasses = {
    xs: 'loading-xs',
    sm: 'loading-sm',
    md: 'loading-md',
    lg: 'loading-lg',
  };

  const colorClasses = {
    primary: 'text-primary',
    secondary: 'text-secondary',
    accent: 'text-accent',
    info: 'text-info',
    success: 'text-success',
    warning: 'text-warning',
    error: 'text-error',
  };

  return (
    <span 
      className={`loading loading-dots ${sizeClasses[size]} ${colorClasses[color]} ${className}`}
    />
  );
};

/**
 * Loading Ring component
 */
export const LoadingRing = ({
  size = 'md',
  color = 'primary',
  className = '',
}: LoadingSpinnerProps) => {
  const sizeClasses = {
    xs: 'loading-xs',
    sm: 'loading-sm',
    md: 'loading-md',
    lg: 'loading-lg',
  };

  const colorClasses = {
    primary: 'text-primary',
    secondary: 'text-secondary',
    accent: 'text-accent',
    info: 'text-info',
    success: 'text-success',
    warning: 'text-warning',
    error: 'text-error',
  };

  return (
    <span 
      className={`loading loading-ring ${sizeClasses[size]} ${colorClasses[color]} ${className}`}
    />
  );
};

/**
 * Loading Ball component
 */
export const LoadingBall = ({
  size = 'md',
  color = 'primary',
  className = '',
}: LoadingSpinnerProps) => {
  const sizeClasses = {
    xs: 'loading-xs',
    sm: 'loading-sm',
    md: 'loading-md',
    lg: 'loading-lg',
  };

  const colorClasses = {
    primary: 'text-primary',
    secondary: 'text-secondary',
    accent: 'text-accent',
    info: 'text-info',
    success: 'text-success',
    warning: 'text-warning',
    error: 'text-error',
  };

  return (
    <span 
      className={`loading loading-ball ${sizeClasses[size]} ${colorClasses[color]} ${className}`}
    />
  );
};

/**
 * Loading Bars component
 */
export const LoadingBars = ({
  size = 'md',
  color = 'primary',
  className = '',
}: LoadingSpinnerProps) => {
  const sizeClasses = {
    xs: 'loading-xs',
    sm: 'loading-sm',
    md: 'loading-md',
    lg: 'loading-lg',
  };

  const colorClasses = {
    primary: 'text-primary',
    secondary: 'text-secondary',
    accent: 'text-accent',
    info: 'text-info',
    success: 'text-success',
    warning: 'text-warning',
    error: 'text-error',
  };

  return (
    <span 
      className={`loading loading-bars ${sizeClasses[size]} ${colorClasses[color]} ${className}`}
    />
  );
};

/**
 * Loading Infinity component
 */
export const LoadingInfinity = ({
  size = 'md',
  color = 'primary',
  className = '',
}: LoadingSpinnerProps) => {
  const sizeClasses = {
    xs: 'loading-xs',
    sm: 'loading-sm',
    md: 'loading-md',
    lg: 'loading-lg',
  };

  const colorClasses = {
    primary: 'text-primary',
    secondary: 'text-secondary',
    accent: 'text-accent',
    info: 'text-info',
    success: 'text-success',
    warning: 'text-warning',
    error: 'text-error',
  };

  return (
    <span 
      className={`loading loading-infinity ${sizeClasses[size]} ${colorClasses[color]} ${className}`}
    />
  );
};

/**
 * Skeleton Loading component
 */
export interface SkeletonProps {
  width?: string | number;
  height?: string | number;
  className?: string;
  rounded?: boolean;
}

export const Skeleton = ({
  width = '100%',
  height = '20px',
  className = '',
  rounded = true,
}: SkeletonProps) => {
  return (
    <div
      className={`skeleton ${rounded ? 'rounded' : ''} ${className}`}
      style={{ width, height }}
    />
  );
};

/**
 * Skeleton Text component
 */
export const SkeletonText = ({
  lines = 3,
  width = '100%',
  className = '',
}: {
  lines?: number;
  width?: string | number;
  className?: string;
}) => {
  return (
    <div className={`space-y-2 ${className}`}>
      {Array.from({ length: lines }).map((_, index) => (
        <Skeleton key={index} width={width} height="16px" />
      ))}
    </div>
  );
};

/**
 * Skeleton Card component
 */
export const SkeletonCard = ({
  className = '',
}: {
  className?: string;
}) => {
  return (
    <div className={`card bg-base-200 ${className}`}>
      <div className="card-body">
        <Skeleton width="60%" height="24px" className="mb-4" />
        <SkeletonText lines={3} className="mb-4" />
        <div className="flex gap-2">
          <Skeleton width="80px" height="32px" />
          <Skeleton width="80px" height="32px" />
        </div>
      </div>
    </div>
  );
};

/**
 * Skeleton Table component
 */
export const SkeletonTable = ({
  rows = 5,
  columns = 4,
  className = '',
}: {
  rows?: number;
  columns?: number;
  className?: string;
}) => {
  return (
    <div className={`overflow-x-auto ${className}`}>
      <table className="table w-full">
        <thead>
          <tr>
            {Array.from({ length: columns }).map((_, index) => (
              <th key={index} className="bg-base-300">
                <Skeleton width="80px" height="20px" />
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {Array.from({ length: rows }).map((_, rowIndex) => (
            <tr key={rowIndex}>
              {Array.from({ length: columns }).map((_, colIndex) => (
                <td key={colIndex}>
                  <Skeleton width="100%" height="16px" />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

/**
 * Loading Overlay component
 */
export const LoadingOverlay = ({
  isLoading = true,
  message = 'Loading...',
  className = '',
}: {
  isLoading?: boolean;
  message?: string;
  className?: string;
}) => {
  if (!isLoading) return null;

  return (
    <div className={`fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 ${className}`}>
      <div className="bg-base-100 p-6 rounded-lg shadow-xl text-center">
        <div className="flex justify-center mb-4">
          <LoadingSpinner size="lg" color="primary" />
        </div>
        <p className="text-lg font-medium">{message}</p>
      </div>
    </div>
  );
};

/**
 * Button with Loading state
 */
export const LoadingButton = ({
  loading = false,
  children,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { loading?: boolean }) => {
  return (
    <button {...props} disabled={loading || props.disabled}>
      {loading ? (
        <>
          <LoadingSpinner size="sm" className="mr-2" />
          {children}
        </>
      ) : (
        children
      )}
    </button>
  );
};

export default {
  LoadingSpinner,
  LoadingDots,
  LoadingRing,
  LoadingBall,
  LoadingBars,
  LoadingInfinity,
  Skeleton,
  SkeletonText,
  SkeletonCard,
  SkeletonTable,
  LoadingOverlay,
  LoadingButton,
};
