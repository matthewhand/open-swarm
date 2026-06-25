import { forwardRef, ButtonHTMLAttributes } from 'react';

/**
 * Button component using DaisyUI classes
 * Docs: https://daisyui.com/components/button/
 */
export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'accent' | 'info' | 'ghost' | 'link' | 'outline' | 'active' | 'disabled';
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
    // Custom classes
    className
  ].filter(Boolean);

  return (
    <button
      ref={ref}
      className={classes.join(' ')}
      disabled={loading || props.disabled}
      aria-disabled={loading || props.disabled}
      aria-busy={loading}
      {...props}
    >
      {/* DaisyUI 5: the bare `loading` btn class no longer renders a spinner —
          an explicit loading-spinner span is required for visible feedback. */}
      {loading && <span data-testid="button-spinner" className="loading loading-spinner loading-sm" aria-hidden="true" />}
      {loading && <span className="sr-only">Loading</span>}
      {children}
    </button>
  );
});

Button.displayName = 'Button';

export default Button;
