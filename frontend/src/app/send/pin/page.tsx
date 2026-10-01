'use client';

import { Fingerprint } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { GlowBackground } from '@/components/GlowBackground';
import { PinInput } from '@/components/PinInput';
import api, { getApiErrorMessage } from '@/services/api';
import { useAuthHydration, useAuthStore } from '@/store/auth';
import { useSendStore } from '@/store/send';

const PIN_LENGTH = 4;

export default function EnterPinPage() {
  const router = useRouter();
  const hasHydrated = useAuthHydration();
  const accessToken = useAuthStore((state) => state.accessToken);
  const source = useSendStore((state) => state.source);
  const amount = useSendStore((state) => state.amount);
  const setLastTransaction = useSendStore((state) => state.setLastTransaction);
  const setLastError = useSendStore((state) => state.setLastError);

  const [digits, setDigits] = useState<string[]>(Array(PIN_LENGTH).fill(''));
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [shake, setShake] = useState(false);

  useEffect(() => {
    if (hasHydrated && !accessToken) {
      router.replace('/signin');
    }
  }, [hasHydrated, accessToken, router]);

  useEffect(() => {
    if (hasHydrated && accessToken && (!source || !amount)) {
      router.replace('/send');
    }
  }, [hasHydrated, accessToken, source, amount, router]);

  useEffect(() => {
    if (digits.every((d) => d !== '') && !isSubmitting && source && amount) {
      setIsSubmitting(true);
      setError(null);

      const pin = digits.join('');
      const request =
        source.method === 'wallet'
          ? api.post('/wallet/transfer', {
              recipientId: source.recipientId,
              amount,
              pin,
            })
          : source.method === 'nfc'
            ? api.post('/nfc/pay', { tagId: source.tagId, amount, pin })
            : api.post('/qr/pay', { qrCode: source.qrCode, amount, pin });

      request
        .then((res) => {
          setLastTransaction({
            amount,
            name: source.name,
            reference: res.data.data.reference,
            date: res.data.data.createdAt ?? new Date().toISOString(),
          });
          router.push('/send/success');
        })
        .catch((err) => {
          const message = getApiErrorMessage(err);
          // a mistyped PIN is by far the most common failure and deserves
          // an immediate retry right here - anything else (insufficient
          // balance, no wallet, etc) goes to the real failure screen
          if (message === 'Incorrect PIN') {
            setError(message);
            setShake(true);
            setTimeout(() => setShake(false), 500);
            setDigits(Array(PIN_LENGTH).fill(''));
            setIsSubmitting(false);
            return;
          }

          setLastError(message);
          router.push('/send/failure');
        });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [digits]);

  if (!hasHydrated || !accessToken || !source || !amount) return null;

  return (
    <GlowBackground className="flex flex-col items-center px-6 py-10">
      <div className="relative mt-16 flex h-20 w-20 items-center justify-center rounded-full bg-[rgba(var(--color-primary-rgb),0.12)]">
        <Fingerprint className="h-10 w-10 text-[var(--color-primary)]" />
      </div>

      <h1 className="animate-rise-in mt-8 text-3xl font-bold text-[var(--color-light)]">
        Enter Pin
      </h1>
      <p
        className="animate-rise-in mt-2 text-white/50"
        style={{ animationDelay: '0.05s' }}
      >
        Authorize this payment of{' '}
        <span className="text-[var(--color-primary)]">
          ₦{amount.toLocaleString('en-NG', { minimumFractionDigits: 2 })}
        </span>
      </p>

      <div className="animate-rise-in mt-10" style={{ animationDelay: '0.1s' }}>
        <PinInput
          digits={digits}
          onChange={setDigits}
          autoFocus
          shake={shake}
          disabled={isSubmitting}
        />
      </div>

      {error && (
        <p className="mt-4 text-sm text-red-400">{error}</p>
      )}
      {isSubmitting && !error && (
        <p className="mt-4 text-sm text-white/40">Processing payment...</p>
      )}

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
