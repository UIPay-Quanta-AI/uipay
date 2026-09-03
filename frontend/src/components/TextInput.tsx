import { forwardRef } from 'react';

interface TextInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export const TextInput = forwardRef<HTMLInputElement, TextInputProps>(
  ({ label, error, className = '', ...props }, ref) => (
    <div className="flex flex-col gap-2">
      {label && (
        <label className="text-sm text-[var(--color-light)]">{label}</label>
      )}
      <input
        ref={ref}
        className={`rounded-xl border border-white/20 bg-transparent px-4 py-3 text-[var(--color-light)] placeholder:text-white/30 focus:border-[var(--color-primary)] focus:outline-none ${className}`}
        {...props}
      />
      {error && <p className="text-sm text-red-400">{error}</p>}
    </div>
  ),
);

TextInput.displayName = 'TextInput';
