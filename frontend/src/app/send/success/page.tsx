'use client';

import { Check, Download, Share2 } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';
import { GlowBackground } from '@/components/GlowBackground';
import { ReceiptCard } from '@/components/ReceiptCard';
import api from '@/services/api';
import { useSendStore } from '@/store/send';

function formatNaira(amount: number) {
  return `₦${amount.toLocaleString('en-NG', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

const METHOD_LABELS: Record<string, string> = {
  wallet: 'Wallet Transfer',
  nfc: 'NFC Payment',
  qr: 'QR Payment',
};

export default function SendSuccessPage() {
  const router = useRouter();
  const lastTransaction = useSendStore((state) => state.lastTransaction);
  const source = useSendStore((state) => state.source);
  const clear = useSendStore((state) => state.clear);

  const [senderName, setSenderName] = useState<string | null>(null);
  const [isCapturing, setIsCapturing] = useState(false);
  const receiptRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!lastTransaction) {
      router.replace('/dashboard');
    }
  }, [lastTransaction, router]);

  // the signed-in user's own name isn't reliably in the auth store - it's
  // only populated there right after signup, not after an ordinary signin -
  // so this is the one place that actually always has it
  useEffect(() => {
    api
      .get('/profile/me')
      .then((res) => {
        const { firstName, lastName } = res.data.data;
        if (firstName && lastName) setSenderName(`${firstName} ${lastName}`);
      })
      .catch(() => {
        // receipt still works without a sender name, just omits that row
      });
  }, []);

  if (!lastTransaction) return null;

  // Renders the receipt (already in the DOM, off-screen) to a canvas and
  // returns it as a PNG blob - the one shared piece of logic behind both
  // Download and Share, so the exported image is always exactly what's
  // captured here, not a second hand-maintained representation.
  const captureReceipt = async (): Promise<Blob | null> => {
    if (!receiptRef.current) return null;
    const html2canvas = (await import('html2canvas')).default;
    const canvas = await html2canvas(receiptRef.current, {
      backgroundColor: null,
      scale: 2,
    });
    return new Promise((resolve) => canvas.toBlob((blob) => resolve(blob), 'image/png'));
  };

  const handleDownload = async () => {
    setIsCapturing(true);
    try {
      const blob = await captureReceipt();
      if (!blob) return;
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `uipay-receipt-${lastTransaction.reference}.png`;
      link.click();
      URL.revokeObjectURL(url);
    } finally {
      setIsCapturing(false);
    }
  };

  const handleShare = async () => {
    setIsCapturing(true);
    try {
      const blob = await captureReceipt();
      if (blob) {
        const file = new File([blob], `uipay-receipt-${lastTransaction.reference}.png`, {
          type: 'image/png',
        });
        if (navigator.canShare?.({ files: [file] })) {
          await navigator.share({ files: [file], title: 'Payment Receipt' }).catch(() => {
            // user cancelled the share sheet - nothing to do
          });
          return;
        }
      }
      // Files not supported on this browser (most desktop browsers) - fall
      // back to the plain text share rather than failing silently.
      if (navigator.share) {
        await navigator
          .share({
            title: 'Payment receipt',
            text: `Paid ${formatNaira(lastTransaction.amount)} to ${lastTransaction.name}. Ref: ${lastTransaction.reference}`,
          })
          .catch(() => {});
      }
    } finally {
      setIsCapturing(false);
    }
  };

  return (
    <GlowBackground className="flex flex-col items-center px-6 py-10">
      <div className="relative flex h-24 w-24 items-center justify-center">
        <span className="animate-pulse-ring absolute h-24 w-24 rounded-full bg-[var(--color-primary)]" />
        <span className="animate-pop-in relative flex h-20 w-20 items-center justify-center rounded-full bg-[var(--color-primary)] shadow-[0_0_40px_rgba(var(--color-primary-rgb),0.5)]">
          <Check className="h-10 w-10 text-[var(--color-dark)]" strokeWidth={3} />
        </span>
      </div>

      <h1 className="animate-rise-in mt-4 text-xl font-bold text-[var(--color-light)]">
        Payment Successful
      </h1>

      <div className="animate-rise-in mt-6 w-full overflow-hidden rounded-3xl shadow-xl" style={{ animationDelay: '0.1s' }}>
        <ReceiptCard
          ref={receiptRef}
          amount={lastTransaction.amount}
          reference={lastTransaction.reference}
          date={lastTransaction.date}
          methodLabel={source ? (METHOD_LABELS[source.method] ?? 'Transfer') : 'Transfer'}
          senderName={senderName}
          beneficiaryName={lastTransaction.name}
          beneficiaryDetail={source?.detail ?? null}
        />
      </div>

      <div
        className="animate-rise-in mt-6 flex items-center gap-6"
        style={{ animationDelay: '0.2s' }}
      >
        <button
          type="button"
          onClick={handleShare}
          disabled={isCapturing}
          className="flex items-center gap-2 text-[var(--color-primary)] disabled:opacity-50"
        >
          <Share2 className="h-5 w-5" />
          Share
        </button>
        <button
          type="button"
          onClick={handleDownload}
          disabled={isCapturing}
          className="flex items-center gap-2 text-[var(--color-primary)] disabled:opacity-50"
        >
          <Download className="h-5 w-5" />
          Download
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
  );
}
