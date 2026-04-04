import React, { ReactNode } from 'react';

/**
 * Badge component using DaisyUI classes
 * Docs: https://daisyui.com/components/badge/
 */
export interface BadgeProps {
  children: ReactNode;
  type?: 'neutral' | 'primary' | 'secondary' | 'accent' | 'ghost' | 'info' | 'success' | 'warning' | 'error';
  size?: 'xs' | 'sm' | 'md' | 'lg';
  outline?: boolean;
  className?: string;
}

export const Badge = ({
  children,
  type = 'neutral',
  size = 'md',
  outline = false,
  className = '',
}: BadgeProps) => {
  const badgeClasses = [
    'badge',
    outline ? 'badge-outline' : `badge-${type}`,
    size === 'xs' ? 'badge-xs' :
    size === 'sm' ? 'badge-sm' :
    size === 'lg' ? 'badge-lg' :
    '',
    className
  ].filter(Boolean);

  return (
    <span className={badgeClasses.join(' ')}>
      {children}
    </span>
  );
};

/**
 * Primary Badge
 */
export const PrimaryBadge = (props: Omit<BadgeProps, 'type'>) => (
  <Badge type="primary" {...props} />
);

/**
 * Success Badge
 */
export const SuccessBadge = (props: Omit<BadgeProps, 'type'>) => (
  <Badge type="success" {...props} />
);

/**
 * Warning Badge
 */
export const WarningBadge = (props: Omit<BadgeProps, 'type'>) => (
  <Badge type="warning" {...props} />
);

/**
 * Error Badge
 */
export const ErrorBadge = (props: Omit<BadgeProps, 'type'>) => (
  <Badge type="error" {...props} />
);

/**
 * Info Badge
 */
export const InfoBadge = (props: Omit<BadgeProps, 'type'>) => (
  <Badge type="info" {...props} />
);

export default Badge;
