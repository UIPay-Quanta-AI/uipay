'use client';

import { Wallet } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { BackButton } from '@/components/BackButton';
import { GlowBackground } from '@/components/GlowBackground';
import api from '@/services/api';
import { useAuthHydration, useAuthStore } from '@/store/auth';
import { useSendStore } from '@/store/send';

const QUICK_AMOUNTS = [1000, 5000, 10000];

function formatNaira(amount: number) {
  return `₦${amount.toLocaleString('en-NG', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

export default function SendAmountPage() {
  const router = useRouter();
  const hasHydrated = useAuthHydration();
  const accessToken = useAuthStore((state) => state.accessToken);
  const recipient = useSendStore((state) => state.recipient);
  const setAmount = useSendStore((state) => state.setAmount);

  const [balance, setBalance] = useState<number | null>(null);
  const [amountInput, setAmountInput] = useState('');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (hasHydrated && !accessToken) {
      router.replace('/signin');
    }
  }, [hasHydrated, accessToken, router]);

  // no recipient means this screen was opened directly (or after a
  // refresh, since the send store isn't persisted) - nothing to send to
  useEffect(() => {
    if (hasHydrated && accessToken && !recipient) {
      router.replace('/send/uipay');
    }
  }, [hasHydrated, accessToken, recipient, router]);

  useEffect(() => {
    if (!accessToken) return;
    api.get('/wallet/balance').then((res) => setBalance(Number(res.data.data.balance)));
  }, [accessToken]);

  const numericAmount = Number(amountInput);
  const isValidAmount = amountInput !== '' && numericAmount > 0;

  const handleContinue = () => {
    if (!isValidAmount) {
      setError('Enter a valid amount');
      return;
    }
    if (balance !== null && numericAmount > balance) {
      setError('Amount exceeds your wallet balance');
      return;
    }

    setError(null);
    setAmount(numericAmount);
    router.push('/send/uipay/confirm');
  };

  if (!hasHydrated || !accessToken || !recipient) return null;

  const maskedAccount = '*'.repeat(recipient.accountNumber.length);

  return (
    <GlowBackground className="flex flex-col px-6 py-10">
      <BackButton />

      <div className="animate-rise-in mt-6 flex items-center gap-4 rounded-2xl bg-[#0d1929] px-5 py-4">
        <span className="flex h-12 w-12 items-center justify-center rounded-full bg-[rgba(var(--color-primary-rgb),0.15)] text-lg font-bold text-[var(--color-primary)]">
          {recipient.accountName.charAt(0).toUpperCase()}
        </span>
        <div className="flex flex-col">
          <span className="text-xs text-white/40">Sending to</span>
          <span className="font-bold text-[var(--color-light)]">
            {recipient.accountName}
          </span>
          <span className="text-sm text-white/40">{maskedAccount}</span>
        </div>
      </div>

      <div
        className="animate-rise-in mt-4 flex items-center gap-3 rounded-2xl bg-[rgba(var(--color-primary-rgb),0.12)] px-5 py-3 text-[var(--color-primary)]"
        style={{ animationDelay: '0.05s' }}
      >
        <Wallet className="h-5 w-5 shrink-0" />
        <span className="text-sm">
          Wallet Balance:{' '}
          <span className="font-bold">
            {balance === null ? '...' : formatNaira(balance)}
          </span>
        </span>
      </div>

      <div
        className="animate-rise-in mt-10 flex flex-col items-center gap-2"
        style={{ animationDelay: '0.1s' }}
      >
        <span className="text-sm text-white/40">Amount</span>
        <div className="flex items-center gap-1">
          <span className="text-3xl font-bold text-[var(--color-primary)]">
            ₦
          </span>
          <input
            value={amountInput}
            onChange={(event) => {
              setError(null);
              setAmountInput(
                event.target.value.replace(/[^\d.]/g, '').replace(/^0+(?=\d)/, ''),
              );
            }}
            inputMode="decimal"
            placeholder="0.00"
            autoFocus
            className="w-full max-w-[220px] bg-transparent text-center text-5xl font-extrabold text-[var(--color-light)] placeholder:text-white/20 focus:outline-none"
          />
        </div>

        <div className="mt-4 flex gap-2">
          {QUICK_AMOUNTS.map((quick) => (
            <button
              key={quick}
              type="button"
              onClick={() => {
                setError(null);
                setAmountInput(String(quick));
              }}
              className="rounded-full bg-[#0d1929] px-4 py-2 text-sm font-semibold text-[var(--color-light)] transition-transform active:scale-95"
            >
              ₦{quick.toLocaleString('en-NG')}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <p className="animate-shake mt-4 text-center text-sm text-red-400">
          {error}
        </p>
      )}

      <button
        type="button"
        onClick={handleContinue}
        disabled={!isValidAmount}
        className="mt-auto mb-6 rounded-full bg-[var(--color-primary)] py-4 font-semibold uppercase text-[var(--color-dark)] transition-transform active:scale-95 disabled:opacity-40"
      >
        Continue
      </button>
    </GlowBackground>
  );
}
