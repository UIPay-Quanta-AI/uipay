'use client';

import { Mic, Settings } from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';
import { useAuthHydration, useAuthStore } from '@/store/auth';

const LISTEN_DURATION_MS = 2800;

export default function VoicePage() {
  const router = useRouter();
  const hasHydrated = useAuthHydration();
  const accessToken = useAuthStore((state) => state.accessToken);

  const [isListening, setIsListening] = useState(false);
  const [notice, setNotice] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (hasHydrated && !accessToken) {
      router.replace('/signin');
    }
  }, [hasHydrated, accessToken, router]);

  useEffect(() => () => {
    if (timerRef.current) clearTimeout(timerRef.current);
  }, []);

  const handleTap = () => {
    if (isListening) return;

    setNotice(false);
    setIsListening(true);
    // there's no voice backend wired up yet, so this is an honest mock, not
    // a fake recognition result - it just times out and points at the real
    // fallback instead of pretending to have heard something
    timerRef.current = setTimeout(() => {
      setIsListening(false);
      setNotice(true);
    }, LISTEN_DURATION_MS);
  };

  if (!hasHydrated || !accessToken) return null;

  return (
    <main className="relative flex h-screen w-screen flex-col items-center overflow-hidden bg-[var(--color-dark)] px-6 py-10">
      <div className="pointer-events-none absolute -left-32 -top-32 h-96 w-96 rounded-full bg-[var(--color-primary)] opacity-30 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-32 -right-32 h-96 w-96 rounded-full bg-[var(--color-primary)] opacity-30 blur-3xl" />

      <div className="relative z-10 flex w-full justify-end">
        <Link
          href="/voice/settings"
          aria-label="Quanta AI Settings"
          className="flex h-10 w-10 items-center justify-center rounded-full bg-[rgba(var(--color-primary-rgb),0.15)] text-[var(--color-primary)]"
        >
          <Settings className="h-5 w-5" />
        </Link>
      </div>

      <div className="relative z-10 flex h-full w-full flex-col items-center">
        <button
          type="button"
          onClick={handleTap}
          className="mt-32 flex h-64 w-64 items-center justify-center rounded-full bg-[rgba(var(--color-primary-rgb),0.12)] transition-transform active:scale-95"
        >
          {isListening ? (
            <div className="flex items-center gap-2">
              {[0, 0.15, 0.3, 0.15, 0].map((delay, index) => (
                <span
                  key={index}
                  className="animate-voice-bar h-16 w-3 rounded-full bg-[var(--color-primary)]"
                  style={{ animationDelay: `${delay}s` }}
                />
              ))}
            </div>
          ) : (
            <Mic className="h-24 w-24 text-[var(--color-primary)]" />
          )}
        </button>

        <p className="animate-rise-in mt-10 text-xl text-[var(--color-light)]">
          Tap To Speak
        </p>
        <p
          className="animate-rise-in mt-2 text-white/50"
          style={{ animationDelay: '0.05s' }}
        >
          Say &ldquo;Hey Quanta&rdquo;
        </p>

        {notice && (
          <p className="animate-rise-in mt-6 max-w-xs text-center text-sm text-white/40">
            Voice payments aren&apos;t connected yet - use manual entry below
            for now.
          </p>
        )}

        <div className="mt-auto flex w-full flex-col gap-4">
          <button
            type="button"
            onClick={() => router.push('/send/uipay')}
            className="rounded-full bg-[rgba(var(--color-primary-rgb),0.15)] py-4 font-semibold text-[var(--color-primary)] transition-transform active:scale-95"
          >
            Switch To Manual Entry
          </button>
          <button
            type="button"
            onClick={() => router.push('/dashboard')}
            className="text-center text-white/50 underline"
          >
            Cancel
          </button>
        </div>
      </div>
    </main>
  );
}
