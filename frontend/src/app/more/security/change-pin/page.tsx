'use client';

import { CheckCircle2 } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { BackButton } from '@/components/BackButton';
import { GlowBackground } from '@/components/GlowBackground';
import { PinInput } from '@/components/PinInput';
import api, { getApiErrorMessage } from '@/services/api';
import { useAuthHydration, useAuthStore } from '@/store/auth';

const PIN_LENGTH = 4;
const EMPTY = Array(PIN_LENGTH).fill('');

type Step = 'current' | 'create' | 'confirm' | 'done';

const COPY: Record<Step, { title: string; subtitle: string }> = {
  current: {
    title: 'Confirm Current PIN',
    subtitle: 'Enter your current 4-digit PIN',
  },
  create: {
    title: 'Create New PIN',
    subtitle: 'Choose a new 4-digit PIN',
  },
  confirm: {
    title: 'Confirm New PIN',
    subtitle: 'Enter the same 4 digits again',
  },
  done: { title: '', subtitle: '' },
};

export default function ChangePinPage() {
  const router = useRouter();
  const hasHydrated = useAuthHydration();
  const accessToken = useAuthStore((state) => state.accessToken);

  const [step, setStep] = useState<Step>('current');
  const [current, setCurrent] = useState<string[]>(EMPTY);
  const [next, setNext] = useState<string[]>(EMPTY);
  const [confirm, setConfirm] = useState<string[]>(EMPTY);
  const [error, setError] = useState<string | null>(null);
  const [shake, setShake] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (hasHydrated && !accessToken) {
      router.replace('/signin');
    }
  }, [hasHydrated, accessToken, router]);

  const fail = (message: string, reset: () => void) => {
    setError(message);
    setShake(true);
    setTimeout(() => setShake(false), 500);
    reset();
  };

  useEffect(() => {
    if (step !== 'current' || !current.every((d) => d !== '') || isSubmitting) {
      return;
    }
    setIsSubmitting(true);
    setError(null);
    api
      .post('/profile/pin/verify', { pin: current.join('') })
      .then(() => {
        setStep('create');
        setIsSubmitting(false);
      })
      .catch((err) => {
        fail(getApiErrorMessage(err), () => setCurrent(EMPTY));
        setIsSubmitting(false);
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [current]);

  useEffect(() => {
    if (step === 'create' && next.every((d) => d !== '')) {
      setStep('confirm');
    }
  }, [next, step]);

  useEffect(() => {
    if (
      step !== 'confirm' ||
      !confirm.every((d) => d !== '') ||
      isSubmitting
    ) {
      return;
    }

    if (next.join('') !== confirm.join('')) {
      fail("PINs don't match, try again", () => {
        setNext(EMPTY);
        setConfirm(EMPTY);
        setStep('create');
      });
      return;
    }

    setIsSubmitting(true);
    setError(null);
    api
      .post('/profile/pin', { pin: next.join('') })
      .then(() => setStep('done'))
      .catch((err) => {
        setError(getApiErrorMessage(err));
        setIsSubmitting(false);
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [confirm]);

  if (!hasHydrated || !accessToken) return null;

  if (step === 'done') {
    return (
      <GlowBackground className="flex flex-col items-center px-6 py-16">
        <span className="animate-pop-in flex h-24 w-24 items-center justify-center rounded-full bg-[var(--color-primary)]">
          <CheckCircle2 className="h-12 w-12 text-[var(--color-dark)]" />
        </span>
        <h1 className="animate-rise-in mt-6 text-xl font-bold text-[var(--color-light)]">
          PIN Updated
        </h1>
        <button
          type="button"
          onClick={() => router.push('/more/security')}
          className="mt-auto mb-6 w-full rounded-full bg-[var(--color-primary)] py-4 font-semibold text-[var(--color-dark)]"
        >
          Done
        </button>
      </GlowBackground>
    );
  }

  return (
    <GlowBackground className="flex flex-col items-center px-6 py-10">
      <div className="w-full">
        <BackButton />
      </div>

      <h1 className="animate-rise-in mt-8 text-center text-2xl font-bold text-[var(--color-light)]">
        {COPY[step].title}
      </h1>
      <p className="animate-rise-in mt-2 text-center text-white/60">
        {COPY[step].subtitle}
      </p>

      <div className="mt-10">
        {step === 'current' && (
          <PinInput
            key="current"
            digits={current}
            onChange={setCurrent}
            autoFocus
            shake={shake}
            disabled={isSubmitting}
          />
        )}
        {step === 'create' && (
          <PinInput key="create" digits={next} onChange={setNext} autoFocus />
        )}
        {step === 'confirm' && (
          <PinInput
            key="confirm"
            digits={confirm}
            onChange={setConfirm}
            autoFocus
            shake={shake}
            disabled={isSubmitting}
          />
        )}
      </div>

      {error && <p className="mt-4 text-sm text-red-400">{error}</p>}
      {isSubmitting && !error && (
        <p className="mt-4 text-sm text-white/40">Please wait...</p>
      )}
    </GlowBackground>
  );
}
