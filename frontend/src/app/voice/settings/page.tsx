'use client';

import { BookmarkCheck, Repeat, ShieldCheck, Tag } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { BackButton } from '@/components/BackButton';
import { GlowBackground } from '@/components/GlowBackground';
import { useAuthHydration, useAuthStore } from '@/store/auth';

const TILES = [
  { label: 'Assign Nicknames', icon: Tag },
  { label: 'Saved Nicknames', icon: BookmarkCheck },
  { label: 'Voice Enrollment Status', icon: ShieldCheck },
  { label: 'Re-enroll Voice', icon: Repeat },
];

export default function VoiceSettingsPage() {
  const router = useRouter();
  const hasHydrated = useAuthHydration();
  const accessToken = useAuthStore((state) => state.accessToken);

  useEffect(() => {
    if (hasHydrated && !accessToken) {
      router.replace('/signin');
    }
  }, [hasHydrated, accessToken, router]);

  if (!hasHydrated || !accessToken) return null;

  return (
    <GlowBackground className="flex flex-col px-6 py-10">
      <div className="flex items-center gap-4">
        <BackButton />
        <h1 className="text-xl font-bold text-[var(--color-light)]">
          Quanta AI Settings
        </h1>
      </div>

      <div className="mt-8 grid grid-cols-2 gap-4">
        {TILES.map(({ label, icon: Icon }) => (
          <div
            key={label}
            title="Coming soon - no voice backend yet"
            className="flex flex-col items-center justify-center gap-3 rounded-2xl bg-[rgba(var(--color-primary-rgb),0.1)] px-4 py-8 text-center opacity-50"
          >
            <Icon className="h-6 w-6 text-[var(--color-primary)]" />
            <span className="font-semibold text-[var(--color-primary)]">
              {label}
            </span>
          </div>
        ))}
      </div>
    </GlowBackground>
  );
}
