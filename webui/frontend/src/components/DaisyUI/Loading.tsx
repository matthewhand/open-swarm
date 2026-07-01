import React from 'react';

/**
 * Loading Spinner component
 * Docs: https://daisyui.com/components/loading/
 */
export interface LoadingSpinnerProps {
  size?: 'xs' | 'sm' | 'md' | 'lg';
  color?: 'primary' | 'secondary' | 'accent' | 'info' | 'success' | 'warning' | 'error';
  className?: string;
  'aria-label'?: string;
}

export const LoadingSpinner = ({
  size = 'md',
  color = 'primary',
  className = '',
  'aria-label': ariaLabel = 'Loading',
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
      role="status"
      aria-label={ariaLabel}
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
  'aria-label': ariaLabel = 'Loading',
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
      role="status"
      aria-label={ariaLabel}
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
  'aria-label': ariaLabel = 'Loading',
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
      role="status"
      aria-label={ariaLabel}
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
  'aria-label': ariaLabel = 'Loading',
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
      role="status"
      aria-label={ariaLabel}
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
  'aria-label': ariaLabel = 'Loading',
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
      role="status"
      aria-label={ariaLabel}
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
  'aria-label': ariaLabel = 'Loading',
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
      role="status"
      aria-label={ariaLabel}
    />
  );
};

/**
 * Skeleton loaders component
 */
export interface SkeletonProps {
  className?: string;
  w?: string;
  h?: string;
  rounded?: boolean;
  circle?: boolean;
}

export const Skeleton = ({
  className = '',
  w,
  h,
  rounded = true,
  circle = false,
}: SkeletonProps) => {
  const style = {
    ...(w ? { width: w } : {}),
    ...(h ? { height: h } : {}),
  };

  const classes = [
    'skeleton',
    circle ? 'rounded-full' : rounded ? 'rounded' : 'rounded-none',
    className
  ].filter(Boolean).join(' ');

  return <div className={classes} style={style} aria-hidden="true" />;
};

export const SkeletonText = ({ lines = 3, className = '' }) => (
  <div className={`space-y-2 ${className}`}>
    {Array.from({ length: lines }).map((_, i) => (
      <Skeleton key={i} h="1rem" w={i === lines - 1 ? '70%' : '100%'} />
    ))}
  </div>
);

export const SkeletonCard = ({ className = '' }) => (
  <div className={`flex flex-col gap-4 p-4 border border-base-300 rounded-box ${className}`}>
    <div className="flex gap-4 items-center">
      <Skeleton w="3rem" h="3rem" circle />
      <SkeletonText lines={2} className="flex-1" />
    </div>
    <Skeleton h="8rem" />
    <SkeletonText lines={2} />
  </div>
);

export const SkeletonTable = ({ rows = 5, cols = 4, className = '' }) => (
  <div className={`overflow-x-auto ${className}`}>
    <table className="table w-full">
      <thead>
        <tr>
          {Array.from({ length: cols }).map((_, i) => (
            <th key={i}><Skeleton h="1rem" w="80%" /></th>
          ))}
        </tr>
      </thead>
      <tbody>
        {Array.from({ length: rows }).map((_, rowIndex) => (
          <tr key={rowIndex}>
            {Array.from({ length: cols }).map((_, colIndex) => (
              <td key={colIndex}>
                <Skeleton h="1rem" w={colIndex === 0 ? '60%' : '90%'} />
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  </div>
);

/**
 * Full page or container loading overlay
 */
export const LoadingOverlay = ({
  message = 'Loading...',
  className = ''
}) => {
  return (
    <div
      className={`fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 ${className}`}
      role="dialog"
      aria-modal="true"
      aria-label={message}
    >
      <div className="bg-base-100 p-6 rounded-lg shadow-xl text-center">
        <div className="flex justify-center mb-4">
          <LoadingSpinner size="lg" color="primary" />
        </div>
        <p className="text-lg font-medium" role="status">{message}</p>
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
    <button
      {...props}
      disabled={loading || props.disabled}
      aria-disabled={loading || props.disabled}
      aria-busy={loading}
    >
      {loading ? (
        <>
          <LoadingSpinner size="sm" className="mr-2" />
          <span className="sr-only">Loading</span>
          {children}
        </>
      ) : (
        children
      )}
    </button>
  );
};

// Export individual components as well as the default object
const LoadingComponents = {
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

export default LoadingComponents;
