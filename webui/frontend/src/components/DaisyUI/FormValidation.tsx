import React, { ReactNode, useState } from 'react';
import { Input, Select, Textarea } from './';

/**
 * Form validation types and utilities
 */
export type ValidationRule = {
  required?: boolean;
  minLength?: number;
  maxLength?: number;
  pattern?: RegExp;
  validate?: (value: any) => boolean | string;
  customMessage?: string;
};

export type FormErrors<T> = {
  [K in keyof T]?: string;
};

export type FormTouched<T> = {
  [K in keyof T]?: boolean;
};

/**
 * Form validation hook
 */
export const useFormValidation = <T extends Record<string, any>>(
  initialValues: T,
  validationRules: Record<keyof T, ValidationRule>
) => {
  const [values, setValues] = useState<T>(initialValues);
  const [errors, setErrors] = useState<FormErrors<T>>({});
  const [touched, setTouched] = useState<FormTouched<T>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isValid, setIsValid] = useState(false);

  // Validate a single field
  const validateField = (name: keyof T, value: any) => {
    const rule = validationRules[name];
    let error = '';

    if (rule) {
      // Required validation
      if (rule.required && !value) {
        error = rule.customMessage || 'This field is required';
      }
      // Min length validation
      else if (rule.minLength && value && value.length < rule.minLength) {
        error = rule.customMessage || `Minimum ${rule.minLength} characters required`;
      }
      // Max length validation
      else if (rule.maxLength && value && value.length > rule.maxLength) {
        error = rule.customMessage || `Maximum ${rule.maxLength} characters allowed`;
      }
      // Pattern validation
      else if (rule.pattern && value && !rule.pattern.test(value)) {
        error = rule.customMessage || 'Invalid format';
      }
      // Custom validation
      else if (rule.validate) {
        const result = rule.validate(value);
        if (typeof result === 'string') {
          error = result;
        } else if (result === false) {
          error = rule.customMessage || 'Invalid value';
        }
      }
    }

    return error;
  };

  // Validate entire form
  const validateForm = () => {
    const newErrors: FormErrors<T> = {};
    let valid = true;

    Object.keys(validationRules).forEach((key) => {
      const fieldKey = key as keyof T;
      const error = validateField(fieldKey, values[fieldKey]);
      if (error) {
        newErrors[fieldKey] = error;
        valid = false;
      }
    });

    setErrors(newErrors);
    setIsValid(valid);
    return valid;
  };

  // Handle field change
  const handleChange = (name: keyof T, value: any) => {
    setValues(prev => ({ ...prev, [name]: value }));
    
    // Validate field on change if already touched
    if (touched[name]) {
      const error = validateField(name, value);
      setErrors(prev => ({ ...prev, [name]: error }));
    }
  };

  // Handle blur (mark as touched)
  const handleBlur = (name: keyof T) => {
    setTouched(prev => ({ ...prev, [name]: true }));
    
    // Validate field when touched
    const error = validateField(name, values[name]);
    setErrors(prev => ({ ...prev, [name]: error }));
  };

  // Handle submit
  const handleSubmit = async (callback: (values: T) => Promise<void> | void) => {
    setIsSubmitting(true);
    
    const isValid = validateForm();
    
    if (isValid) {
      try {
        await callback(values);
      } catch (error) {
        console.error('Form submission error:', error);
        throw error;
      } finally {
        setIsSubmitting(false);
      }
    } else {
      setIsSubmitting(false);
    }
  };

  // Reset form
  const resetForm = () => {
    setValues(initialValues);
    setErrors({});
    setTouched({});
    setIsSubmitting(false);
    setIsValid(false);
  };

  return {
    values,
    errors,
    touched,
    isSubmitting,
    isValid,
    handleChange,
    handleBlur,
    handleSubmit,
    resetForm,
    setValues,
    setErrors,
  };
};

/**
 * Validated Input component
 */
export interface ValidatedInputProps {
  name: string;
  label?: string;
  type?: string;
  placeholder?: string;
  value: any;
  error?: string;
  touched?: boolean;
  onChange: (name: string, value: any) => void;
  onBlur: (name: string) => void;
  inputProps?: React.InputHTMLAttributes<HTMLInputElement>;
}

export const ValidatedInput = ({
  name,
  label,
  type = 'text',
  placeholder,
  value,
  error,
  touched,
  onChange,
  onBlur,
  inputProps,
}: ValidatedInputProps) => {
  return (
    <Input
      label={label}
      type={type}
      placeholder={placeholder}
      value={value}
      error={touched && error ? error : undefined}
      onChange={(e) => onChange(name, e.target.value)}
      onBlur={() => onBlur(name)}
      {...inputProps}
    />
  );
};

/**
 * Validated Select component
 */
export interface ValidatedSelectProps {
  name: string;
  label?: string;
  placeholder?: string;
  value: any;
  error?: string;
  touched?: boolean;
  onChange: (name: string, value: any) => void;
  onBlur: (name: string) => void;
  options: { value: string; label: ReactNode }[];
  selectProps?: React.SelectHTMLAttributes<HTMLSelectElement>;
}

export const ValidatedSelect = ({
  name,
  label,
  placeholder,
  value,
  error,
  touched,
  onChange,
  onBlur,
  options,
  selectProps,
}: ValidatedSelectProps) => {
  return (
    <Select
      label={label}
      value={value}
      error={touched && error ? error : undefined}
      onChange={(e) => onChange(name, e.target.value)}
      onBlur={() => onBlur(name)}
      {...selectProps}
    >
      {placeholder && <option value="" disabled>{placeholder}</option>}
      {options.map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </Select>
  );
};

/**
 * Validated Textarea component
 */
export interface ValidatedTextareaProps {
  name: string;
  label?: string;
  placeholder?: string;
  value: any;
  error?: string;
  touched?: boolean;
  onChange: (name: string, value: any) => void;
  onBlur: (name: string) => void;
  textareaProps?: React.TextareaHTMLAttributes<HTMLTextAreaElement>;
}

export const ValidatedTextarea = ({
  name,
  label,
  placeholder,
  value,
  error,
  touched,
  onChange,
  onBlur,
  textareaProps,
}: ValidatedTextareaProps) => {
  return (
    <Textarea
      label={label}
      placeholder={placeholder}
      value={value}
      error={touched && error ? error : undefined}
      onChange={(e) => onChange(name, e.target.value)}
      onBlur={() => onBlur(name)}
      {...textareaProps}
    />
  );
};

/**
 * Form component with validation
 */
export interface FormProps<T extends Record<string, any>> {
  initialValues: T;
  validationRules: Record<keyof T, ValidationRule>;
  onSubmit: (values: T) => Promise<void> | void;
  children: (form: ReturnType<typeof useFormValidation<T>>) => ReactNode;
}

export const Form = <T extends Record<string, any>>({
  initialValues,
  validationRules,
  onSubmit,
  children,
}: FormProps<T>) => {
  const form = useFormValidation(initialValues, validationRules);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await form.handleSubmit(onSubmit);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {children(form)}
    </form>
  );
};

export default {
  useFormValidation,
  ValidatedInput,
  ValidatedSelect,
  ValidatedTextarea,
  Form,
};
