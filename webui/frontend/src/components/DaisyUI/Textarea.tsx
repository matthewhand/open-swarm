import React, { TextareaHTMLAttributes, forwardRef } from 'react';

/**
 * Textarea component using DaisyUI classes
 * Docs: https://daisyui.com/components/textarea/
 */
export interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
  bordered?: boolean;
  size?: 'xs' | 'sm' | 'md' | 'lg';
  color?: 'primary' | 'secondary' | 'accent' | 'info' | 'success' | 'warning' | 'error';
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(({
  label,
  error,
  bordered = true,
  size = 'md',
  color,
  className = '',
  ...props
}, ref) => {
  const textareaClasses = [
    'textarea',
    bordered ? 'textarea-bordered' : '',
    size === 'xs' ? 'textarea-xs' :
    size === 'sm' ? 'textarea-sm' :
    size === 'lg' ? 'textarea-lg' :
    '',
    color ? `textarea-${color}` : '',
    error ? 'textarea-error' : '',
    className
  ].filter(Boolean);

  return (
    <div className="form-control w-full">
      {label && (
        <label className="label">
          <span className="label-text">{label}</span>
        </label>
      )}
      <textarea ref={ref} className={textareaClasses.join(' ')} {...props} />
      {error && (
        <label className="label">
          <span className="label-text-alt text-error">{error}</span>
        </label>
      )}
    </div>
  );
});

Textarea.displayName = 'Textarea';

export default Textarea;
