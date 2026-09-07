'use client';

import { Check, Share2 } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { GlowBackground } from '@/components/GlowBackground';
import { useSendStore } from '@/store/send';

function formatNaira(amount: number) {
  return `₦${amount.toLocaleString('en-NG', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

export default function SendSuccessPage() {
  const router = useRouter();
  const lastTransaction = useSendStore((state) => state.lastTransaction);
  const clear = useSendStore((state) => state.clear);

  useEffect(() => {
    if (!lastTransaction) {
      router.replace('/dashboard');
    }
  }, [lastTransaction, router]);

  if (!lastTransaction) return null;

  const handleShare = () => {
    if (navigator.share) {
      navigator
        .share({
          title: 'Payment receipt',
          text: `Paid ${formatNaira(lastTransaction.amount)} to ${lastTransaction.accountName}. Ref: ${lastTransaction.reference}`,
        })
        .catch(() => {
          // user cancelled the share sheet - nothing to do
        });
    }
  };

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
        Payment Successful
      </h1>

      <p
        className="animate-rise-in mt-4 text-4xl font-extrabold text-[var(--color-light)]"
        style={{ animationDelay: '0.1s' }}
      >
        {formatNaira(lastTransaction.amount)}
      </p>

      <div
        className="animate-rise-in mt-8 flex w-full flex-col items-center gap-1 rounded-2xl bg-[#0d1929] px-6 py-5"
        style={{ animationDelay: '0.2s' }}
      >
        <span className="text-sm text-white/50">Paid To</span>
        <span className="text-lg font-semibold text-[var(--color-light)]">
          {lastTransaction.accountName}
        </span>
        <span className="mt-2 text-xs text-white/30">
          REF: {lastTransaction.reference}
        </span>
      </div>

      <button
        type="button"
        onClick={handleShare}
        className="animate-rise-in mt-6 flex items-center gap-2 text-[var(--color-primary)]"
        style={{ animationDelay: '0.3s' }}
      >
        <Share2 className="h-5 w-5" />
        Share Receipt
      </button>

      <div className="mt-auto flex w-full flex-col gap-3">
        <button
          type="button"
          onClick={() => {
            clear();
            router.push('/send/uipay');
          }}
          className="rounded-full bg-[#0d1929] py-4 font-semibold text-[var(--color-primary)] transition-transform active:scale-95"
        >
          Send Again
        </button>
        <button
          type="button"
          onClick={() => {
            clear();
            router.push('/dashboard');
          }}
          className="rounded-full bg-[var(--color-primary)] py-4 font-semibold text-[var(--color-dark)] transition-transform active:scale-95"
        >
          Done
        </button>
      </div>
    </GlowBackground>
  );
}
