'use client';

import { Flag } from 'lucide-react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useEffect, useState } from 'react';
import { AdminBackground } from '@/components/admin/AdminBackground';
import { AdminHeader } from '@/components/admin/AdminHeader';
import api, { getApiErrorMessage } from '@/services/api';

interface TransactionDetail {
  id: string;
  amount: string;
  method: string;
  status: string;
  reference: string;
  flagged: boolean;
  flagReason: string | null;
  senderName: string;
  recipientName: string;
  createdAt: string;
}

export default function AdminTransactionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [tx, setTx] = useState<TransactionDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get(`/admin/transactions/${id}`)
      .then((res) => setTx(res.data.data))
      .catch((err) => setError(getApiErrorMessage(err)));
  }, [id]);

  if (!tx) {
    return (
      <AdminBackground className="items-center justify-center px-6 py-12">
        <p className="text-white/50">{error ?? 'Loading…'}</p>
      </AdminBackground>
    );
  }

  return (
    <AdminBackground>
      <AdminHeader
        title={tx.senderName}
        rightSlot={
          tx.flagged ? (
            <Flag className="h-6 w-6 fill-red-500 text-red-500" />
          ) : (
            <Link href={`/admin/transactions/${id}/flag`} aria-label="Flag transaction">
              <Flag className="h-6 w-6 text-[var(--color-light)]" />
            </Link>
          )
        }
      />

      <div className="px-6">
        <p className="text-center text-sm text-white/50 capitalize">
          Transaction Type: {tx.method.replace('_', ' ')}
        </p>
        <p className="mb-6 text-center text-sm text-white/40">
          {new Date(tx.createdAt).toLocaleString()}
        </p>

        <div className="rounded-2xl bg-[rgba(var(--color-primary-rgb),0.12)] p-5 text-[var(--color-light)]">
          <Row label="Amount" value={`₦${Number(tx.amount).toLocaleString()}`} />
          <Row label="From" value={tx.senderName} />
          <Row label="To" value={tx.recipientName} />
          <div className="flex items-center justify-between border-b border-white/10 py-2">
            <span className="text-white/60">Status</span>
            <span
              className={`rounded-full px-3 py-1 text-xs font-semibold uppercase ${
                tx.status === 'success'
                  ? 'bg-[rgba(var(--color-primary-rgb),0.2)] text-[var(--color-primary)]'
                  : 'bg-red-500/15 text-red-400'
              }`}
            >
              {tx.status}
            </span>
          </div>
          <Row label="Reference" value={tx.reference} />
          {tx.flagged && (
            <div className="flex items-center justify-between py-2">
              <span className="text-white/60">Flag reason</span>
              <span className="rounded-full bg-red-500/15 px-3 py-1 text-xs font-semibold uppercase text-red-400">
                {(tx.flagReason ?? '').replace('_', ' ')}
              </span>
            </div>
          )}
        </div>

        {error && <p className="mt-4 text-sm text-red-400">{error}</p>}
      </div>
    </AdminBackground>
  );
}

function Row({
  label,
  value,
  capitalize = false,
}: {
  label: string;
  value: string;
  capitalize?: boolean;
}) {
  return (
    <div className="flex items-center justify-between border-b border-white/10 py-2 last:border-none">
      <span className="text-white/60">{label}</span>
      <span
        className={`max-w-[60%] truncate text-right font-medium ${
          capitalize ? 'capitalize' : ''
        }`}
      >
        {value}
      </span>
    </div>
  );
}
