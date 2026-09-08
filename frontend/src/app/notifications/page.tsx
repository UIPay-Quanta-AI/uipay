'use client';

import { ArrowDownLeft, ArrowUpRight } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { BackButton } from '@/components/BackButton';
import { GlowBackground } from '@/components/GlowBackground';
import api, { getApiErrorMessage } from '@/services/api';
import { useAuthHydration, useAuthStore } from '@/store/auth';

interface Transaction {
  id: string;
  senderId: string;
  senderName: string;
  recipientName: string;
  amount: string;
  method: string;
  createdAt: string;
}

function formatNaira(amount: string) {
  return `₦${Number(amount).toLocaleString('en-NG', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

function timeAgo(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const minutes = Math.floor(diffMs / 60000);
  if (minutes < 1) return 'Just now';
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

// there's no separate notification-generation system yet - these are the
// user's real transactions, framed as a notification feed rather than
// fabricated content
export default function NotificationsPage() {
  const router = useRouter();
  const hasHydrated = useAuthHydration();
  const accessToken = useAuthStore((state) => state.accessToken);
  const userId = useAuthStore((state) => state.user?.id);

  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (hasHydrated && !accessToken) {
      router.replace('/signin');
    }
  }, [hasHydrated, accessToken, router]);

  useEffect(() => {
    if (!accessToken) return;
    api
      .get('/wallet/history')
      .then((res) => setTransactions(res.data.data))
      .catch((err) => setError(getApiErrorMessage(err)))
      .finally(() => setIsLoading(false));
  }, [accessToken]);

  if (!hasHydrated || !accessToken) return null;

  return (
    <GlowBackground className="flex flex-col px-6 py-10">
      <div className="flex items-center gap-4">
        <BackButton />
        <h1 className="text-xl font-bold text-[var(--color-light)]">
          Notifications
        </h1>
      </div>

      {error && <p className="mt-4 text-sm text-red-400">{error}</p>}
      {isLoading && <p className="mt-6 text-sm text-white/40">Loading...</p>}
      {!isLoading && transactions.length === 0 && (
        <p className="mt-6 text-sm text-white/40">Nothing yet.</p>
      )}

      <div className="mt-4 flex flex-col gap-3">
        {transactions.map((tx) => {
          const isDebit = tx.senderId === userId;
          const counterpart = isDebit ? tx.recipientName : tx.senderName;
          return (
            <div
              key={tx.id}
              className="flex items-center gap-3 rounded-xl bg-[#0d1929] px-4 py-4"
            >
              <span
                className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full ${
                  isDebit ? 'bg-red-500/15' : 'bg-[rgba(var(--color-primary-rgb),0.15)]'
                }`}
              >
                {isDebit ? (
                  <ArrowUpRight className="h-5 w-5 text-red-400" />
                ) : (
                  <ArrowDownLeft className="h-5 w-5 text-[var(--color-primary)]" />
                )}
              </span>
              <div className="flex flex-1 flex-col">
                <span className="text-sm text-[var(--color-light)]">
                  {isDebit ? `You paid ${counterpart}` : `${counterpart} paid you`}
                </span>
                <span className="text-xs text-white/40">
                  {timeAgo(tx.createdAt)}
                </span>
              </div>
              <span
                className={`text-sm font-semibold ${
                  isDebit ? 'text-red-400' : 'text-[var(--color-primary)]'
                }`}
              >
                {isDebit ? '-' : '+'}
                {formatNaira(tx.amount)}
              </span>
            </div>
          );
        })}
      </div>
    </GlowBackground>
  );
}
