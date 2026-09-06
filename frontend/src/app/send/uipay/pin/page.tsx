'use client';

import { Fingerprint } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';
import { GlowBackground } from '@/components/GlowBackground';
import api, { getApiErrorMessage } from '@/services/api';
import { useAuthHydration, useAuthStore } from '@/store/auth';
import { useSendStore } from '@/store/send';

const PIN_LENGTH = 4;

export default function EnterPinPage() {
  const router = useRouter();
  const hasHydrated = useAuthHydration();
  const accessToken = useAuthStore((state) => state.accessToken);
  const recipient = useSendStore((state) => state.recipient);
  const amount = useSendStore((state) => state.amount);
  const setLastTransaction = useSendStore((state) => state.setLastTransaction);
  const setLastError = useSendStore((state) => state.setLastError);

  const [digits, setDigits] = useState<string[]>(Array(PIN_LENGTH).fill(''));
  const [isSubmitting, setIsSubmitting] = useState(false);
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

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
    if (digits.every((d) => d !== '') && !isSubmitting && recipient && amount) {
      setIsSubmitting(true);
      api
        .post('/wallet/transfer', {
          recipientId: recipient.userId,
          amount,
          pin: digits.join(''),
        })
        .then((res) => {
          setLastTransaction({
            amount,
            accountName: recipient.accountName,
            reference: res.data.data.reference,
          });
          router.push('/send/uipay/success');
        })
        .catch((err) => {
          setLastError(getApiErrorMessage(err));
          router.push('/send/uipay/failure');
        });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [digits]);

  const handleChange = (index: number, value: string) => {
    const digit = value.replace(/\D/g, '').slice(-1);
    const next = [...digits];
    next[index] = digit;
    setDigits(next);
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

  if (!hasHydrated || !accessToken || !recipient || !amount) return null;

  return (
    <GlowBackground className="flex flex-col items-center px-6 py-10">
      <h1 className="mt-16 text-3xl font-bold text-[var(--color-light)]">
        Enter Pin
      </h1>

      <div className="mt-10 flex gap-3">
        {digits.map((digit, index) => (
          <input
            key={index}
            ref={(el) => {
              inputRefs.current[index] = el;
            }}
            value={digit}
            onChange={(event) => handleChange(index, event.target.value)}
            onKeyDown={(event) => handleKeyDown(index, event)}
            inputMode="numeric"
            maxLength={1}
            type="password"
            disabled={isSubmitting}
            className="h-16 w-14 rounded-xl border border-[rgba(var(--color-primary-rgb),0.5)] bg-[rgba(var(--color-primary-rgb),0.1)] text-center text-2xl font-bold text-[var(--color-primary)] focus:border-[var(--color-primary)] focus:outline-none disabled:opacity-50"
          />
        ))}
      </div>

      {isSubmitting && (
        <p className="mt-6 text-sm text-white/40">Processing payment...</p>
      )}

      <Fingerprint className="mt-16 h-10 w-10 text-[var(--color-primary)]" />

      <button
        type="button"
        onClick={() => router.push('/dashboard')}
        className="mt-auto mb-6 text-center text-white/50 underline"
      >
        Cancel
      </button>
    </GlowBackground>
  );
}
