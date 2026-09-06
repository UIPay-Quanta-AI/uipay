'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { BackButton } from '@/components/BackButton';
import { GlowBackground } from '@/components/GlowBackground';
import { TextInput } from '@/components/TextInput';
import api, { getApiErrorMessage } from '@/services/api';
import { useAuthHydration, useAuthStore } from '@/store/auth';
import { useSendStore } from '@/store/send';

interface ResolvedRecipient {
  userId: string;
  accountName: string;
}

interface RecentRecipient {
  userId: string;
  accountName: string;
  accountNumber: string | null;
}

interface Beneficiary {
  id: string;
  nickname: string;
  accountNumber: string;
  bankName: string;
}

export default function SendToUipayAccountPage() {
  const router = useRouter();
  const hasHydrated = useAuthHydration();
  const accessToken = useAuthStore((state) => state.accessToken);
  const setRecipient = useSendStore((state) => state.setRecipient);

  const [accountNumber, setAccountNumber] = useState('');
  const [resolved, setResolved] = useState<ResolvedRecipient | null>(null);
  const [resolveError, setResolveError] = useState<string | null>(null);
  const [isResolving, setIsResolving] = useState(false);

  const [tab, setTab] = useState<'recent' | 'saved'>('recent');
  const [recent, setRecent] = useState<RecentRecipient[]>([]);
  const [saved, setSaved] = useState<Beneficiary[]>([]);

  useEffect(() => {
    if (hasHydrated && !accessToken) {
      router.replace('/signin');
    }
  }, [hasHydrated, accessToken, router]);

  useEffect(() => {
    if (!accessToken) return;
    api.get('/wallet/recent-recipients').then((res) => setRecent(res.data.data));
    api.get('/beneficiaries').then((res) => setSaved(res.data.data));
  }, [accessToken]);

  // resolve the typed account number once it's a full 10 digits
  useEffect(() => {
    if (accountNumber.length !== 10) {
      setResolved(null);
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
          setResolved(res.data.data);
        })
        .catch((err) => {
          if (cancelled) return;
          setResolved(null);
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

  const handleProceed = () => {
    if (!resolved) return;
    setRecipient({
      userId: resolved.userId,
      accountName: resolved.accountName,
      accountNumber,
    });
    router.push('/send/uipay/amount');
  };

  if (!hasHydrated || !accessToken) return null;

  return (
    <GlowBackground className="flex flex-col px-6 py-10">
      <BackButton />

      <h1 className="mt-6 text-2xl font-bold text-[var(--color-light)]">
        UIPay Account Number
      </h1>

      <div className="mt-4">
        <TextInput
          variant="filled"
          value={accountNumber}
          onChange={(event) =>
            setAccountNumber(event.target.value.replace(/\D/g, '').slice(0, 10))
          }
          placeholder="Enter 10 digit account number"
          inputMode="numeric"
        />
      </div>

      {isResolving && (
        <p className="mt-2 text-sm text-white/40">Looking up account...</p>
      )}
      {resolveError && (
        <p className="mt-2 text-sm text-red-400">{resolveError}</p>
      )}
      {resolved && (
        <div className="mt-2 rounded-xl bg-[rgba(var(--color-primary-rgb),0.15)] px-4 py-3 text-[var(--color-light)]">
          {resolved.accountName}
        </div>
      )}

      <div className="mt-8 flex items-center gap-3">
        <h2 className="font-bold text-[var(--color-light)]">Beneficiaries</h2>
        <button
          type="button"
          onClick={() => setTab('recent')}
          className={`rounded-full px-3 py-1 text-sm font-semibold ${
            tab === 'recent'
              ? 'bg-[var(--color-primary)] text-[var(--color-dark)]'
              : 'text-[var(--color-primary)]'
          }`}
        >
          Recent
        </button>
        <button
          type="button"
          onClick={() => setTab('saved')}
          className={`rounded-full px-3 py-1 text-sm font-semibold ${
            tab === 'saved'
              ? 'bg-[var(--color-primary)] text-[var(--color-dark)]'
              : 'text-[var(--color-primary)]'
          }`}
        >
          Saved
        </button>
        <button
          type="button"
          onClick={() => router.push('/send/uipay/beneficiaries')}
          className="ml-auto text-sm text-[var(--color-primary)] underline"
        >
          See all
        </button>
      </div>

      <div className="mt-3 flex flex-col gap-3 overflow-y-auto">
        {tab === 'recent' &&
          (recent.length === 0 ? (
            <p className="text-sm text-white/40">No recent recipients yet.</p>
          ) : (
            recent.map((entry) => (
              <button
                key={entry.userId}
                type="button"
                disabled={!entry.accountNumber}
                onClick={() =>
                  entry.accountNumber && setAccountNumber(entry.accountNumber)
                }
                className="flex items-center justify-between rounded-xl bg-[rgba(var(--color-primary-rgb),0.1)] px-5 py-4 text-left text-[var(--color-light)] disabled:opacity-40"
              >
                {entry.accountName}
              </button>
            ))
          ))}

        {tab === 'saved' &&
          (saved.length === 0 ? (
            <p className="text-sm text-white/40">No saved beneficiaries yet.</p>
          ) : (
            saved.map((entry) => (
              <button
                key={entry.id}
                type="button"
                onClick={() => setAccountNumber(entry.accountNumber)}
                className="flex items-center justify-between rounded-xl bg-[rgba(var(--color-primary-rgb),0.1)] px-5 py-4 text-left text-[var(--color-light)]"
              >
                <span>{entry.nickname}</span>
                <span className="text-sm text-white/40">
                  {entry.bankName}
                </span>
              </button>
            ))
          ))}
      </div>

      <button
        type="button"
        onClick={() => router.push('/send/uipay/beneficiaries/add')}
        className="mt-3 text-center text-sm text-[var(--color-primary)] underline"
      >
        Add a new beneficiary
      </button>

      <button
        type="button"
        onClick={handleProceed}
        disabled={!resolved}
        className="mt-auto mb-6 rounded-full bg-[var(--color-primary)] py-4 font-semibold uppercase text-[var(--color-dark)] disabled:opacity-40"
      >
        Proceed
      </button>
    </GlowBackground>
  );
}
