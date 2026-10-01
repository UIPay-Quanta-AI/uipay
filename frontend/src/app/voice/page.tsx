'use client';

import { Mic, Settings, Square } from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { useAudioRecorder } from '@/hooks/useAudioRecorder';
import { getVoicePreference } from '@/lib/voicePreference';
import { getApiErrorMessage } from '@/services/api';
import {
  quantaVoiceInteract,
  resolveTransferBeneficiary,
  type BeneficiaryNotFoundData,
  type ResolvedTransferRecipient,
  type TransferPreparationData,
  type VoicePipelineResult,
} from '@/services/quanta';
import { useAuthHydration, useAuthStore } from '@/store/auth';
import { useSendStore } from '@/store/send';

const OUTCOME_MESSAGE: Record<string, string> = {
  verification_unavailable:
    "I couldn't verify your voice - enroll it in Settings first so I can recognize you.",
  verification_failed:
    "That didn't sound like your enrolled voice, so I can't act on it - use manual entry instead.",
  transcription_failed: "I didn't catch that - try again, a little closer to the mic.",
};

function formatNaira(amount: number) {
  return `₦${amount.toLocaleString('en-NG', { minimumFractionDigits: 2 })}`;
}

export default function VoicePage() {
  const router = useRouter();
  const hasHydrated = useAuthHydration();
  const accessToken = useAuthStore((state) => state.accessToken);

  const { status: recorderStatus, errorMessage: recorderError, start, stop } = useAudioRecorder();
  const [isProcessing, setIsProcessing] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [callError, setCallError] = useState<string | null>(null);
  const [result, setResult] = useState<VoicePipelineResult | null>(null);
  const [pendingTransfer, setPendingTransfer] = useState<ResolvedTransferRecipient | null>(null);
  const [resolvingTransfer, setResolvingTransfer] = useState(false);
  const setSource = useSendStore((state) => state.setSource);
  const setAmount = useSendStore((state) => state.setAmount);

  useEffect(() => {
    if (hasHydrated && !accessToken) {
      router.replace('/signin');
    }
  }, [hasHydrated, accessToken, router]);

  // The actual processing is one long blocking call with no server-sent
  // progress - this is real elapsed time, not a fake staged animation, so
  // it stays honest about how long it's actually taking instead of
  // guessing at a stage that may not match reality.
  useEffect(() => {
    if (!isProcessing) {
      setElapsedSeconds(0);
      return;
    }
    const timer = setInterval(() => setElapsedSeconds((s) => s + 1), 1000);
    return () => clearInterval(timer);
  }, [isProcessing]);

  const transferData =
    result?.outcome === 'success' &&
    result.response?.ui.type === 'transfer_confirmation' &&
    result.response.data?.beneficiary_id
      ? (result.response.data as unknown as TransferPreparationData)
      : null;

  const beneficiaryNotFoundData =
    result?.outcome === 'success' &&
    result.response?.status === 'input_required' &&
    result.response.ui.type === 'beneficiary_selection'
      ? (result.response.data as unknown as BeneficiaryNotFoundData)
      : null;

  useEffect(() => {
    if (!transferData) {
      setPendingTransfer(null);
      return;
    }

    let cancelled = false;
    setResolvingTransfer(true);
    resolveTransferBeneficiary(transferData.beneficiary_id)
      .then((recipient) => {
        if (!cancelled) setPendingTransfer(recipient);
      })
      .catch((err) => {
        if (!cancelled) setCallError(getApiErrorMessage(err));
      })
      .finally(() => {
        if (!cancelled) setResolvingTransfer(false);
      });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [transferData?.beneficiary_id]);

  const handleReviewTransfer = () => {
    if (!pendingTransfer || !transferData) return;
    setSource({
      method: 'wallet',
      recipientId: pendingTransfer.recipientId,
      name: pendingTransfer.name,
      detail: pendingTransfer.accountNumber,
    });
    setAmount(transferData.amount);
    router.push('/send/confirm');
  };

  const handleTap = async () => {
    if (recorderStatus === 'recording') {
      const blob = await stop();
      if (!blob) return;

      setIsProcessing(true);
      setCallError(null);
      setResult(null);
      try {
        const preference = getVoicePreference();
        const response = await quantaVoiceInteract(blob, preference.language);
        setResult(response);
      } catch (err) {
        setCallError(getApiErrorMessage(err));
      } finally {
        setIsProcessing(false);
      }
      return;
    }

    setResult(null);
    setCallError(null);
    await start();
  };

  const isListening = recorderStatus === 'recording';
  const isBusy = recorderStatus === 'requesting' || isProcessing;

  const replyText =
    result?.outcome === 'success'
      ? result.response?.speech?.text
      : result
        ? OUTCOME_MESSAGE[result.outcome]
        : null;

  if (!hasHydrated || !accessToken) return null;

  return (
    <main className="relative flex h-screen w-screen flex-col items-center overflow-hidden bg-[var(--color-dark)] px-6 py-10">
      <div className="pointer-events-none absolute -left-32 -top-32 h-96 w-96 rounded-full bg-[var(--color-primary)] opacity-30 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-32 -right-32 h-96 w-96 rounded-full bg-[var(--color-primary)] opacity-30 blur-3xl" />

      <div className="relative z-10 flex w-full justify-end">
        <Link
          href="/voice/settings"
          aria-label="Quanta AI Settings"
          className="flex h-10 w-10 items-center justify-center rounded-full bg-[rgba(var(--color-primary-rgb),0.15)] text-[var(--color-primary)]"
        >
          <Settings className="h-5 w-5" />
        </Link>
      </div>

      <div className="relative z-10 flex h-full w-full flex-col items-center overflow-y-auto">
        <button
          type="button"
          onClick={handleTap}
          disabled={isBusy}
          className="mt-24 flex h-64 w-64 items-center justify-center rounded-full bg-[rgba(var(--color-primary-rgb),0.12)] transition-transform active:scale-95 disabled:opacity-60"
        >
          {isListening ? (
            <Square className="h-20 w-20 text-[var(--color-primary)]" />
          ) : (
            <Mic className="h-24 w-24 text-[var(--color-primary)]" />
          )}
        </button>

        <p className="animate-rise-in mt-10 text-xl text-[var(--color-light)]">
          {isListening
            ? 'Listening - tap to stop'
            : isProcessing
              ? `Thinking... (${elapsedSeconds}s)`
              : 'Tap To Speak'}
        </p>

        {isProcessing && elapsedSeconds >= 8 && (
          <p className="animate-rise-in mt-2 max-w-xs text-center text-sm text-white/40">
            Still working - verifying your voice, transcribing, and asking
            Quanta can take a while, especially right after a restart.
          </p>
        )}

        {result?.transcript && (
          <p className="animate-rise-in mt-4 max-w-xs text-center text-white/60">
            &ldquo;{result.transcript.text}&rdquo;
          </p>
        )}

        {replyText && (
          <p className="animate-rise-in mt-4 max-w-xs text-center text-[var(--color-light)]">
            {replyText}
          </p>
        )}

        {transferData && (
          <div className="animate-rise-in mt-4 w-full max-w-xs rounded-2xl bg-[#0d1929] p-5 text-[var(--color-light)]">
            <div className="flex justify-between">
              <span className="text-white/50">Amount</span>
              <span className="font-semibold">{formatNaira(transferData.amount)}</span>
            </div>
            <div className="mt-2 flex justify-between">
              <span className="text-white/50">To</span>
              <span className="font-semibold">
                {resolvingTransfer ? 'Looking up...' : (pendingTransfer?.name ?? 'Unknown')}
              </span>
            </div>
            <button
              type="button"
              onClick={handleReviewTransfer}
              disabled={!pendingTransfer}
              className="mt-4 w-full rounded-full bg-[var(--color-primary)] py-3 font-semibold text-[var(--color-dark)] transition-transform active:scale-95 disabled:opacity-50"
            >
              Review & Confirm
            </button>
          </div>
        )}

        {beneficiaryNotFoundData && (
          <div className="animate-rise-in mt-4 w-full max-w-xs rounded-2xl bg-[#0d1929] p-5 text-center text-[var(--color-light)]">
            <p className="text-sm text-white/60">
              We couldn&apos;t find a saved contact named &ldquo;
              {beneficiaryNotFoundData.name_heard}&rdquo;.
            </p>
            <button
              type="button"
              onClick={() =>
                router.push(
                  `/send/uipay/beneficiaries/add?nickname=${encodeURIComponent(beneficiaryNotFoundData.name_heard)}`,
                )
              }
              className="mt-4 w-full rounded-full bg-[var(--color-primary)] py-3 font-semibold text-[var(--color-dark)] transition-transform active:scale-95"
            >
              Add As Beneficiary
            </button>
          </div>
        )}

        {(recorderError || callError) && (
          <p className="animate-rise-in mt-6 max-w-xs text-center text-sm text-red-400">
            {recorderError ?? callError}
          </p>
        )}

        <div className="mt-auto flex w-full flex-col gap-4">
          <button
            type="button"
            onClick={() => router.push('/send/uipay')}
            className="rounded-full bg-[rgba(var(--color-primary-rgb),0.15)] py-4 font-semibold text-[var(--color-primary)] transition-transform active:scale-95"
          >
            Switch To Manual Entry
          </button>
          <button
            type="button"
            onClick={() => router.push('/dashboard')}
            className="text-center text-white/50 underline"
          >
            Cancel
          </button>
        </div>
      </div>
    </main>
  );
}
