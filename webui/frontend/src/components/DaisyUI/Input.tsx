import { InputHTMLAttributes, forwardRef, useId } from 'react';

/**
 * Input component using DaisyUI 5 classes.
 * Docs: https://daisyui.com/components/input/
 *
 * daisyUI v5 notes: `form-control`, `label-text`, `label-text-alt`, and
 * `input-bordered` were removed. Layout uses utility classes; borders come
 * from the base `input` style. The `bordered` prop is kept for API
 * compatibility and maps to an explicit border for a non-default look.
 */
export interface InputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'size'> {
  label?: string;
  error?: string;
  bordered?: boolean;
  size?: 'xs' | 'sm' | 'md' | 'lg';
  color?: 'primary' | 'secondary' | 'accent' | 'info' | 'success' | 'warning' | 'error';
}

export const Input = forwardRef<HTMLInputElement, InputProps>(({
  label,
  error,
  bordered = true,
  size = 'md',
  color,
  className = '',
  id: propId,
  ...props
}, ref) => {
  const generatedId = useId();
  const inputId = propId || generatedId;
  const errorId = error ? `${inputId}-error` : undefined;

  const inputClasses = [
    'input',
    bordered ? '' : 'border-0',
    size === 'xs' ? 'input-xs' :
    size === 'sm' ? 'input-sm' :
    size === 'lg' ? 'input-lg' :
    '',
    color ? `input-${color}` : '',
    error ? 'input-error' : '',
    className
  ].filter(Boolean);

  return (
    <div className="w-full flex flex-col gap-1">
      {label && (
        <label htmlFor={inputId} className="text-sm font-medium">
          {label}
        </label>
      )}
      <input
        id={inputId}
        ref={ref}
        className={inputClasses.join(' ')}
        aria-invalid={!!error}
        aria-describedby={errorId}
        {...props}
      />
      {error && (
        <span id={errorId} role="alert" className="text-xs text-error">{error}</span>
      )}
    </div>
  );
});

Input.displayName = 'Input';

export default Input;
