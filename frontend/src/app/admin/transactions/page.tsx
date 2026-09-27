'use client';

import { SlidersHorizontal } from 'lucide-react';
import Link from 'next/link';
import { useEffect, useState } from 'react';
import { AdminBackground } from '@/components/admin/AdminBackground';
import { AdminHeader } from '@/components/admin/AdminHeader';
import api from '@/services/api';

interface AdminTransaction {
  id: string;
  amount: string;
  method: string;
  status: string;
  flagged: boolean;
  senderName: string;
  recipientName: string;
  createdAt: string;
}

type Period = 'daily' | 'weekly' | 'monthly';

export default function AdminTransactionsPage() {
  const [period, setPeriod] = useState<Period>('daily');
  const [showFilter, setShowFilter] = useState(false);
  const [transactions, setTransactions] = useState<AdminTransaction[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api
      .get(`/admin/transactions?period=${period}`)
      .then((res) => setTransactions(res.data.data.transactions))
      .catch(() => setTransactions([]))
      .finally(() => setLoading(false));
  }, [period]);

  return (
    <AdminBackground>
      <AdminHeader
        title="Transactions"
        rightSlot={
          <button
            type="button"
            aria-label="Filter"
            onClick={() => setShowFilter((v) => !v)}
            className="text-[var(--color-primary)]"
          >
            <SlidersHorizontal className="h-6 w-6" />
          </button>
        }
      />

      <div className="px-6">
        {showFilter && (
          <div className="mb-4 flex gap-2">
            {(['daily', 'weekly', 'monthly'] as Period[]).map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => setPeriod(p)}
                className={`rounded-full px-4 py-1.5 text-sm capitalize ${
                  period === p
                    ? 'bg-[var(--color-primary)] text-[var(--color-dark)]'
                    : 'bg-white/10 text-[var(--color-light)]'
                }`}
              >
                {p}
              </button>
            ))}
          </div>
        )}

        {loading && <p className="text-white/50">Loading…</p>}
        {!loading && transactions.length === 0 && (
          <p className="text-white/50">No transactions in this period.</p>
        )}

        <div className="flex flex-col gap-3 pb-8">
          {transactions.map((tx) => (
            <Link
              key={tx.id}
              href={`/admin/transactions/${tx.id}`}
              className="flex items-center justify-between rounded-2xl bg-[rgba(var(--color-primary-rgb),0.1)] px-4 py-3 transition-colors hover:bg-[rgba(var(--color-primary-rgb),0.18)]"
            >
              <div>
                <p className="flex items-center gap-2 font-semibold text-[var(--color-light)]">
                  User {tx.senderName}
                  {tx.flagged && (
                    <span className="rounded-full bg-red-500/15 px-2 py-0.5 text-xs uppercase text-red-400">
                      Flagged
                    </span>
                  )}
                </p>
                <p className="text-sm text-white/50 capitalize">
                  {tx.method.replace('_', ' ')}
                </p>
              </div>
              <div className="text-right">
                <p className="font-semibold text-[var(--color-light)]">
                  ₦{Number(tx.amount).toLocaleString()}
                </p>
                <p className="text-sm text-white/50">
                  {new Date(tx.createdAt).toLocaleTimeString('en-GB', {
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </p>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </AdminBackground>
  );
}
