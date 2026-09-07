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
      <span className="animate-pop-in flex h-28 w-28 items-center justify-center rounded-full bg-red-500/15">
        <span className="animate-shake flex h-20 w-20 items-center justify-center rounded-full bg-red-500">
          <X className="h-10 w-10 text-[var(--color-light)]" strokeWidth={3} />
        </span>
      </span>

      <h1 className="animate-rise-in mt-8 text-2xl font-bold text-[var(--color-light)]">
        Payment Unsuccessful
      </h1>

      <div
        className="animate-rise-in mt-6 w-full rounded-2xl bg-[#0d1929] px-6 py-5 text-center text-white/60"
        style={{ animationDelay: '0.1s' }}
      >
        {lastError}
      </div>

      <button
        type="button"
        onClick={() => {
          clear();
          router.push('/dashboard');
        }}
        className="mt-auto w-full rounded-full bg-[var(--color-primary)] py-4 font-semibold text-[var(--color-dark)] transition-transform active:scale-95"
      >
        Done
      </button>
    </GlowBackground>
  );
}
