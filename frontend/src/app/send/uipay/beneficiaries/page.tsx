'use client';

import { Plus } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { BackButton } from '@/components/BackButton';
import { GlowBackground } from '@/components/GlowBackground';
import api, { getApiErrorMessage } from '@/services/api';
import { useAuthHydration, useAuthStore } from '@/store/auth';
import { useSendStore } from '@/store/send';

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

export default function BeneficiariesPage() {
  const router = useRouter();
  const hasHydrated = useAuthHydration();
  const accessToken = useAuthStore((state) => state.accessToken);
  const setSource = useSendStore((state) => state.setSource);

  const [tab, setTab] = useState<'recent' | 'saved'>('saved');
  const [recent, setRecent] = useState<RecentRecipient[]>([]);
  const [saved, setSaved] = useState<Beneficiary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isSelecting, setIsSelecting] = useState(false);

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

  const selectAccountNumber = async (accountNumber: string | null) => {
    if (!accountNumber || isSelecting) return;

    setIsSelecting(true);
    setError(null);
    try {
      const res = await api.get(`/wallet/resolve/${accountNumber}`);
      setSource({
        method: 'wallet',
        recipientId: res.data.data.userId,
        name: res.data.data.accountName,
        detail: `UIPay · ${accountNumber}`,
      });
      router.push('/send/amount');
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setIsSelecting(false);
    }
  };

  if (!hasHydrated || !accessToken) return null;

  return (
    <GlowBackground className="flex flex-col px-6 py-10">
      <div className="flex items-center justify-between">
        <BackButton />
        <h1 className="text-2xl font-bold text-[var(--color-light)]">
          Beneficiaries
        </h1>
        <button
          type="button"
          aria-label="Add beneficiary"
          onClick={() => router.push('/send/uipay/beneficiaries/add')}
        >
          <Plus className="h-6 w-6 text-[var(--color-light)]" />
        </button>
      </div>

      <div className="mt-6 flex gap-2 border-b border-white/10 pb-3">
        <button
          type="button"
          onClick={() => setTab('recent')}
          className={`rounded-full px-4 py-1 text-sm font-semibold ${
            tab === 'recent'
              ? 'bg-[var(--color-primary)] text-[var(--color-dark)]'
              : 'bg-white/10 text-white/60'
          }`}
        >
          Recent
        </button>
        <button
          type="button"
          onClick={() => setTab('saved')}
          className={`rounded-full px-4 py-1 text-sm font-semibold ${
            tab === 'saved'
              ? 'bg-[var(--color-primary)] text-[var(--color-dark)]'
              : 'bg-white/10 text-white/60'
          }`}
        >
          Saved
        </button>
      </div>

      {error && <p className="mt-4 text-sm text-red-400">{error}</p>}

      <div className="mt-4 flex flex-col gap-3 overflow-y-auto">
        {tab === 'recent' &&
          (recent.length === 0 ? (
            <p className="text-sm text-white/40">No recent recipients yet.</p>
          ) : (
            recent.map((entry) => (
              <button
                key={entry.userId}
                type="button"
                onClick={() => selectAccountNumber(entry.accountNumber)}
                className="flex items-center justify-between rounded-xl bg-[rgba(var(--color-primary-rgb),0.1)] px-5 py-4 text-left text-[var(--color-light)]"
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
                onClick={() => selectAccountNumber(entry.accountNumber)}
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
    </GlowBackground>
  );
}
