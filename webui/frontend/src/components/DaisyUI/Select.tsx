import { SelectHTMLAttributes, forwardRef, ReactNode, useId } from 'react';

/**
 * Select component using DaisyUI classes
 * Docs: https://daisyui.com/components/select/
 */
export interface SelectProps extends Omit<SelectHTMLAttributes<HTMLSelectElement>, 'size'> {
  label?: string;
  error?: string;
  bordered?: boolean;
  size?: 'xs' | 'sm' | 'md' | 'lg';
  color?: 'primary' | 'secondary' | 'accent' | 'info' | 'success' | 'warning' | 'error';
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(({
  label,
  error,
  bordered = true,
  size = 'md',
  color,
  children,
  className = '',
  id: propId,
  ...props
}, ref) => {
  const generatedId = useId();
  const selectId = propId || generatedId;
  const errorId = error ? `${selectId}-error` : undefined;

  const selectClasses = [
    'select',
    bordered ? '' : 'border-0',
    size === 'xs' ? 'select-xs' :
    size === 'sm' ? 'select-sm' :
    size === 'lg' ? 'select-lg' :
    '',
    color ? `select-${color}` : '',
    error ? 'select-error' : '',
    className
  ].filter(Boolean);

  return (
    <div className="w-full flex flex-col gap-1">
      {label && (
        <label htmlFor={selectId} className="text-sm font-medium">
          {label}
        </label>
      )}
      <select
        id={selectId}
        ref={ref}
        className={selectClasses.join(' ')}
        aria-invalid={!!error}
        aria-describedby={errorId}
        {...props}
      >
        {children}
      </select>
      {error && (
        <span id={errorId} role="alert" className="text-xs text-error">{error}</span>
      )}
    </div>
  );
});

Select.displayName = 'Select';

/**
 * Select with custom options
 */
export interface SelectOption {
  value: string;
  label: ReactNode;
  disabled?: boolean;
}

export interface SmartSelectProps extends Omit<SelectProps, 'children'> {
  options: SelectOption[];
  placeholder?: string;
}

export const SmartSelect = forwardRef<HTMLSelectElement, SmartSelectProps>(({
  options,
  placeholder = 'Select an option',
  ...props
}, ref) => {
  return (
    <Select ref={ref} {...props}>
      {placeholder && <option value="" disabled>{placeholder}</option>}
      {options.map((option) => (
        <option key={option.value} value={option.value} disabled={option.disabled}>
          {option.label}
        </option>
      ))}
    </Select>
  );
});

SmartSelect.displayName = 'SmartSelect';

export default Select;
