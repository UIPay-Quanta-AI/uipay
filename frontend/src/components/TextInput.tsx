import { forwardRef } from 'react';

interface TextInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  // "outline" matches the signup/signin fields, "filled" matches the
  // forgot-password screens' solid green boxes
  variant?: 'outline' | 'filled';
}

const VARIANT_CLASSES: Record<NonNullable<TextInputProps['variant']>, string> = {
  outline:
    'border border-white/20 bg-transparent focus:border-[var(--color-primary)]',
  filled:
    'border-none bg-[rgba(var(--color-primary-rgb),0.15)] focus:ring-2 focus:ring-[var(--color-primary)]',
};

export const TextInput = forwardRef<HTMLInputElement, TextInputProps>(
  ({ label, error, variant = 'outline', className = '', ...props }, ref) => (
    <div className="flex flex-col gap-2">
      {label && (
        <label className="text-sm text-[var(--color-light)]">{label}</label>
      )}
      <input
        ref={ref}
        className={`rounded-xl px-4 py-4 text-[var(--color-light)] placeholder:text-white/40 focus:outline-none ${VARIANT_CLASSES[variant]} ${className}`}
        {...props}
      />
      {error && <p className="text-sm text-red-400">{error}</p>}
    </div>
  ),
);

TextInput.displayName = 'TextInput';
