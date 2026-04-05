import React, { InputHTMLAttributes, forwardRef } from 'react';

/**
 * Input component using DaisyUI classes
 * Docs: https://daisyui.com/components/input/
 */
export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
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
  ...props
}, ref) => {
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
        <label className="label">
          <span className="label-text">{label}</span>
        </label>
      )}
      <input ref={ref} className={inputClasses.join(' ')} {...props} />
      {error && (
        <label className="label">
          <span className="label-text-alt text-error">{error}</span>
        </label>
      )}
    </div>
  );
});

Input.displayName = 'Input';

export default Input;
