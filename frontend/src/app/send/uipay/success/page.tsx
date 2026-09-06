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
      <span className="flex h-32 w-32 items-center justify-center rounded-full bg-[var(--color-primary)]">
        <Check className="h-16 w-16 text-[var(--color-dark)]" />
      </span>

      <h1 className="mt-8 text-2xl font-bold text-[var(--color-light)]">
        Payment Successful
      </h1>

      <p className="mt-6 text-4xl font-extrabold text-[var(--color-light)]">
        {formatNaira(lastTransaction.amount)}
      </p>

      <p className="mt-6 text-white/60">Paid To:</p>
      <p className="text-lg font-semibold text-[var(--color-light)]">
        {lastTransaction.accountName}
      </p>
      <p className="text-sm text-white/40">
        REF: {lastTransaction.reference}
      </p>

      <button
        type="button"
        onClick={handleShare}
        className="mt-10 flex items-center gap-2 text-[var(--color-primary)]"
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
          className="rounded-full bg-[#0d1929] py-4 font-semibold text-[var(--color-primary)]"
        >
          Send Again
        </button>
        <button
          type="button"
          onClick={() => {
            clear();
            router.push('/dashboard');
          }}
          className="rounded-full bg-[var(--color-primary)] py-4 font-semibold text-[var(--color-dark)]"
        >
          Done
        </button>
      </div>
    </GlowBackground>
  );
}
