'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { BackButton } from '@/components/BackButton';
import { GlowBackground } from '@/components/GlowBackground';
import api, { getApiErrorMessage } from '@/services/api';
import { useAuthHydration, useAuthStore } from '@/store/auth';
import { useSendStore } from '@/store/send';

function formatNaira(amount: number) {
  return `₦${amount.toLocaleString('en-NG', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

export default function SendConfirmPage() {
  const router = useRouter();
  const hasHydrated = useAuthHydration();
  const accessToken = useAuthStore((state) => state.accessToken);
  const recipient = useSendStore((state) => state.recipient);
  const amount = useSendStore((state) => state.amount);

  const [balance, setBalance] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isChecking, setIsChecking] = useState(false);

  useEffect(() => {
    if (hasHydrated && !accessToken) {
      router.replace('/signin');
    }
  }, [hasHydrated, accessToken, router]);

  useEffect(() => {
    if (hasHydrated && accessToken && (!recipient || !amount)) {
      router.replace('/send/uipay');
    }
  }, [hasHydrated, accessToken, recipient, amount, router]);

  useEffect(() => {
    if (!accessToken) return;
    api.get('/wallet/balance').then((res) => setBalance(Number(res.data.data.balance)));
  }, [accessToken]);

  const handleConfirm = async () => {
    setIsChecking(true);
    setError(null);
    try {
      const res = await api.get('/profile/me');
      if (res.data.data.hasTransactionPin) {
        router.push('/send/uipay/pin');
      } else {
        router.push('/send/set-pin');
      }
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setIsChecking(false);
    }
  };

  if (!hasHydrated || !accessToken || !recipient || !amount) return null;

  return (
    <GlowBackground className="flex flex-col px-6 py-10">
      <BackButton />

      <h1 className="mt-8 text-center text-3xl font-bold text-[var(--color-light)]">
        Sending To
      </h1>

      <p className="mt-8 text-center text-xl font-bold text-[var(--color-light)]">
        {recipient.accountName}
      </p>
      <p className="mt-4 text-center text-[var(--color-light)]">UIPay</p>
      <p className="mt-4 text-center text-[var(--color-light)]">
        {recipient.accountNumber}
      </p>

      <p className="mt-8 text-center text-4xl font-extrabold text-[var(--color-light)]">
        {formatNaira(amount)}
      </p>

      <div className="mt-auto flex flex-col gap-3 rounded-2xl bg-[#0d1929] p-5 text-[var(--color-light)]">
        <div className="flex justify-between">
          <span>Amount</span>
          <span>{formatNaira(amount)}</span>
        </div>
        <div className="flex justify-between">
          <span>Fee</span>
          <span>{formatNaira(0)}</span>
        </div>
        <div className="flex justify-between">
          <span>V.A.T</span>
          <span>{formatNaira(0)}</span>
        </div>
        <div className="flex justify-between">
          <span>Available Balance</span>
          <span>{balance === null ? '...' : formatNaira(balance)}</span>
        </div>
      </div>

      {error && <p className="mt-4 text-sm text-red-400">{error}</p>}

      <button
        type="button"
        onClick={handleConfirm}
        disabled={isChecking}
        className="mt-4 mb-6 rounded-full bg-[var(--color-primary)] py-4 font-semibold text-[var(--color-dark)] disabled:opacity-60"
      >
        {isChecking ? 'Please wait...' : 'Confirm & Pay'}
      </button>
    </GlowBackground>
  );
}
