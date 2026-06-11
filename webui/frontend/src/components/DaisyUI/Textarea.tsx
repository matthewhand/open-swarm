import { TextareaHTMLAttributes, forwardRef, useId } from 'react';

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
  id: propId,
  ...props
}, ref) => {
  const generatedId = useId();
  const textareaId = propId || generatedId;
  const errorId = error ? `${textareaId}-error` : undefined;

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
        <label htmlFor={textareaId} className="label">
          <span className="label-text">{label}</span>
        </label>
      )}
      <textarea
        id={textareaId}
        ref={ref}
        className={textareaClasses.join(' ')}
        aria-invalid={!!error}
        aria-describedby={errorId}
        {...props}
      />
      {error && (
        <label htmlFor={textareaId} className="label">
          <span id={errorId} className="label-text-alt text-error">{error}</span>
        </label>
      )}
    </div>
  );
});

Textarea.displayName = 'Textarea';

export default Textarea;
