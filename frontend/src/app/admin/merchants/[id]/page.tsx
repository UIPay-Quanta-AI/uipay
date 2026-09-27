'use client';

import { useParams, useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { AdminBackground } from '@/components/admin/AdminBackground';
import api, { getApiErrorMessage } from '@/services/api';

interface MerchantDetail {
  id: string;
  businessName: string;
  category: string;
  applicantType: string;
  status: 'pending' | 'approved' | 'rejected';
  user: { firstName: string; lastName: string; email: string };
}

export default function AdminMerchantDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [merchant, setMerchant] = useState<MerchantDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api
      .get(`/admin/merchants/${id}`)
      .then((res) => setMerchant(res.data.data))
      .catch((err) => setError(getApiErrorMessage(err)));
  }, [id]);

  const act = async (action: 'approve' | 'reject') => {
    setBusy(true);
    setError(null);
    try {
      const res = await api.patch(`/admin/merchants/${id}/${action}`);
      setMerchant(res.data.data);
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  if (!merchant) {
    return (
      <AdminBackground className="items-center justify-center px-6 py-12">
        <p className="text-white/50">{error ?? 'Loading…'}</p>
      </AdminBackground>
    );
  }

  return (
    <AdminBackground className="items-center gap-2 px-6 pb-12 pt-16">
      <button
        type="button"
        onClick={() => router.back()}
        className="self-start text-[var(--color-light)]"
      >
        ←
      </button>

      <div className="flex h-24 w-24 items-center justify-center rounded-full bg-black text-3xl font-bold text-white">
        {merchant.businessName.charAt(0).toUpperCase()}
      </div>

      <h1 className="mt-2 text-xl font-bold text-[var(--color-light)]">
        {merchant.businessName}
      </h1>
      <p className="text-white/70">
        {merchant.applicantType === 'organisation' ? 'Organization' : 'Individual'}
      </p>

      <div className="mt-2 w-full max-w-sm rounded-2xl bg-[rgba(var(--color-primary-rgb),0.12)] p-5 text-[var(--color-light)]">
        <Row label="Category" value={merchant.category} />
        <Row label="Applicant" value={`${merchant.user.firstName} ${merchant.user.lastName}`} />
        <Row label="Email" value={merchant.user.email} capitalize={false} />
        <div className="flex items-center justify-between py-2">
          <span className="text-white/60">Status</span>
          <span
            className={`rounded-full px-3 py-1 text-xs font-semibold uppercase ${
              merchant.status === 'approved'
                ? 'bg-[rgba(var(--color-primary-rgb),0.2)] text-[var(--color-primary)]'
                : merchant.status === 'rejected'
                  ? 'bg-red-500/15 text-red-400'
                  : 'bg-white/10 text-white/70'
            }`}
          >
            {merchant.status}
          </span>
        </div>
      </div>

      {error && <p className="text-sm text-red-400">{error}</p>}

      <div className="mt-auto flex w-full max-w-sm flex-col gap-3 pt-8">
        {merchant.status !== 'approved' && (
          <button
            type="button"
            disabled={busy}
            onClick={() => act('approve')}
            className="rounded-2xl bg-[var(--color-primary)] py-4 font-semibold text-[var(--color-dark)] disabled:opacity-60"
          >
            APPROVE
          </button>
        )}
        {merchant.status !== 'rejected' && (
          <button
            type="button"
            disabled={busy}
            onClick={() => act('reject')}
            className="rounded-2xl border border-red-500 py-4 font-semibold text-red-400 disabled:opacity-60"
          >
            REJECT
          </button>
        )}
      </div>
    </AdminBackground>
  );
}

function Row({
  label,
  value,
  capitalize = true,
}: {
  label: string;
  value: string;
  capitalize?: boolean;
}) {
  return (
    <div className="flex items-center justify-between border-b border-white/10 py-2 last:border-none">
      <span className="text-white/60">{label}</span>
      <span className={`font-medium ${capitalize ? 'capitalize' : ''}`}>{value}</span>
    </div>
  );
}
