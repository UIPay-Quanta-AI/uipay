'use client';

import { useRouter, useSearchParams } from 'next/navigation';
import { useEffect, useState } from 'react';
import { BackButton } from '@/components/BackButton';
import { GlowBackground } from '@/components/GlowBackground';
import { TextInput } from '@/components/TextInput';
import api, { getApiErrorMessage } from '@/services/api';
import { useAuthHydration, useAuthStore } from '@/store/auth';

// only UIPay-to-UIPay transfers are real right now (no external bank
// integration yet), so this is the only bank on offer
const BANK_NAME = 'UIPay';

export default function AddBeneficiaryPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const hasHydrated = useAuthHydration();
  const accessToken = useAuthStore((state) => state.accessToken);

  const [accountNumber, setAccountNumber] = useState('');
  const [accountName, setAccountName] = useState<string | null>(null);
  // Quanta sometimes gets here by voice, when it heard a name it has no
  // saved beneficiary for - prefilling saves retyping what was already said.
  const [nickname, setNickname] = useState(searchParams.get('nickname') ?? '');
  const [resolveError, setResolveError] = useState<string | null>(null);
  const [isResolving, setIsResolving] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (hasHydrated && !accessToken) {
      router.replace('/signin');
    }
  }, [hasHydrated, accessToken, router]);

  useEffect(() => {
    if (accountNumber.length !== 10) {
      setAccountName(null);
      setResolveError(null);
      return;
    }

    let cancelled = false;
    setIsResolving(true);
    setResolveError(null);

    const timer = setTimeout(() => {
      api
        .get(`/wallet/resolve/${accountNumber}`)
        .then((res) => {
          if (cancelled) return;
          setAccountName(res.data.data.accountName);
        })
        .catch((err) => {
          if (cancelled) return;
          setAccountName(null);
          setResolveError(getApiErrorMessage(err));
        })
        .finally(() => {
          if (!cancelled) setIsResolving(false);
        });
    }, 400);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [accountNumber]);

  const handleSave = async () => {
    if (!accountName || !nickname.trim()) return;

    setSubmitError(null);
    setIsSubmitting(true);
    try {
      await api.post('/beneficiaries', {
        nickname: nickname.trim(),
        accountNumber,
        bankName: BANK_NAME,
      });
      router.push('/send/uipay');
    } catch (err) {
      setSubmitError(getApiErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!hasHydrated || !accessToken) return null;

  return (
    <GlowBackground className="flex flex-col px-6 py-10">
      <div className="flex items-center justify-center">
        <div className="absolute left-6">
          <BackButton />
        </div>
        <h1 className="text-2xl font-bold text-[var(--color-light)]">
          Add Beneficiary
        </h1>
      </div>

      <div className="mt-8 flex flex-col gap-4">
        <div className="flex flex-col gap-2">
          <label className="text-[var(--color-light)]">Account Number</label>
          <TextInput
            variant="filled"
            value={accountNumber}
            onChange={(event) =>
              setAccountNumber(
                event.target.value.replace(/\D/g, '').slice(0, 10),
              )
            }
            inputMode="numeric"
          />
        </div>

        <div className="flex flex-col gap-2">
          <label className="text-[var(--color-light)]">Bank Name</label>
          <div className="rounded-xl border border-white/20 px-4 py-3 text-[var(--color-light)]">
            {BANK_NAME}
          </div>
        </div>

        <div className="flex flex-col gap-2">
          <label className="text-[var(--color-light)]">Account Name</label>
          <TextInput
            variant="filled"
            value={
              isResolving ? 'Looking up...' : (accountName ?? '')
            }
            readOnly
            placeholder="Enter a valid account number above"
          />
          {resolveError && (
            <p className="text-sm text-red-400">{resolveError}</p>
          )}
        </div>

        <div className="flex flex-col gap-2">
          <label className="text-[var(--color-light)]">
            Nickname (for Quanta AI)
          </label>
          <TextInput
            variant="filled"
            value={nickname}
            onChange={(event) => setNickname(event.target.value)}
          />
        </div>
      </div>

      {submitError && (
        <p className="mt-4 text-sm text-red-400">{submitError}</p>
      )}

      <button
        type="button"
        onClick={handleSave}
        disabled={!accountName || !nickname.trim() || isSubmitting}
        className="mt-auto mb-6 rounded-full bg-[var(--color-primary)] py-4 font-semibold uppercase text-[var(--color-dark)] disabled:opacity-40"
      >
        {isSubmitting ? 'Saving...' : 'Save'}
      </button>
    </GlowBackground>
  );
}
