'use client';

import { X } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { GlowBackground } from '@/components/GlowBackground';
import { useSendStore } from '@/store/send';

export default function SendFailurePage() {
  const router = useRouter();
  const lastError = useSendStore((state) => state.lastError);
  const clear = useSendStore((state) => state.clear);

  useEffect(() => {
    if (!lastError) {
      router.replace('/dashboard');
    }
  }, [lastError, router]);

  if (!lastError) return null;

  return (
    <GlowBackground className="flex flex-col items-center px-6 py-16">
      <span className="flex h-32 w-32 items-center justify-center rounded-full bg-[var(--color-primary)]">
        <X className="h-16 w-16 text-[var(--color-dark)]" />
      </span>

      <h1 className="mt-8 text-2xl font-bold text-[var(--color-light)]">
        Payment Unsuccessful
      </h1>

      <p className="mt-4 text-center text-white/60">{lastError}</p>

      <button
        type="button"
        onClick={() => {
          clear();
          router.push('/dashboard');
        }}
        className="mt-auto w-full rounded-full bg-[var(--color-primary)] py-4 font-semibold text-[var(--color-dark)]"
      >
        Done
      </button>
    </GlowBackground>
  );
}
