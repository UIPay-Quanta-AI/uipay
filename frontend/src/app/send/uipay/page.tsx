'use client';

import { UserPlus } from 'lucide-react';
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
  const setSource = useSendStore((state) => state.setSource);

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
    setSource({
      method: 'wallet',
      recipientId: resolved.userId,
      name: resolved.accountName,
      detail: `UIPay · ${accountNumber}`,
    });
    router.push('/send/amount');
  };

  if (!hasHydrated || !accessToken) return null;

  return (
    <GlowBackground className="flex flex-col px-6 py-10">
      <BackButton />

      <h1 className="animate-rise-in mt-6 text-2xl font-bold text-[var(--color-light)]">
        UIPay Account Number
      </h1>

      <div className="animate-rise-in mt-4" style={{ animationDelay: '0.05s' }}>
        <TextInput
          variant="filled"
          value={accountNumber}
          onChange={(event) =>
            setAccountNumber(event.target.value.replace(/\D/g, '').slice(0, 10))
          }
          placeholder="Enter 10 digit account number"
          inputMode="numeric"
          className={
            resolveError ? 'ring-2 ring-red-400' : resolved ? 'ring-2 ring-[var(--color-primary)]' : ''
          }
        />
      </div>

      <div className="min-h-[52px]">
        {isResolving && (
          <p className="animate-fade-slide-in mt-2 text-sm text-white/40">
            Looking up account...
          </p>
        )}
        {resolveError && (
          <p className="animate-shake mt-2 text-sm text-red-400">
            {resolveError}
          </p>
        )}
        {resolved && (
          <div className="animate-pop-in mt-2 flex items-center gap-3 rounded-xl bg-[rgba(var(--color-primary-rgb),0.15)] px-4 py-3">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[var(--color-primary)] text-sm font-bold text-[var(--color-dark)]">
              {resolved.accountName.charAt(0).toUpperCase()}
            </span>
            <span className="font-semibold text-[var(--color-light)]">
              {resolved.accountName}
            </span>
          </div>
        )}
      </div>

      <div className="mt-6 flex items-center gap-3">
        <h2 className="font-bold text-[var(--color-light)]">Beneficiaries</h2>
        <div className="relative flex rounded-full bg-[#0d1929] p-1">
          <button
            type="button"
            onClick={() => setTab('recent')}
            className={`relative z-10 rounded-full px-3 py-1 text-sm font-semibold transition-colors ${
              tab === 'recent' ? 'text-[var(--color-dark)]' : 'text-[var(--color-primary)]'
            }`}
          >
            Recent
          </button>
          <button
            type="button"
            onClick={() => setTab('saved')}
            className={`relative z-10 rounded-full px-3 py-1 text-sm font-semibold transition-colors ${
              tab === 'saved' ? 'text-[var(--color-dark)]' : 'text-[var(--color-primary)]'
            }`}
          >
            Saved
          </button>
          <span
            className="absolute inset-y-1 w-[calc(50%-4px)] rounded-full bg-[var(--color-primary)] transition-transform duration-300 ease-out"
            style={{
              transform: tab === 'saved' ? 'translateX(calc(100% + 4px))' : 'translateX(2px)',
            }}
          />
        </div>
        <button
          type="button"
          onClick={() => router.push('/send/uipay/beneficiaries')}
          className="ml-auto text-sm text-[var(--color-primary)] underline"
        >
          See all
        </button>
      </div>

      <div key={tab} className="animate-fade-slide-in mt-3 flex flex-col gap-3 overflow-y-auto">
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
                className="flex items-center gap-3 rounded-xl bg-[rgba(var(--color-primary-rgb),0.1)] px-5 py-4 text-left text-[var(--color-light)] transition-transform active:scale-[0.98] disabled:opacity-40"
              >
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[rgba(var(--color-primary-rgb),0.2)] text-sm font-bold text-[var(--color-primary)]">
                  {entry.accountName.charAt(0).toUpperCase()}
                </span>
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
                className="flex items-center justify-between rounded-xl bg-[rgba(var(--color-primary-rgb),0.1)] px-5 py-4 text-left text-[var(--color-light)] transition-transform active:scale-[0.98]"
              >
                <span className="flex items-center gap-3">
                  <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[rgba(var(--color-primary-rgb),0.2)] text-sm font-bold text-[var(--color-primary)]">
                    {entry.nickname.charAt(0).toUpperCase()}
                  </span>
                  {entry.nickname}
                </span>
                <span className="text-sm text-white/40">{entry.bankName}</span>
              </button>
            ))
          ))}
      </div>

      <button
        type="button"
        onClick={() => router.push('/send/uipay/beneficiaries/add')}
        className="mt-3 flex items-center justify-center gap-2 text-center text-sm text-[var(--color-primary)]"
      >
        <UserPlus className="h-4 w-4" />
        Add a new beneficiary
      </button>

      <button
        type="button"
        onClick={handleProceed}
        disabled={!resolved}
        className="mt-auto mb-6 rounded-full bg-[var(--color-primary)] py-4 font-semibold uppercase text-[var(--color-dark)] transition-transform active:scale-95 disabled:opacity-40"
      >
        Proceed
      </button>
    </GlowBackground>
  );
}
