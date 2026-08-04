import { InputHTMLAttributes, forwardRef, useId } from 'react';

/**
 * Input component using DaisyUI classes
 * Docs: https://daisyui.com/components/input/
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
    bordered ? 'input-bordered' : '',
    size === 'xs' ? 'input-xs' :
    size === 'sm' ? 'input-sm' :
    size === 'lg' ? 'input-lg' :
    '',
    color ? `input-${color}` : '',
    error ? 'input-error' : '',
    className
  ].filter(Boolean);

  return (
    <div className="form-control w-full">
      {label && (
        <label htmlFor={inputId} className="label">
          <span className="label-text">{label}</span>
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
        <label htmlFor={inputId} className="label">
          <span id={errorId} className="label-text-alt text-error">{error}</span>
        </label>
      )}
    </div>
  );
});

Input.displayName = 'Input';

export default Input;
