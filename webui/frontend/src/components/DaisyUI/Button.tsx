import React, { forwardRef, ButtonHTMLAttributes } from 'react';

/**
 * Button component using DaisyUI classes
 * Docs: https://daisyui.com/components/button/
 */
export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'accent' | 'ghost' | 'link' | 'outline' | 'active' | 'disabled';
  size?: 'lg' | 'md' | 'sm' | 'xs';
  color?: 'primary' | 'secondary' | 'accent' | 'info' | 'success' | 'warning' | 'error' | 'ghost';
  wide?: boolean;
  block?: boolean;
  glass?: boolean;
  noAnimation?: boolean;
  loading?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(({
  variant = 'primary',
  size = 'md',
  color,
  wide = false,
  block = false,
  glass = false,
  noAnimation = false,
  loading = false,
  className = '',
  children,
  ...props
}, ref) => {
  // Build class list
  const classes = [
    'btn',
    // Variant classes
    variant === 'ghost' ? 'btn-ghost' :
    variant === 'link' ? 'btn-link' :
    variant === 'outline' ? 'btn-outline' :
    variant === 'active' ? 'btn-active' :
    variant === 'disabled' ? 'btn-disabled' :
    `btn-${variant}`,
    // Size classes
    size === 'lg' ? 'btn-lg' :
    size === 'sm' ? 'btn-sm' :
    size === 'xs' ? 'btn-xs' :
    '',
    // Color classes (override variant if specified)
    color ? `btn-${color}` : '',
    // Width classes
    wide ? 'btn-wide' : '',
    block ? 'btn-block' : '',
    // Glass effect
    glass ? 'glass' : '',
    // Animation
    noAnimation ? 'no-animation' : '',
    // Loading state
    loading ? 'loading' : '',
    // Custom classes
    className
  ].filter(Boolean);

  return (
    <button ref={ref} className={classes.join(' ')} {...props} disabled={loading || props.disabled}>
      {children}
    </button>
  );
});

Button.displayName = 'Button';

export default Button;
