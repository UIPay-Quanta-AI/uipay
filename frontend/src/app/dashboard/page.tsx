'use client';

import { isAxiosError } from 'axios';
import {
  Bell,
  ChevronRight,
  Copy,
  CreditCard,
  Eye,
  EyeOff,
  Grid3x3,
  Headphones,
  History,
  Home,
  Mic,
  Nfc,
  QrCode,
} from 'lucide-react';
import Image from 'next/image';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useMemo, useState } from 'react';
import api, { getApiErrorMessage } from '@/services/api';
import { useAuthHydration, useAuthStore } from '@/store/auth';

interface Transaction {
  id: string;
  senderId: string;
  recipientId: string;
  amount: string;
  method: string;
  reference: string;
  status: string;
  createdAt: string;
}

interface Profile {
  firstName: string;
  lastName: string;
  identityVerifiedAt: string | null;
}

function formatNaira(amount: number | string) {
  return `₦${Number(amount).toLocaleString('en-NG', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

const DAY_MS = 24 * 60 * 60 * 1000;

export default function DashboardPage() {
  const router = useRouter();
  const hasHydrated = useAuthHydration();
  const accessToken = useAuthStore((state) => state.accessToken);
  const userId = useAuthStore((state) => state.user?.id);
  const clearAuth = useAuthStore((state) => state.clearAuth);

  const [profile, setProfile] = useState<Profile | null>(null);
  const [balance, setBalance] = useState<number | null>(null);
  const [accountNumber, setAccountNumber] = useState<string | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [balanceHidden, setBalanceHidden] = useState(false);
  const [justCopied, setJustCopied] = useState(false);
  const [trendPeriod, setTrendPeriod] = useState<'week' | 'month'>('week');

  useEffect(() => {
    if (hasHydrated && !accessToken) {
      router.replace('/signin');
    }
  }, [hasHydrated, accessToken, router]);

  useEffect(() => {
    if (!accessToken) return;

    let cancelled = false;

    async function load() {
      setIsLoading(true);
      setError(null);
      try {
        const [balanceRes, accountRes, historyRes, profileRes] = await Promise.all([
          api.get('/wallet/balance'),
          api.get('/wallet/account-number'),
          api.get('/wallet/history'),
          api.get('/profile/me'),
        ]);

        if (cancelled) return;
        setBalance(Number(balanceRes.data.data.balance));
        setAccountNumber(accountRes.data.data.accountNumber);
        setTransactions(historyRes.data.data);
        setProfile(profileRes.data.data);
      } catch (err) {
        if (cancelled) return;
        if (isAxiosError(err) && err.response?.status === 401) {
          clearAuth();
          router.replace('/signin');
          return;
        }
        setError(getApiErrorMessage(err));
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [accessToken, router, clearAuth]);

  const trends = useMemo(() => {
    const windowMs = (trendPeriod === 'week' ? 7 : 30) * DAY_MS;
    const cutoff = Date.now() - windowMs;

    let moneyIn = 0;
    let moneyOut = 0;
    for (const tx of transactions) {
      if (new Date(tx.createdAt).getTime() < cutoff) continue;
      if (tx.recipientId === userId) moneyIn += Number(tx.amount);
      if (tx.senderId === userId) moneyOut += Number(tx.amount);
    }
    return { moneyIn, moneyOut };
  }, [transactions, trendPeriod, userId]);

  const handleCopyAccountNumber = async () => {
    if (!accountNumber) return;
    try {
      await navigator.clipboard.writeText(accountNumber);
      setJustCopied(true);
      setTimeout(() => setJustCopied(false), 1500);
    } catch {
      // clipboard access can be denied by the browser - nothing useful to do
    }
  };

  if (!hasHydrated || !accessToken) return null;

  const quickLinks = [
    { label: 'Transfer Money', icon: null, href: '/send' },
    { label: 'Pay with NFC Tags', icon: Nfc, href: '/nfc' },
    { label: 'Pay with QR code', icon: QrCode, href: '/qr' },
    { label: 'Pay with Quanta', icon: Mic, href: '/voice' },
  ];

  const fullName = profile ? `${profile.firstName} ${profile.lastName}` : '';

  return (
    <main className="min-h-screen w-screen bg-[var(--color-dark)] px-5 pb-24 pt-6">
      <div className="mx-auto flex w-full max-w-sm flex-col gap-6">
        <div className="flex items-center justify-between">
          <Link href="/profile" className="flex items-center gap-3">
            <span className="flex h-11 w-11 items-center justify-center rounded-full bg-[rgba(var(--color-primary-rgb),0.15)] text-lg font-bold text-[var(--color-primary)]">
              {profile?.firstName?.charAt(0).toUpperCase() ?? ''}
            </span>
            <span className="flex flex-col">
              <span className="text-sm text-[var(--color-primary)]">
                Welcome Back!
              </span>
              <span className="font-bold text-[var(--color-light)]">
                {profile?.firstName ?? '...'}
              </span>
            </span>
          </Link>
          <div className="flex gap-2">
            <button
              type="button"
              aria-label="Support"
              className="flex h-10 w-10 items-center justify-center rounded-full bg-[rgba(var(--color-primary-rgb),0.15)] text-[var(--color-primary)]"
            >
              <Headphones className="h-5 w-5" />
            </button>
            <button
              type="button"
              aria-label="Notifications"
              className="flex h-10 w-10 items-center justify-center rounded-full bg-[rgba(var(--color-primary-rgb),0.15)] text-[var(--color-primary)]"
            >
              <Bell className="h-5 w-5" />
            </button>
          </div>
        </div>

        {isLoading ? (
          <div className="h-48 animate-pulse rounded-2xl bg-[#0d1929]" />
        ) : (
          <div className="flex flex-col gap-4 rounded-2xl bg-[#0d1929] p-5">
            <div className="flex items-center justify-between">
              <button
                type="button"
                onClick={handleCopyAccountNumber}
                className="flex items-center gap-2 text-sm text-white/70"
              >
                <span>
                  {accountNumber} | {fullName}
                </span>
                <Copy className="h-4 w-4 text-[var(--color-primary)]" />
                {justCopied && (
                  <span className="text-xs text-[var(--color-primary)]">
                    Copied!
                  </span>
                )}
              </button>
              <Link
                href="/history"
                className="flex items-center gap-1 rounded-full bg-[rgba(var(--color-primary-rgb),0.15)] px-3 py-1 text-xs font-semibold text-[var(--color-primary)]"
              >
                <History className="h-3.5 w-3.5" />
                History
              </Link>
            </div>

            <div className="flex flex-col gap-1">
              <span className="text-sm text-white/60">Available Balance</span>
              <div className="flex items-center gap-3">
                <span className="text-3xl font-extrabold text-[var(--color-light)]">
                  {balanceHidden || balance === null
                    ? '₦ • • • • • •'
                    : formatNaira(balance)}
                </span>
                <button
                  type="button"
                  aria-label={balanceHidden ? 'Show balance' : 'Hide balance'}
                  onClick={() => setBalanceHidden((value) => !value)}
                  className="text-[var(--color-primary)]"
                >
                  {balanceHidden ? (
                    <EyeOff className="h-5 w-5" />
                  ) : (
                    <Eye className="h-5 w-5" />
                  )}
                </button>
              </div>
            </div>

            <div className="mt-2 flex gap-3">
              <button
                type="button"
                disabled
                title="Coming soon"
                className="flex-1 rounded-full border border-white/15 py-3 text-sm font-semibold text-white/40"
              >
                Add Money
              </button>
              <Link
                href="/send"
                className="flex-1 rounded-full bg-[var(--color-primary)] py-3 text-center text-sm font-semibold text-[var(--color-dark)]"
              >
                Send Money
              </Link>
            </div>
          </div>
        )}

        {profile && !profile.identityVerifiedAt && (
          <Link
            href="/profile-setup/verify-id"
            className="flex items-center justify-between rounded-2xl bg-[rgba(var(--color-primary-rgb),0.1)] px-5 py-4 text-[var(--color-primary)]"
          >
            <span className="font-semibold">Complete Your KYC</span>
            <ChevronRight className="h-5 w-5" />
          </Link>
        )}

        {error && <p className="text-sm text-red-400">{error}</p>}

        <div className="flex flex-col gap-3">
          <span className="text-sm font-semibold text-white/60">
            Quick Links
          </span>
          <div className="grid grid-cols-4 gap-3">
            {quickLinks.map(({ label, icon: Icon, href }) => (
              <Link
                key={label}
                href={href}
                className="flex flex-col items-center gap-2 rounded-2xl bg-[#0d1929] py-4 text-center"
              >
                {Icon ? (
                  <Icon className="h-6 w-6 text-[var(--color-primary)]" />
                ) : (
                  <Image
                    src="/logo-icon.png"
                    alt=""
                    width={24}
                    height={24}
                    className="h-6 w-6"
                  />
                )}
                <span className="text-xs text-[var(--color-light)]">
                  {label}
                </span>
              </Link>
            ))}
          </div>
        </div>

        <div className="flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <span className="font-semibold text-[var(--color-light)]">
              Spending Trends
            </span>
            <div className="flex rounded-full bg-[#0d1929] p-1 text-xs font-semibold">
              <button
                type="button"
                onClick={() => setTrendPeriod('week')}
                className={`rounded-full px-3 py-1 ${
                  trendPeriod === 'week'
                    ? 'bg-[var(--color-primary)] text-[var(--color-dark)]'
                    : 'text-white/50'
                }`}
              >
                Week
              </button>
              <button
                type="button"
                onClick={() => setTrendPeriod('month')}
                className={`rounded-full px-3 py-1 ${
                  trendPeriod === 'month'
                    ? 'bg-[var(--color-primary)] text-[var(--color-dark)]'
                    : 'text-white/50'
                }`}
              >
                Month
              </button>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-2xl bg-[#0d1929] p-4">
              <span className="block text-lg font-bold text-[var(--color-light)]">
                {formatNaira(trends.moneyIn)}
              </span>
              <span className="text-sm text-[var(--color-primary)]">
                Money In
              </span>
            </div>
            <div className="rounded-2xl bg-[#0d1929] p-4">
              <span className="block text-lg font-bold text-[var(--color-light)]">
                {formatNaira(trends.moneyOut)}
              </span>
              <span className="text-sm text-orange-400">Money Out</span>
            </div>
          </div>
        </div>

        <div className="flex items-center justify-between gap-4 rounded-2xl bg-[#0d1929] p-5">
          <div className="flex flex-col gap-3">
            <span className="font-semibold text-[var(--color-light)]">
              Activate Physical Card
            </span>
            <span className="text-sm text-white/50">
              Expected arrival: 1st - 15th Dec
            </span>
            <button
              type="button"
              disabled
              title="Coming soon"
              className="w-fit rounded-full bg-[var(--color-primary)] px-4 py-2 text-sm font-semibold text-[var(--color-dark)] opacity-60"
            >
              Activate
            </button>
          </div>
          <div className="flex h-24 w-32 shrink-0 flex-col justify-between rounded-xl bg-black p-3">
            <CreditCard className="h-5 w-5 text-[var(--color-primary)]" />
            <span className="text-[10px] tracking-widest text-white/60">
              •••• •••• •••• ••••
            </span>
          </div>
        </div>

        <div className="flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-[var(--color-light)]">
              Recent Transactions
            </h2>
            <Link href="/history" className="text-sm text-[var(--color-primary)]">
              See all
            </Link>
          </div>

          {transactions.length === 0 && !isLoading && (
            <p className="text-sm text-white/40">No transactions yet.</p>
          )}

          {transactions.slice(0, 5).map((tx) => {
            const isDebit = tx.senderId === userId;
            return (
              <div
                key={tx.id}
                className="flex items-center justify-between rounded-2xl bg-[#0d1929] px-4 py-3"
              >
                <div className="flex items-center gap-3">
                  <span className="flex h-9 w-9 items-center justify-center rounded-full bg-[rgba(var(--color-primary-rgb),0.15)] text-sm font-bold text-[var(--color-primary)]">
                    {tx.recipientId.charAt(0).toUpperCase()}
                  </span>
                  <div className="flex flex-col">
                    <span className="text-sm text-[var(--color-light)]">
                      {tx.method}
                    </span>
                    <span className="text-xs text-white/40">
                      {tx.reference.slice(0, 10)}...
                    </span>
                  </div>
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
      </div>

      <nav className="fixed inset-x-0 bottom-0 flex justify-center border-t border-white/10 bg-[var(--color-dark)] py-3">
        <div className="flex w-full max-w-sm items-center justify-around">
          <span className="flex flex-col items-center gap-1 text-[var(--color-primary)]">
            <Home className="h-5 w-5" />
            <span className="text-xs">Home</span>
          </span>
          <Link
            href="/cards"
            className="flex flex-col items-center gap-1 text-white/40"
          >
            <CreditCard className="h-5 w-5" />
            <span className="text-xs">Cards</span>
          </Link>
          <Link
            href="/more"
            className="flex flex-col items-center gap-1 text-white/40"
          >
            <Grid3x3 className="h-5 w-5" />
            <span className="text-xs">More</span>
          </Link>
        </div>
      </nav>
    </main>
  );
}
