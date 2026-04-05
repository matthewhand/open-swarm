import React, { SelectHTMLAttributes, forwardRef, ReactNode } from 'react';

/**
 * Select component using DaisyUI classes
 * Docs: https://daisyui.com/components/select/
 */
export interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
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
  ...props
}, ref) => {
  const selectClasses = [
    'select',
    bordered ? 'select-bordered' : '',
    size === 'xs' ? 'select-xs' :
    size === 'sm' ? 'select-sm' :
    size === 'lg' ? 'select-lg' :
    '',
    color ? `select-${color}` : '',
    error ? 'select-error' : '',
    className
  ].filter(Boolean);

  return (
    <div className="form-control w-full">
      {label && (
        <label className="label">
          <span className="label-text">{label}</span>
        </label>
      )}
      <select ref={ref} className={selectClasses.join(' ')} {...props}>
        {children}
      </select>
      {error && (
        <label className="label">
          <span className="label-text-alt text-error">{error}</span>
        </label>
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
