'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { LogoIcon, LogoWordmark } from '@/components/Logo';

type Stage = 'glow' | 'dot' | 'bounce' | 'icon' | 'wordmark' | 'wipe';

const STAGE_TIMINGS: { stage: Stage; delay: number }[] = [
  { stage: 'dot', delay: 200 },
  { stage: 'bounce', delay: 1000 },
  { stage: 'icon', delay: 1650 },
  { stage: 'wordmark', delay: 2300 },
  { stage: 'wipe', delay: 3800 },
];

const NAVIGATE_DELAY = 4500;

export default function Home() {
  const router = useRouter();
  const [stage, setStage] = useState<Stage>('glow');

  useEffect(() => {
    const timers = STAGE_TIMINGS.map(({ stage: nextStage, delay }) =>
      setTimeout(() => setStage(nextStage), delay),
    );
    const navigateTimer = setTimeout(() => {
      router.push('/onboarding');
    }, NAVIGATE_DELAY);

    return () => {
      timers.forEach(clearTimeout);
      clearTimeout(navigateTimer);
    };
  }, [router]);

  const isDotStage = stage === 'dot' || stage === 'bounce';
  const isLogoStage =
    stage === 'icon' || stage === 'wordmark' || stage === 'wipe';

  return (
    <main className="relative flex h-screen w-screen items-center justify-center overflow-hidden bg-[var(--color-dark)]">
      {/* the glow that shrinks down into a dot and bounces */}
      <div
        className={`absolute rounded-full bg-[var(--color-primary)] transition-all duration-[800ms] ease-out ${
          isLogoStage
            ? 'h-0 w-0 opacity-0'
            : isDotStage
              ? 'h-4 w-4 opacity-100'
              : 'h-[520px] w-[520px] opacity-60 blur-3xl'
        } ${stage === 'bounce' ? 'animate-splash-bounce' : ''}`}
      />

      {/* the icon and wordmark the dot bounces into */}
      <div
        className={`relative flex items-center gap-2 transition-all duration-300 ${
          isLogoStage ? 'scale-100 opacity-100' : 'scale-50 opacity-0'
        }`}
      >
        <LogoIcon className="h-10 w-auto" />
        <span
          className={`transition-opacity duration-300 ${
            stage === 'wordmark' || stage === 'wipe'
              ? 'opacity-100'
              : 'opacity-0'
          }`}
        >
          <LogoWordmark className="h-8 w-auto" />
        </span>
      </div>

      {/* full screen wipe into the next screen */}
      <div
        className={`pointer-events-none absolute inset-0 bg-[var(--color-primary)] transition-opacity duration-700 ${
          stage === 'wipe' ? 'opacity-100' : 'opacity-0'
        }`}
      />
    </main>
  );
}
