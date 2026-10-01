'use client';

import { BookmarkCheck, Check, Mic, ShieldCheck, ShieldX, Tag } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { BackButton } from '@/components/BackButton';
import { GlowBackground } from '@/components/GlowBackground';
import {
  getVoicePreference,
  setVoicePreference,
  VOICE_LANGUAGES,
  type VoiceGender,
  type VoiceLanguage,
} from '@/lib/voicePreference';
import { quantaVoiceStatus } from '@/services/quanta';
import { useAuthHydration, useAuthStore } from '@/store/auth';

const COMING_SOON_TILES = [
  { label: 'Assign Nicknames', icon: Tag },
  { label: 'Saved Nicknames', icon: BookmarkCheck },
];

export default function VoiceSettingsPage() {
  const router = useRouter();
  const hasHydrated = useAuthHydration();
  const accessToken = useAuthStore((state) => state.accessToken);

  const [enrolled, setEnrolled] = useState<boolean | null>(null);
  const [preference, setPreference] = useState(getVoicePreference());

  useEffect(() => {
    if (hasHydrated && !accessToken) {
      router.replace('/signin');
    }
  }, [hasHydrated, accessToken, router]);

  useEffect(() => {
    if (!accessToken) return;
    quantaVoiceStatus()
      .then((res) => setEnrolled(res.enrolled))
      .catch(() => setEnrolled(null));
  }, [accessToken]);

  const updatePreference = (language: VoiceLanguage, gender: VoiceGender) => {
    const next = { language, gender };
    setPreference(next);
    setVoicePreference(next);
  };

  if (!hasHydrated || !accessToken) return null;

  return (
    <GlowBackground className="flex flex-col px-6 py-10">
      <div className="flex items-center gap-4">
        <BackButton />
        <h1 className="text-xl font-bold text-[var(--color-light)]">
          Quanta AI Settings
        </h1>
      </div>

      <button
        type="button"
        onClick={() => router.push('/voice/settings/enroll')}
        className="mt-8 flex items-center gap-4 rounded-2xl bg-[rgba(var(--color-primary-rgb),0.1)] px-4 py-5 text-left"
      >
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-[rgba(var(--color-primary-rgb),0.15)]">
          <Mic className="h-6 w-6 text-[var(--color-primary)]" />
        </div>
        <div className="flex-1">
          <p className="font-semibold text-[var(--color-light)]">
            {enrolled ? 'Re-enroll Voice' : 'Enroll Your Voice'}
          </p>
          <p className="mt-1 flex items-center gap-1 text-sm text-white/50">
            {enrolled === null ? (
              'Checking status...'
            ) : enrolled ? (
              <>
                <ShieldCheck className="h-4 w-4 text-green-400" /> Enrolled
              </>
            ) : (
              <>
                <ShieldX className="h-4 w-4 text-white/40" /> Not enrolled yet
              </>
            )}
          </p>
        </div>
      </button>

      <h2 className="mt-8 text-sm font-semibold uppercase tracking-wide text-white/50">
        Quanta&apos;s Voice
      </h2>
      <p className="mt-1 text-sm text-white/40">
        Choose the language and voice Quanta uses when it replies to you.
      </p>

      <div className="mt-4 flex flex-col gap-2">
        {VOICE_LANGUAGES.map(({ code, label }) => (
          <div
            key={code}
            className="flex items-center justify-between rounded-2xl bg-[rgba(var(--color-primary-rgb),0.1)] px-4 py-3"
          >
            <span className="font-medium text-[var(--color-light)]">{label}</span>
            <div className="flex gap-2">
              {(['female', 'male'] as const).map((gender) => {
                const active = preference.language === code && preference.gender === gender;
                return (
                  <button
                    key={gender}
                    type="button"
                    onClick={() => updatePreference(code, gender)}
                    className={`flex items-center gap-1 rounded-full px-3 py-1.5 text-sm capitalize transition-colors ${
                      active
                        ? 'bg-[var(--color-primary)] text-[var(--color-dark)]'
                        : 'bg-white/5 text-white/60'
                    }`}
                  >
                    {active && <Check className="h-3.5 w-3.5" />}
                    {gender}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      <div className="mt-8 grid grid-cols-2 gap-4">
        {COMING_SOON_TILES.map(({ label, icon: Icon }) => (
          <div
            key={label}
            title="Coming soon"
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
