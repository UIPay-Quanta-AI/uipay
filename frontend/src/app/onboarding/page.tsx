'use client';

import { useRouter } from 'next/navigation';
import { useRef, useState } from 'react';

type Slide = {
  icon: string;
  iconAlt: string;
  width: number;
  height: number;
  title: string;
  subtitle: string;
};

const SLIDES: Slide[] = [
  {
    icon: '/onboarding-payments.svg',
    iconAlt: 'Wallet with a security shield',
    width: 357,
    height: 357,
    title: 'Seamless Digital Payments',
    subtitle: 'Send, receive, and manage money with ease, anytime, anywhere.',
  },
  {
    icon: '/onboarding-secure.svg',
    iconAlt: 'Bank protected by a shield',
    width: 398,
    height: 387,
    title: 'Stay Secure',
    subtitle:
      'Advanced encryption and real-time alerts keep your transactions safe.',
  },
  {
    icon: '/onboarding-assistant.svg',
    iconAlt: 'Phone connected to NFC, QR, and AI',
    width: 324,
    height: 295,
    title: 'Your Financial Assistant',
    subtitle: 'Experience the best the future of digital payment has to offer.',
  },
];

const SWIPE_THRESHOLD = 50;

export default function OnboardingPage() {
  const router = useRouter();
  const [index, setIndex] = useState(0);
  const touchStartX = useRef<number | null>(null);

  const isLast = index === SLIDES.length - 1;

  const goToProfileSetup = () => {
    router.push('/profile-setup');
  };

  const goNext = () => {
    if (isLast) {
      goToProfileSetup();
      return;
    }
    setIndex((current) => current + 1);
  };

  const goBack = () => {
    setIndex((current) => Math.max(0, current - 1));
  };

  const handleTouchStart = (event: React.TouchEvent) => {
    touchStartX.current = event.touches[0].clientX;
  };

  const handleTouchEnd = (event: React.TouchEvent) => {
    if (touchStartX.current === null) return;

    const deltaX = event.changedTouches[0].clientX - touchStartX.current;
    touchStartX.current = null;

    if (deltaX <= -SWIPE_THRESHOLD) {
      goNext();
    } else if (deltaX >= SWIPE_THRESHOLD) {
      goBack();
    }
  };

  return (
    <main className="relative flex h-screen w-screen flex-col overflow-hidden bg-[var(--color-dark)]">
      <div className="pointer-events-none absolute -left-32 -top-32 h-96 w-96 rounded-full bg-[var(--color-primary)] opacity-30 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-32 -right-32 h-96 w-96 rounded-full bg-[var(--color-primary)] opacity-30 blur-3xl" />

      <div
        className="relative flex flex-1 flex-col items-center justify-center overflow-hidden px-8"
        onTouchStart={handleTouchStart}
        onTouchEnd={handleTouchEnd}
      >
        <div
          className="flex w-full transition-transform duration-300 ease-out"
          style={{ transform: `translateX(-${index * 100}%)` }}
        >
          {SLIDES.map((slide) => (
            <div
              key={slide.icon}
              className="flex w-full shrink-0 flex-col items-center gap-8 px-4 text-center"
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={slide.icon}
                alt={slide.iconAlt}
                width={slide.width}
                height={slide.height}
                className="h-64 w-64 object-contain"
              />

              <div className="flex flex-col gap-3">
                <h1 className="text-3xl font-extrabold text-[var(--color-light)]">
                  {slide.title}
                </h1>
                <p className="mx-auto max-w-xs text-[var(--color-primary)]">
                  {slide.subtitle}
                </p>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-6 flex items-center justify-center gap-2">
          {SLIDES.map((slide, dotIndex) => (
            <button
              key={slide.icon}
              type="button"
              aria-label={`Go to slide ${dotIndex + 1}`}
              onClick={() => setIndex(dotIndex)}
              className={`h-2 rounded-full transition-all ${
                dotIndex === index
                  ? 'w-8 bg-[var(--color-primary)]'
                  : 'w-2 bg-white/30'
              }`}
            />
          ))}
        </div>
      </div>

      <div className="flex items-center justify-between px-8 pb-12">
        {index === 0 ? (
          <button
            type="button"
            onClick={goToProfileSetup}
            className="rounded-full bg-[var(--color-light)] px-8 py-3 font-semibold text-[var(--color-dark)]"
          >
            Skip
          </button>
        ) : (
          <button
            type="button"
            onClick={goBack}
            className="rounded-full bg-[var(--color-light)] px-8 py-3 font-semibold text-[var(--color-dark)]"
          >
            Back
          </button>
        )}

        <button
          type="button"
          onClick={goNext}
          className="rounded-full border border-white/10 bg-white/5 px-8 py-3 font-semibold text-[var(--color-primary)]"
        >
          {isLast ? 'Get Started' : 'Next'}
        </button>
      </div>
    </main>
  );
}
