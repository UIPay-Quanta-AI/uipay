'use client';

import { Headset, Nfc, QrCode, Receipt, ScanLine, Bell, LogOut, Users2 } from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { AdminBackground } from '@/components/admin/AdminBackground';
import { RevenueChart } from '@/components/admin/RevenueChart';
import api from '@/services/api';
import { useAuthStore } from '@/store/auth';

interface RevenueData {
  totalVolume: number;
  transactionCount: number;
  series: { label: string; amount: number }[];
}

interface NfcQrCounts {
  nfc: { tagsRegistered: number; payments: number };
  qr: { payments: number };
}

type Period = 'daily' | 'weekly';

export default function AdminDashboardPage() {
  const router = useRouter();
  const user = useAuthStore((state) => state.user);
  const clearAuth = useAuthStore((state) => state.clearAuth);
  const [period, setPeriod] = useState<Period>('daily');
  const [revenue, setRevenue] = useState<RevenueData | null>(null);
  const [transactionsToday, setTransactionsToday] = useState<number | null>(null);
  const [adminName, setAdminName] = useState<string | null>(null);
  const [counts, setCounts] = useState<NfcQrCounts | null>(null);

  useEffect(() => {
    api
      .get(`/admin/revenue?period=${period}`)
      .then((res) => setRevenue(res.data.data))
      .catch(() => setRevenue(null));
  }, [period]);

  useEffect(() => {
    api
      .get('/admin/transactions?period=daily')
      .then((res) => setTransactionsToday(res.data.data.count))
      .catch(() => setTransactionsToday(null));
  }, []);

  useEffect(() => {
    api
      .get('/admin/nfc-qr-count')
      .then((res) => setCounts(res.data.data))
      .catch(() => setCounts(null));
  }, []);

  useEffect(() => {
    if (!user?.id) return;
    api
      .get(`/admin/users/${user.id}`)
      .then((res) => {
        const u = res.data.data;
        setAdminName(`${u.firstName} ${u.lastName}`.trim());
      })
      .catch(() => setAdminName(null));
  }, [user?.id]);

  return (
    <AdminBackground className="gap-6 px-6 pb-28 pt-8">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-[var(--color-primary)]">Welcome Back!</p>
          <h1 className="text-2xl font-bold text-[var(--color-light)]">
            {adminName ?? user?.email ?? 'Admin'}
          </h1>
        </div>
        <div className="flex gap-3">
          <button
            type="button"
            aria-label="Support"
            className="rounded-full bg-[rgba(var(--color-primary-rgb),0.15)] p-2 text-[var(--color-primary)]"
          >
            <Headset className="h-5 w-5" />
          </button>
          <button
            type="button"
            aria-label="Notifications"
            className="rounded-full bg-[rgba(var(--color-primary-rgb),0.15)] p-2 text-[var(--color-primary)]"
          >
            <Bell className="h-5 w-5" />
          </button>
          <button
            type="button"
            aria-label="Log out"
            onClick={() => {
              clearAuth();
              router.replace('/admin/login');
            }}
            className="rounded-full bg-red-500/15 p-2 text-red-400"
          >
            <LogOut className="h-5 w-5" />
          </button>
        </div>
      </div>

      <div className="rounded-2xl bg-[rgba(var(--color-primary-rgb),0.12)] p-5">
        <p className="text-[var(--color-light)]">Transactions Today</p>
        <p className="mt-2 text-4xl font-bold text-[var(--color-light)]">
          {transactionsToday ?? '—'}
        </p>
      </div>

      <div className="rounded-2xl bg-[rgba(var(--color-primary-rgb),0.12)] p-5">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="font-semibold text-[var(--color-light)] underline">
            Revenue Summary
          </h2>
          <select
            value={period}
            onChange={(e) => setPeriod(e.target.value as Period)}
            className="rounded-full bg-[var(--color-primary)] px-3 py-1 text-sm font-medium text-[var(--color-dark)] focus:outline-none"
          >
            <option value="daily">Daily</option>
            <option value="weekly">Weekly</option>
          </select>
        </div>

        {revenue && <RevenueChart data={revenue.series} />}

        <Link
          href="/admin/transactions"
          className="mt-4 flex items-center justify-between border-t border-white/10 pt-4"
        >
          <span className="text-[var(--color-light)] underline">Transactions Completed</span>
          <span className="text-2xl font-bold text-[var(--color-light)]">
            {revenue?.transactionCount ?? '—'}
          </span>
        </Link>
      </div>

      <div>
        <h2 className="mb-3 font-bold text-[var(--color-light)]">Quick Menu</h2>
        <div className="grid grid-cols-2 gap-4">
          <StatTile
            icon={<QrCode className="h-6 w-6" />}
            label="QR count"
            value={counts?.qr.payments}
          />
          <StatTile
            icon={<Nfc className="h-6 w-6" />}
            label="NFC Tag count"
            value={counts?.nfc.tagsRegistered}
          />
          <QuickTile href="/admin/merchants" icon={<Users2 className="h-6 w-6" />} label="Manage Merchants" />
          <QuickTile href="/admin/users" icon={<Users2 className="h-6 w-6" />} label="Manage Users" />
          <QuickTile
            href="/admin/transactions"
            icon={<Receipt className="h-6 w-6" />}
            label="Manage Transactions"
            className="col-span-2"
          />
        </div>
        <Link
          href="/admin/qr"
          className="mt-4 flex items-center justify-center gap-2 rounded-2xl bg-[var(--color-primary)] py-4 font-semibold text-[var(--color-dark)]"
        >
          <ScanLine className="h-5 w-5" />
          Create QR for a user
        </Link>
      </div>
    </AdminBackground>
  );
}

function QuickTile({
  href,
  icon,
  label,
  className = '',
}: {
  href: string;
  icon: React.ReactNode;
  label: string;
  className?: string;
}) {
  return (
    <Link
      href={href}
      className={`flex flex-col items-start justify-center gap-3 rounded-2xl bg-[rgba(var(--color-primary-rgb),0.12)] p-4 text-[var(--color-light)] ${className}`}
    >
      <span className="text-[var(--color-primary)]">{icon}</span>
      <span className="text-sm font-medium">{label}</span>
    </Link>
  );
}

function StatTile({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value?: number;
}) {
  return (
    <div className="flex flex-col items-start justify-center gap-3 rounded-2xl bg-[rgba(var(--color-primary-rgb),0.12)] p-4 text-[var(--color-light)]">
      <span className="text-[var(--color-primary)]">{icon}</span>
      <span className="text-sm font-medium">{label}</span>
      <span className="text-xl font-bold">{value ?? '—'}</span>
    </div>
  );
}
