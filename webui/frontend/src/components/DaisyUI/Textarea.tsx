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
    bordered ? '' : 'border-0',
    size === 'xs' ? 'textarea-xs' :
    size === 'sm' ? 'textarea-sm' :
    size === 'lg' ? 'textarea-lg' :
    '',
    color ? `textarea-${color}` : '',
    error ? 'textarea-error' : '',
    className
  ].filter(Boolean);

  return (
    <div className="w-full flex flex-col gap-1">
      {label && (
        <label htmlFor={textareaId} className="text-sm font-medium">
          {label}
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
        <span id={errorId} role="alert" className="text-xs text-error">{error}</span>
      )}
    </div>
  );
});

Textarea.displayName = 'Textarea';

export default Textarea;
