'use client';

import { Check, Printer, Share2 } from 'lucide-react';
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

function formatDate(iso: string) {
  return new Date(iso).toLocaleString('en-NG', {
    dateStyle: 'medium',
    timeStyle: 'short',
  });
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
          text: `Paid ${formatNaira(lastTransaction.amount)} to ${lastTransaction.name}. Ref: ${lastTransaction.reference}`,
        })
        .catch(() => {
          // user cancelled the share sheet - nothing to do
        });
    }
  };

  return (
    <>
      {/* Screen view - the usual animated success screen. Hidden when
          printing so the print output is the clean receipt below instead
          of a dark, decorative screen layout. */}
      <GlowBackground className="flex flex-col items-center px-6 py-16 print:hidden">
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
            {lastTransaction.name}
          </span>
          <span className="mt-2 text-xs text-white/30">
            REF: {lastTransaction.reference}
          </span>
          <span className="mt-1 text-xs text-white/30">
            {formatDate(lastTransaction.date)}
          </span>
        </div>

        <div
          className="animate-rise-in mt-6 flex items-center gap-6"
          style={{ animationDelay: '0.3s' }}
        >
          <button
            type="button"
            onClick={handleShare}
            className="flex items-center gap-2 text-[var(--color-primary)]"
          >
            <Share2 className="h-5 w-5" />
            Share
          </button>
          <button
            type="button"
            onClick={() => window.print()}
            className="flex items-center gap-2 text-[var(--color-primary)]"
          >
            <Printer className="h-5 w-5" />
            Print Receipt
          </button>
        </div>

        <div className="mt-auto flex w-full flex-col gap-3">
          <button
            type="button"
            onClick={() => {
              clear();
              router.push('/send');
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

      {/* Print view - plain black-on-white receipt. Hidden on screen,
          only rendered into the page when window.print() is called. */}
      <div className="hidden print:block print:p-10 print:text-black">
        <div className="print:mx-auto print:max-w-sm print:border print:border-black/20 print:p-6">
          <h1 className="print:text-center print:text-lg print:font-bold">
            UIPay Receipt
          </h1>
          <p className="print:mt-1 print:text-center print:text-xs print:text-black/60">
            {formatDate(lastTransaction.date)}
          </p>

          <div className="print:my-4 print:border-t print:border-dashed print:border-black/30" />

          <div className="print:flex print:justify-between print:text-sm">
            <span>Status</span>
            <span className="print:font-semibold">Successful</span>
          </div>
          <div className="print:mt-2 print:flex print:justify-between print:text-sm">
            <span>Amount</span>
            <span className="print:font-semibold">
              {formatNaira(lastTransaction.amount)}
            </span>
          </div>
          <div className="print:mt-2 print:flex print:justify-between print:text-sm">
            <span>Paid To</span>
            <span className="print:font-semibold">{lastTransaction.name}</span>
          </div>
          <div className="print:mt-2 print:flex print:justify-between print:text-sm">
            <span>Reference</span>
            <span className="print:font-semibold">{lastTransaction.reference}</span>
          </div>

          <div className="print:my-4 print:border-t print:border-dashed print:border-black/30" />

          <p className="print:text-center print:text-xs print:text-black/50">
            Thank you for using UIPay.
          </p>
        </div>
      </div>
    </>
  );
}
