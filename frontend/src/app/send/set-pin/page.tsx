'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { BackButton } from '@/components/BackButton';
import { GlowBackground } from '@/components/GlowBackground';
import { PinInput } from '@/components/PinInput';
import api, { getApiErrorMessage } from '@/services/api';
import { useAuthHydration, useAuthStore } from '@/store/auth';
import { useSendStore } from '@/store/send';

const PIN_LENGTH = 4;

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
  const [shake, setShake] = useState(false);
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
        setShake(true);
        setTimeout(() => setShake(false), 500);
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
    <GlowBackground className="flex flex-col items-center px-6 py-10">
      <div className="w-full">
        <BackButton />
      </div>

      <h1 className="animate-rise-in mt-8 text-center text-3xl font-bold text-[var(--color-light)]">
        {step === 'create' ? 'Create Transaction PIN' : 'Confirm Your PIN'}
      </h1>
      <p
        className="animate-rise-in mt-2 text-center text-white/60"
        style={{ animationDelay: '0.05s' }}
      >
        {step === 'create'
          ? 'This PIN authorizes every payment you make'
          : 'Enter the same 4 digits again'}
      </p>

      <div className="animate-rise-in mt-12" style={{ animationDelay: '0.1s' }}>
        {step === 'create' ? (
          <PinInput
            key="create"
            digits={pin}
            onChange={setPin}
            autoFocus
            shake={shake}
          />
        ) : (
          <PinInput
            key="confirm"
            digits={confirmPin}
            onChange={setConfirmPin}
            autoFocus
            shake={shake}
            disabled={isSubmitting}
          />
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
