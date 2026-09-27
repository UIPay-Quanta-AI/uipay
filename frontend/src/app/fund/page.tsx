'use client';

import { Check, Wallet } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { BackButton } from '@/components/BackButton';
import { GlowBackground } from '@/components/GlowBackground';
import api, { getApiErrorMessage } from '@/services/api';
import { useAuthHydration, useAuthStore } from '@/store/auth';

const QUICK_AMOUNTS = [1000, 5000, 10000];

function formatNaira(amount: number) {
  return `₦${amount.toLocaleString('en-NG', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

type Stage = 'entry' | 'processing' | 'success';

export default function FundWalletPage() {
  const router = useRouter();
  const hasHydrated = useAuthHydration();
  const accessToken = useAuthStore((state) => state.accessToken);
  const email = useAuthStore((state) => state.user?.email);

  const [balance, setBalance] = useState<number | null>(null);
  const [amountInput, setAmountInput] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [stage, setStage] = useState<Stage>('entry');
  const [creditedAmount, setCreditedAmount] = useState<number | null>(null);

  useEffect(() => {
    if (hasHydrated && !accessToken) {
      router.replace('/signin');
    }
  }, [hasHydrated, accessToken, router]);

  useEffect(() => {
    if (!accessToken) return;
    api.get('/wallet/balance').then((res) => setBalance(Number(res.data.data.balance)));
  }, [accessToken]);

  const numericAmount = Number(amountInput);
  const isValidAmount = amountInput !== '' && numericAmount >= 100;

  const handleFund = async () => {
    if (!isValidAmount || !email) return;
    setError(null);
    setStage('processing');

    try {
      const initRes = await api.post('/wallet/fund/initiate', {
        amount: numericAmount,
      });
      const { reference, amount } = initRes.data.data as {
        reference: string;
        amount: number;
      };

      const publicKey = process.env.NEXT_PUBLIC_PAYSTACK_PUBLIC_KEY;
      if (!publicKey) {
        throw new Error('Payments are not configured on this build.');
      }

      // @paystack/inline-js touches `window` as soon as it's imported, which
      // breaks server-side rendering of this page - load it only here,
      // client-side, in response to the user's click.
      const { default: PaystackPop } = await import('@paystack/inline-js');
      const popup = new PaystackPop();
      popup.newTransaction({
        key: publicKey,
        email,
        amount: Math.round(amount * 100),
        reference,
        currency: 'NGN',
        onSuccess: async () => {
          try {
            const verifyRes = await api.post('/wallet/fund/verify', { reference });
            const result = verifyRes.data.data as { status: string; amount: string };
            if (result.status === 'success') {
              setCreditedAmount(Number(result.amount));
              setStage('success');
            } else {
              setError('Payment could not be confirmed. Contact support if you were charged.');
              setStage('entry');
            }
          } catch (err) {
            setError(getApiErrorMessage(err));
            setStage('entry');
          }
        },
        onCancel: () => {
          setStage('entry');
        },
        onError: (err) => {
          setError(err.message || 'Payment failed. Please try again.');
          setStage('entry');
        },
      });
    } catch (err) {
      setError(getApiErrorMessage(err));
      setStage('entry');
    }
  };

  if (!hasHydrated || !accessToken) return null;

  if (stage === 'success' && creditedAmount !== null) {
    return (
      <GlowBackground className="flex flex-col items-center px-6 py-16">
        <div className="relative flex h-32 w-32 items-center justify-center">
          <span className="animate-pulse-ring absolute h-32 w-32 rounded-full bg-[var(--color-primary)]" />
          <span
            className="animate-pulse-ring absolute h-32 w-32 rounded-full bg-[var(--color-primary)]"
            style={{ animationDelay: '0.5s' }}
          />
          <span className="animate-pop-in relative flex h-28 w-28 items-center justify-center rounded-full bg-[var(--color-primary)] shadow-[0_0_40px_rgba(var(--color-primary-rgb),0.5)]">
            <Check className="h-14 w-14 text-[var(--color-dark)]" strokeWidth={3} />
          </span>
        </div>

        <h1 className="animate-rise-in mt-8 text-2xl font-bold text-[var(--color-light)]">
          Wallet Funded
        </h1>

        <p
          className="animate-rise-in mt-4 text-4xl font-extrabold text-[var(--color-light)]"
          style={{ animationDelay: '0.1s' }}
        >
          {formatNaira(creditedAmount)}
        </p>

        <button
          type="button"
          onClick={() => router.push('/dashboard')}
          className="mt-auto w-full rounded-full bg-[var(--color-primary)] py-4 font-semibold text-[var(--color-dark)] transition-transform active:scale-95"
        >
          Done
        </button>
      </GlowBackground>
    );
  }

  return (
    <GlowBackground className="flex flex-col px-6 py-10">
      <BackButton />

      <div
        className="animate-rise-in mt-6 flex items-center gap-3 rounded-2xl bg-[rgba(var(--color-primary-rgb),0.12)] px-5 py-3 text-[var(--color-primary)]"
      >
        <Wallet className="h-5 w-5 shrink-0" />
        <span className="text-sm">
          Wallet Balance:{' '}
          <span className="font-bold">
            {balance === null ? '...' : formatNaira(balance)}
          </span>
        </span>
      </div>

      <div className="animate-rise-in mt-10 flex flex-col items-center gap-2" style={{ animationDelay: '0.1s' }}>
        <span className="text-sm text-white/40">Amount to add</span>
        <div className="flex items-center gap-1">
          <span className="text-3xl font-bold text-[var(--color-primary)]">₦</span>
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
            disabled={stage === 'processing'}
            className="w-full max-w-[220px] bg-transparent text-center text-5xl font-extrabold text-[var(--color-light)] placeholder:text-white/20 focus:outline-none disabled:opacity-70"
          />
        </div>

        <div className="mt-4 flex gap-2">
          {QUICK_AMOUNTS.map((quick) => (
            <button
              key={quick}
              type="button"
              disabled={stage === 'processing'}
              onClick={() => {
                setError(null);
                setAmountInput(String(quick));
              }}
              className="rounded-full bg-[#0d1929] px-4 py-2 text-sm font-semibold text-[var(--color-light)] transition-transform active:scale-95 disabled:opacity-50"
            >
              ₦{quick.toLocaleString('en-NG')}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <p className="animate-shake mt-4 text-center text-sm text-red-400">{error}</p>
      )}

      <button
        type="button"
        onClick={handleFund}
        disabled={!isValidAmount || stage === 'processing'}
        className="mt-auto mb-6 rounded-full bg-[var(--color-primary)] py-4 font-semibold uppercase text-[var(--color-dark)] transition-transform active:scale-95 disabled:opacity-40"
      >
        {stage === 'processing' ? 'Waiting for payment...' : 'Fund Wallet'}
      </button>
    </GlowBackground>
  );
}
