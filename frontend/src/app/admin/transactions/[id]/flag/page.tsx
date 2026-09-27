'use client';

import { useParams, useRouter } from 'next/navigation';
import { useState } from 'react';
import { AdminBackground } from '@/components/admin/AdminBackground';
import { AdminHeader } from '@/components/admin/AdminHeader';
import api, { getApiErrorMessage } from '@/services/api';

const REASONS = [
  { value: 'mismatch', label: 'Mismatch' },
  { value: 'wrong_category', label: 'Wrong Category' },
  { value: 'malicious_activity', label: 'Malicious Activity' },
] as const;

type Reason = (typeof REASONS)[number]['value'];

export default function AdminFlagTransactionPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [selected, setSelected] = useState<Reason | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const submit = async () => {
    if (!selected) return;
    setSubmitting(true);
    setError(null);
    try {
      await api.patch(`/admin/transactions/${id}/flag`, { reason: selected });
      router.replace(`/admin/transactions/${id}`);
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AdminBackground className="min-h-screen">
      <AdminHeader title="Reason for Flagging?" />

      <div className="flex flex-1 flex-col px-6">
        <div className="flex flex-col gap-6">
          {REASONS.map((reason) => (
            <label
              key={reason.value}
              className="flex items-center gap-3 text-[var(--color-light)]"
            >
              <input
                type="checkbox"
                checked={selected === reason.value}
                onChange={() => setSelected(reason.value)}
                className="h-5 w-5 accent-[var(--color-primary)]"
              />
              {reason.label}
            </label>
          ))}
        </div>

        {error && <p className="mt-4 text-sm text-red-400">{error}</p>}

        <button
          type="button"
          disabled={!selected || submitting}
          onClick={submit}
          className="mt-auto mb-8 rounded-full bg-red-600 py-4 font-semibold uppercase text-white disabled:opacity-50"
        >
          Flag
        </button>
      </div>
    </AdminBackground>
  );
}
