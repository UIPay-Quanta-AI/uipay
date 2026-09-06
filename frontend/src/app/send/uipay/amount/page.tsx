'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { BackButton } from '@/components/BackButton';
import { GlowBackground } from '@/components/GlowBackground';
import api from '@/services/api';
import { useAuthHydration, useAuthStore } from '@/store/auth';
import { useSendStore } from '@/store/send';

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

  const handleContinue = () => {
    const amount = Number(amountInput);
    if (!amount || amount <= 0) {
      setError('Enter a valid amount');
      return;
    }
    if (balance !== null && amount > balance) {
      setError('Amount exceeds your wallet balance');
      return;
    }

    setError(null);
    setAmount(amount);
    router.push('/send/uipay/confirm');
  };

  if (!hasHydrated || !accessToken || !recipient) return null;

  const maskedAccount = '*'.repeat(recipient.accountNumber.length);

  return (
    <GlowBackground className="flex flex-col px-6 py-10">
      <BackButton />

      <h1 className="mt-6 text-[var(--color-light)]">Sending to:</h1>
      <p className="text-xl font-bold text-[var(--color-light)]">
        {recipient.accountName}
      </p>
      <p className="text-sm text-white/40">{maskedAccount}</p>

      <div className="mt-4 rounded-xl bg-[var(--color-primary)] px-4 py-3 text-[var(--color-dark)]">
        Wallet Balance: {balance === null ? '...' : formatNaira(balance)}
      </div>

      <div className="mt-6 flex flex-col gap-2">
        <label className="text-[var(--color-light)]">Amount</label>
        <input
          value={amountInput}
          onChange={(event) =>
            setAmountInput(event.target.value.replace(/[^\d.]/g, ''))
          }
          inputMode="decimal"
          placeholder="00.00"
          className="rounded-xl border border-white/20 bg-transparent px-4 py-4 text-lg text-[var(--color-light)] placeholder:text-white/30 focus:border-[var(--color-primary)] focus:outline-none"
        />
      </div>

      {error && <p className="mt-4 text-sm text-red-400">{error}</p>}

      <button
        type="button"
        onClick={handleContinue}
        className="mt-auto mb-6 rounded-full bg-[var(--color-primary)] py-4 font-semibold uppercase text-[var(--color-dark)]"
      >
        Continue
      </button>
    </GlowBackground>
  );
}
