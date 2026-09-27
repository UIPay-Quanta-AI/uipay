'use client';

import {
  Calendar,
  Mail,
  MapPin,
  Repeat,
  User as UserIcon,
  Wallet,
} from 'lucide-react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { AdminBackground } from '@/components/admin/AdminBackground';
import api, { getApiErrorMessage } from '@/services/api';

interface UserDetail {
  id: string;
  firstName: string;
  lastName: string;
  email: string;
  dob: string;
  tier: number;
  status: 'active' | 'suspended';
  balance: string | null;
  currency: string | null;
  totalTransactions: number;
}

export default function AdminUserDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [user, setUser] = useState<UserDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = () => {
    api
      .get(`/admin/users/${id}`)
      .then((res) => setUser(res.data.data))
      .catch((err) => setError(getApiErrorMessage(err)));
  };

  useEffect(load, [id]);

  const toggleStatus = async () => {
    if (!user) return;
    setBusy(true);
    setError(null);
    try {
      const action = user.status === 'active' ? 'suspend' : 'reactivate';
      const res = await api.patch(`/admin/users/${id}/${action}`);
      setUser((prev) => (prev ? { ...prev, status: res.data.data.status } : prev));
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  if (!user) {
    return (
      <AdminBackground className="items-center justify-center px-6 py-12">
        <p className="text-white/50">{error ?? 'Loading…'}</p>
      </AdminBackground>
    );
  }

  const isActive = user.status === 'active';

  return (
    <AdminBackground className="items-center gap-4 px-6 pb-12 pt-8">
      <button
        type="button"
        onClick={() => router.back()}
        className="self-start text-[var(--color-light)]"
      >
        ←
      </button>

      <div className="w-full max-w-sm rounded-3xl bg-[rgba(var(--color-primary-rgb),0.9)] p-6 text-[var(--color-dark)]">
        <div className="flex flex-col items-center">
          <div className="flex h-24 w-24 items-center justify-center rounded-full bg-black/20 text-2xl font-bold text-white">
            {user.firstName.charAt(0)}
            {user.lastName.charAt(0)}
          </div>
          <h1 className="mt-3 text-xl font-bold">
            {user.firstName} {user.lastName}
          </h1>
          <p className="opacity-80">Tier {user.tier}</p>
        </div>

        <div className="mt-5 rounded-2xl bg-black/10 p-3">
          <Field icon={<Mail className="h-4 w-4" />} label="Email" value={user.email} wide />
        </div>

        <div className="mt-3 grid grid-cols-2 gap-3">
          <Field icon={<UserIcon className="h-4 w-4" />} label="Gender" value="—" />
          <Field
            icon={<Wallet className="h-4 w-4" />}
            label="Available Balance"
            value={
              user.balance ? `${user.currency ?? 'NGN'} ${Number(user.balance).toLocaleString()}` : '—'
            }
          />
          <Field icon={<Calendar className="h-4 w-4" />} label="D.O.B" value={user.dob} />
          <Field
            icon={<Repeat className="h-4 w-4" />}
            label="Transactions"
            value={String(user.totalTransactions)}
          />
          <Field icon={<MapPin className="h-4 w-4" />} label="State" value="—" />
          <Field icon={<MapPin className="h-4 w-4" />} label="L.G.A" value="—" />
        </div>

        <div className="mt-3 rounded-2xl bg-black/10 p-3">
          <Field icon={<MapPin className="h-4 w-4" />} label="Address" value="—" wide />
        </div>

        <div className="mt-5 flex items-center justify-center gap-2">
          <span className="font-semibold">Account Status:</span>
          <span
            className={`rounded-full px-3 py-1 text-sm font-semibold ${
              isActive ? 'bg-black/15 text-[var(--color-dark)]' : 'bg-red-900/20 text-red-800'
            }`}
          >
            {isActive ? 'Active' : 'Suspended'}
          </span>
        </div>

        <Link
          href={`/admin/users/${id}/activity`}
          className="mt-4 block rounded-full bg-[var(--color-dark)] py-3 text-center font-semibold text-[var(--color-light)]"
        >
          Activity Log
        </Link>
      </div>

      {error && <p className="text-sm text-red-400">{error}</p>}

      <button
        type="button"
        disabled={busy}
        onClick={toggleStatus}
        className={`w-full max-w-sm rounded-full py-4 font-semibold disabled:opacity-60 ${
          isActive
            ? 'border border-red-500 text-red-400'
            : 'bg-[var(--color-primary)] text-[var(--color-dark)]'
        }`}
      >
        {isActive ? 'SUSPEND' : 'REACTIVATE'}
      </button>
    </AdminBackground>
  );
}

function Field({
  icon,
  label,
  value,
  wide = false,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  wide?: boolean;
}) {
  return (
    <div className={wide ? '' : 'rounded-2xl bg-black/10 p-3'}>
      <div className="flex items-center gap-1.5 opacity-70">
        {icon}
        <p className="text-xs uppercase tracking-wide">{label}</p>
      </div>
      <p className="mt-1 break-words font-semibold">{value}</p>
    </div>
  );
}
