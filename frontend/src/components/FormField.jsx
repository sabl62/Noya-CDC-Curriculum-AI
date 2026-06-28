import React, { forwardRef } from "react";

/**
 * Labeled form field. Centralizes the input chrome shared by
 * Login and SignUp so the two screens can't drift out of sync,
 * and so accessibility (label association, autocomplete) is
 * correct in exactly one place.
 */
const FormField = forwardRef(
  (
    {
      id,
      label,
      type = "text",
      value,
      onChange,
      placeholder,
      autoComplete,
      inputMode,
      required = false,
      error,
      trailing,
      spellCheck,
    },
    ref
  ) => {
    const errorId = error ? `${id}-error` : undefined;

    return (
      <div>
        <label
          htmlFor={id}
          className="mb-1.5 block text-[13px] font-semibold tracking-wide text-[var(--ink-soft)]"
        >
          {label}
        </label>
        <div className="relative">
          <input
            ref={ref}
            id={id}
            name={id}
            type={type}
            inputMode={inputMode}
            value={value}
            onChange={onChange}
            onPaste={undefined}
            required={required}
            autoComplete={autoComplete}
            spellCheck={spellCheck}
            aria-invalid={error ? "true" : undefined}
            aria-describedby={errorId}
            placeholder={placeholder}
            className="field-input w-full rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--surface)] px-4 py-3 text-[15px] text-[var(--ink)] outline-none transition-colors duration-150 placeholder:text-[var(--ink-faint)] focus-visible:border-[var(--pine)] focus-visible:ring-2 focus-visible:ring-[var(--pine)]/25"
          />
          {trailing}
        </div>
        {error && (
          <p id={errorId} role="alert" className="mt-1.5 text-[13px] font-medium text-[var(--error)]">
            {error}
          </p>
        )}
      </div>
    );
  }
);

FormField.displayName = "FormField";

export default FormField;
