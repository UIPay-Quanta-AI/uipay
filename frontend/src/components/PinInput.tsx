'use client';

import { useEffect, useRef } from 'react';

const PIN_LENGTH = 4;

// dot-style PIN entry - real inputs underneath capture keystrokes/backspace
// navigation as usual, but the actual digit stays hidden behind a filled
// dot (text-transparent + caret-transparent) rather than showing through
// like a plain password box would, matching typical banking-app PIN UX
export function PinInput({
  digits,
  onChange,
  autoFocus,
  shake,
  disabled,
}: {
  digits: string[];
  onChange: (digits: string[]) => void;
  autoFocus?: boolean;
  shake?: boolean;
  disabled?: boolean;
}) {
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  // runs once on mount only - doing this inside the ref callback instead
  // (as a previous version of this component did) re-fires on every
  // re-render, since inline arrow-function refs get a new identity each
  // render and React detaches/reattaches them. That stole focus back to
  // box 0 immediately after auto-advancing to box 1, so typing the second
  // digit required manually tapping into the next box.
  useEffect(() => {
    if (autoFocus) {
      inputRefs.current[0]?.focus();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleChange = (index: number, value: string) => {
    const digit = value.replace(/\D/g, '').slice(-1);
    const next = [...digits];
    next[index] = digit;
    onChange(next);
    if (digit && index < PIN_LENGTH - 1) {
      inputRefs.current[index + 1]?.focus();
    }
  };

  const handleKeyDown = (
    index: number,
    event: React.KeyboardEvent<HTMLInputElement>,
  ) => {
    if (event.key === 'Backspace' && !digits[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  };

  return (
    <div className={`flex justify-center gap-4 ${shake ? 'animate-shake' : ''}`}>
      {digits.map((digit, index) => (
        <div key={index} className="relative h-16 w-16">
          <input
            ref={(el) => {
              inputRefs.current[index] = el;
            }}
            value={digit}
            onChange={(event) => handleChange(index, event.target.value)}
            onKeyDown={(event) => handleKeyDown(index, event)}
            inputMode="numeric"
            maxLength={1}
            disabled={disabled}
            className="absolute inset-0 h-full w-full rounded-2xl border-2 border-[rgba(var(--color-primary-rgb),0.3)] bg-[rgba(var(--color-primary-rgb),0.08)] text-center text-transparent caret-transparent focus:border-[var(--color-primary)] focus:outline-none disabled:opacity-50"
          />
          <span
            key={digit ? `filled-${index}` : `empty-${index}`}
            className={`pointer-events-none absolute inset-0 flex items-center justify-center ${
              digit ? 'animate-dot-fill' : ''
            }`}
          >
            {digit && (
              <span className="h-4 w-4 rounded-full bg-[var(--color-primary)] shadow-[0_0_12px_rgba(var(--color-primary-rgb),0.6)]" />
            )}
          </span>
        </div>
      ))}
    </div>
  );
}
