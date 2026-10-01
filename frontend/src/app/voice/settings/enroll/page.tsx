'use client';

import { Mic, Square } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { BackButton } from '@/components/BackButton';
import { GlowBackground } from '@/components/GlowBackground';
import { useAudioRecorder } from '@/hooks/useAudioRecorder';
import { getApiErrorMessage } from '@/services/api';
import { quantaVoiceEnroll } from '@/services/quanta';
import { useAuthHydration, useAuthStore } from '@/store/auth';

export default function VoiceEnrollPage() {
  const router = useRouter();
  const hasHydrated = useAuthHydration();
  const accessToken = useAuthStore((state) => state.accessToken);

  const { status, errorMessage, start, stop } = useAudioRecorder();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [percentComplete, setPercentComplete] = useState(0);
  const [message, setMessage] = useState(
    'Record a short sample of your voice (a few seconds is enough) to enroll it for voice payments.',
  );
  const [complete, setComplete] = useState(false);

  useEffect(() => {
    if (hasHydrated && !accessToken) {
      router.replace('/signin');
    }
  }, [hasHydrated, accessToken, router]);

  const handleStop = async () => {
    const blob = await stop();
    if (!blob) return;

    setIsSubmitting(true);
    setSubmitError(null);
    try {
      const result = await quantaVoiceEnroll(blob);
      setPercentComplete(result.percent_complete);
      setMessage(result.message);
      setComplete(result.complete);
    } catch (err) {
      setSubmitError(getApiErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!hasHydrated || !accessToken) return null;

  return (
    <GlowBackground className="flex flex-col items-center px-6 py-10">
      <div className="flex w-full items-center gap-4">
        <BackButton />
        <h1 className="text-xl font-bold text-[var(--color-light)]">
          Enroll Your Voice
        </h1>
      </div>

      <div className="mt-6 w-full max-w-xs rounded-2xl bg-[rgba(var(--color-primary-rgb),0.1)] px-4 py-3 text-center">
        <div className="h-2 w-full overflow-hidden rounded-full bg-white/10">
          <div
            className="h-full rounded-full bg-[var(--color-primary)] transition-all"
            style={{ width: `${percentComplete}%` }}
          />
        </div>
        <p className="mt-2 text-sm text-white/60">{percentComplete}% complete</p>
      </div>

      <p className="animate-rise-in mt-10 max-w-xs text-center text-[var(--color-light)]">
        {message}
      </p>

      <button
        type="button"
        onClick={status === 'recording' ? handleStop : start}
        disabled={status === 'requesting' || isSubmitting}
        className="mt-16 flex h-40 w-40 items-center justify-center rounded-full bg-[rgba(var(--color-primary-rgb),0.12)] transition-transform active:scale-95 disabled:opacity-50"
      >
        {status === 'recording' ? (
          <Square className="h-16 w-16 text-[var(--color-primary)]" />
        ) : (
          <Mic className="h-16 w-16 text-[var(--color-primary)]" />
        )}
      </button>

      <p className="mt-4 text-sm text-white/50">
        {status === 'recording'
          ? 'Recording - tap to stop'
          : isSubmitting
            ? 'Processing sample...'
            : 'Tap to record a sample'}
      </p>

      {(errorMessage || submitError) && (
        <p className="mt-4 max-w-xs text-center text-sm text-red-400">
          {errorMessage ?? submitError}
        </p>
      )}

      <div className="mt-auto flex w-full max-w-xs flex-col gap-4 pt-10">
        {complete ? (
          <button
            type="button"
            onClick={() => router.push('/voice/settings')}
            className="rounded-full bg-[var(--color-primary)] py-4 font-semibold uppercase text-[var(--color-dark)]"
          >
            Done
          </button>
        ) : (
          <button
            type="button"
            onClick={() => router.push('/voice/settings')}
            className="text-center text-white/50 underline"
          >
            Cancel
          </button>
        )}
      </div>
    </GlowBackground>
  );
}
