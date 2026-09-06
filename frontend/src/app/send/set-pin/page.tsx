'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { BackButton } from '@/components/BackButton';
import { GlowBackground } from '@/components/GlowBackground';
import api, { getApiErrorMessage } from '@/services/api';
import { useAuthHydration, useAuthStore } from '@/store/auth';
import { useSendStore } from '@/store/send';

const PIN_LENGTH = 4;

function PinBoxes({
  digits,
  onChange,
  autoFocus,
}: {
  digits: string[];
  onChange: (digits: string[]) => void;
  autoFocus?: boolean;
}) {
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

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
    <div className="flex justify-center gap-3">
      {digits.map((digit, index) => (
        <input
          key={index}
          ref={(el) => {
            inputRefs.current[index] = el;
            if (autoFocus && index === 0) el?.focus();
          }}
          value={digit}
          onChange={(event) => handleChange(index, event.target.value)}
          onKeyDown={(event) => handleKeyDown(index, event)}
          inputMode="numeric"
          maxLength={1}
          type="password"
          className="h-16 w-14 rounded-xl border border-[rgba(var(--color-primary-rgb),0.5)] bg-[rgba(var(--color-primary-rgb),0.1)] text-center text-2xl font-bold text-[var(--color-primary)] focus:border-[var(--color-primary)] focus:outline-none"
        />
      ))}
    </div>
  );
}

export default function SetPinPage() {
  const router = useRouter();
  const hasHydrated = useAuthHydration();
  const accessToken = useAuthStore((state) => state.accessToken);
  const recipient = useSendStore((state) => state.recipient);
  const amount = useSendStore((state) => state.amount);

  const [pin, setPin] = useState<string[]>(Array(PIN_LENGTH).fill(''));
  const [confirmPin, setConfirmPin] = useState<string[]>(
    Array(PIN_LENGTH).fill(''),
  );
  const [step, setStep] = useState<'create' | 'confirm'>('create');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (hasHydrated && !accessToken) {
      router.replace('/signin');
    }
  }, [hasHydrated, accessToken, router]);

  useEffect(() => {
    if (hasHydrated && accessToken && (!recipient || !amount)) {
      router.replace('/send/uipay');
    }
  }, [hasHydrated, accessToken, recipient, amount, router]);

  useEffect(() => {
    if (step === 'create' && pin.every((d) => d !== '')) {
      setStep('confirm');
    }
  }, [pin, step]);

  useEffect(() => {
    if (
      step === 'confirm' &&
      confirmPin.every((d) => d !== '') &&
      !isSubmitting
    ) {
      if (pin.join('') !== confirmPin.join('')) {
        setError("PINs don't match, try again");
        setPin(Array(PIN_LENGTH).fill(''));
        setConfirmPin(Array(PIN_LENGTH).fill(''));
        setStep('create');
        return;
      }

      setError(null);
      setIsSubmitting(true);
      api
        .post('/profile/pin', { pin: pin.join('') })
        .then(() => router.push('/send/uipay/pin'))
        .catch((err) => {
          setError(getApiErrorMessage(err));
          setIsSubmitting(false);
        });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [confirmPin]);

  if (!hasHydrated || !accessToken || !recipient || !amount) return null;

  return (
    <GlowBackground className="flex flex-col px-6 py-10">
      <BackButton />

      <h1 className="mt-8 text-center text-3xl font-bold text-[var(--color-light)]">
        {step === 'create' ? 'Create Transaction PIN' : 'Confirm Your PIN'}
      </h1>
      <p className="mt-2 text-center text-white/60">
        {step === 'create'
          ? 'This PIN authorizes every payment you make'
          : 'Enter the same 4 digits again'}
      </p>

      <div className="mt-10">
        {step === 'create' ? (
          <PinBoxes digits={pin} onChange={setPin} autoFocus />
        ) : (
          <PinBoxes digits={confirmPin} onChange={setConfirmPin} autoFocus />
        )}
      </div>

      {error && (
        <p className="mt-4 text-center text-sm text-red-400">{error}</p>
      )}
      {isSubmitting && (
        <p className="mt-4 text-center text-sm text-white/40">Saving...</p>
      )}
    </GlowBackground>
  );
}
