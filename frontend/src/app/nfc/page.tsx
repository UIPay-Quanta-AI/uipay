'use client';

import { CheckCircle2, Nfc, Smartphone } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';
import api, { getApiErrorMessage } from '@/services/api';
import { useAuthHydration, useAuthStore } from '@/store/auth';
import { useSendStore } from '@/store/send';

// Web NFC (NDEFReader) isn't in TS's default lib.dom.d.ts - it's also only
// implemented in Android Chrome (89+), over HTTPS/localhost. There's no
// Web NFC on iOS Safari or any desktop browser - Apple restricts NFC
// reading to native apps entirely. So this is real where it can be, with a
// manual fallback everywhere else (including for testing today, since no
// physical tags exist yet).
interface NdefReadingEvent {
  serialNumber: string;
}
interface NdefReaderLike {
  scan: () => Promise<void>;
  addEventListener: (
    type: 'reading',
    listener: (event: NdefReadingEvent) => void,
  ) => void;
}

type ScanState = 'waiting' | 'detected' | 'resolving' | 'error';

export default function NfcPayPage() {
  const router = useRouter();
  const hasHydrated = useAuthHydration();
  const accessToken = useAuthStore((state) => state.accessToken);
  const setSource = useSendStore((state) => state.setSource);

  const [state, setState] = useState<ScanState>('waiting');
  const [error, setError] = useState<string | null>(null);
  const [webNfcSupported, setWebNfcSupported] = useState(false);
  const [manualTagId, setManualTagId] = useState('');
  const handledRef = useRef(false);

  useEffect(() => {
    if (hasHydrated && !accessToken) {
      router.replace('/signin');
    }
  }, [hasHydrated, accessToken, router]);

  const resolveTag = async (tagId: string) => {
    if (handledRef.current) return;
    handledRef.current = true;

    setState('detected');
    await new Promise((resolve) => setTimeout(resolve, 600)); // let "Detected" register visually

    setState('resolving');
    setError(null);
    try {
      const res = await api.get(`/nfc/resolve/${tagId}`);
      const { businessName, category } = res.data.data;
      setSource({
        method: 'nfc',
        tagId,
        name: businessName,
        detail: category,
      });
      router.push('/send/amount');
    } catch (err) {
      handledRef.current = false;
      setState('error');
      setError(getApiErrorMessage(err));
    }
  };

  useEffect(() => {
    const NDEFReaderCtor = (window as { NDEFReader?: new () => NdefReaderLike })
      .NDEFReader;
    if (!NDEFReaderCtor) return;

    setWebNfcSupported(true);
    const reader = new NDEFReaderCtor();

    reader
      .scan()
      .then(() => {
        reader.addEventListener('reading', (event) => {
          resolveTag(event.serialNumber);
        });
      })
      .catch(() => {
        // permission denied or scan failed to start - the manual fallback
        // below still works
        setWebNfcSupported(false);
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleManualSubmit = () => {
    if (!manualTagId.trim()) return;
    resolveTag(manualTagId.trim());
  };

  if (!hasHydrated || !accessToken) return null;

  return (
    <main className="relative flex h-screen w-screen flex-col items-center overflow-hidden bg-[var(--color-dark)] px-6 py-10">
      <div className="pointer-events-none absolute -left-32 -top-32 h-96 w-96 rounded-full bg-[var(--color-primary)] opacity-30 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-32 -right-32 h-96 w-96 rounded-full bg-[var(--color-primary)] opacity-30 blur-3xl" />

      <div className="relative z-10 flex h-full w-full flex-col items-center">
        <div className="mt-16 flex flex-col items-center gap-6">
          <div
            className={`relative flex h-56 w-56 items-center justify-center rounded-3xl border-2 ${
              state === 'detected'
                ? 'animate-pop-in border-[var(--color-primary)] bg-[rgba(var(--color-primary-rgb),0.15)]'
                : 'border-[var(--color-primary)]/40'
            }`}
          >
            {state === 'waiting' && (
              <>
                <span className="animate-pulse-ring absolute h-40 w-40 rounded-full bg-[var(--color-primary)]" />
                <span
                  className="animate-pulse-ring absolute h-40 w-40 rounded-full bg-[var(--color-primary)]"
                  style={{ animationDelay: '0.6s' }}
                />
              </>
            )}
            {state === 'detected' || state === 'resolving' ? (
              <CheckCircle2 className="relative h-24 w-24 text-[var(--color-primary)]" />
            ) : (
              <Nfc className="relative h-24 w-24 text-[var(--color-primary)]" />
            )}
          </div>

          <p className="animate-rise-in text-center text-lg text-[var(--color-light)]">
            Tap Your Phone Against The Tag
          </p>

          <Smartphone className="h-8 w-8 text-[var(--color-primary)]" />

          <p className="animate-rise-in font-bold text-[var(--color-light)]">
            {state === 'waiting' && 'Waiting'}
            {state === 'detected' && 'Detected'}
            {state === 'resolving' && 'Checking tag...'}
            {state === 'error' && 'Try Again'}
          </p>

          {error && (
            <p className="animate-shake max-w-xs text-center text-sm text-red-400">
              {error}
            </p>
          )}
        </div>

        <div className="mt-auto flex w-full flex-col gap-4">
          {!webNfcSupported && (
            <div className="animate-rise-in flex flex-col gap-2 rounded-2xl bg-[#0d1929] p-4">
              <span className="text-xs text-white/40">
                NFC tap-to-pay needs Android Chrome. No tag reachable here -
                enter a tag ID to continue for testing.
              </span>
              <div className="flex gap-2">
                <input
                  value={manualTagId}
                  onChange={(event) => setManualTagId(event.target.value)}
                  placeholder="Tag ID"
                  className="flex-1 rounded-xl border border-white/20 bg-transparent px-4 py-2 text-sm text-[var(--color-light)] placeholder:text-white/30 focus:border-[var(--color-primary)] focus:outline-none"
                />
                <button
                  type="button"
                  onClick={handleManualSubmit}
                  disabled={!manualTagId.trim() || state === 'resolving'}
                  className="rounded-xl bg-[var(--color-primary)] px-4 py-2 text-sm font-semibold text-[var(--color-dark)] disabled:opacity-40"
                >
                  Go
                </button>
              </div>
            </div>
          )}

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
