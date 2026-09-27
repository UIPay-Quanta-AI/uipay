'use client';

import { isAxiosError } from 'axios';
import { useRouter } from 'next/navigation';
import { useEffect, useMemo, useState } from 'react';
import { BackButton } from '@/components/BackButton';
import { Transaction, TransactionRow } from '@/components/TransactionRow';
import api, { getApiErrorMessage } from '@/services/api';
import { useAuthHydration, useAuthStore } from '@/store/auth';

type Filter = 'all' | 'transfer' | 'funding';

export default function HistoryPage() {
  const router = useRouter();
  const hasHydrated = useAuthHydration();
  const accessToken = useAuthStore((state) => state.accessToken);
  const userId = useAuthStore((state) => state.user?.id);

  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [filter, setFilter] = useState<Filter>('all');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (hasHydrated && !accessToken) {
      router.replace('/signin');
    }
  }, [hasHydrated, accessToken, router]);

  useEffect(() => {
    if (!accessToken) return;

    let cancelled = false;
    api
      .get('/wallet/history')
      .then((res) => {
        if (!cancelled) setTransactions(res.data.data);
      })
      .catch((err) => {
        if (cancelled) return;
        if (isAxiosError(err) && err.response?.status === 401) return;
        setError(getApiErrorMessage(err));
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [accessToken]);

  const filtered = useMemo(
    () => (filter === 'all' ? transactions : transactions.filter((tx) => tx.type === filter)),
    [transactions, filter],
  );

  if (!hasHydrated || !accessToken) return null;

  return (
    <main className="min-h-screen w-screen bg-[var(--color-dark)] px-5 pb-16 pt-6">
      <div className="mx-auto flex w-full max-w-sm flex-col gap-5">
        <div className="relative flex items-center justify-center">
          <div className="absolute left-0">
            <BackButton />
          </div>
          <h1 className="text-lg font-bold text-[var(--color-light)]">
            Transaction History
          </h1>
        </div>

        <div className="flex gap-2">
          {(
            [
              { key: 'all', label: 'All' },
              { key: 'transfer', label: 'Transfers' },
              { key: 'funding', label: 'Funding' },
            ] as { key: Filter; label: string }[]
          ).map(({ key, label }) => (
            <button
              key={key}
              type="button"
              onClick={() => setFilter(key)}
              className={`rounded-full px-4 py-1.5 text-sm font-semibold ${
                filter === key
                  ? 'bg-[var(--color-primary)] text-[var(--color-dark)]'
                  : 'bg-[#0d1929] text-white/60'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {error && <p className="text-sm text-red-400">{error}</p>}

        {isLoading ? (
          <div className="flex flex-col gap-3">
            {[0, 1, 2, 3].map((i) => (
              <div key={i} className="h-16 animate-pulse rounded-2xl bg-[#0d1929]" />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <p className="mt-6 text-center text-sm text-white/40">
            {filter === 'all'
              ? 'No transactions yet.'
              : filter === 'funding'
                ? 'No wallet funding yet.'
                : 'No transfers yet.'}
          </p>
        ) : (
          <div className="flex flex-col gap-3">
            {filtered.map((tx) => (
              <TransactionRow key={tx.id} tx={tx} userId={userId} />
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
