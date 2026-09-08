'use client';

import { HelpCircle, LogOut, SlidersHorizontal, User, Users } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { GlowBackground } from '@/components/GlowBackground';
import { SettingsRow } from '@/components/SettingsRow';
import { useAuthHydration, useAuthStore } from '@/store/auth';

export default function MorePage() {
  const router = useRouter();
  const hasHydrated = useAuthHydration();
  const accessToken = useAuthStore((state) => state.accessToken);
  const clearAuth = useAuthStore((state) => state.clearAuth);

  useEffect(() => {
    if (hasHydrated && !accessToken) {
      router.replace('/signin');
    }
  }, [hasHydrated, accessToken, router]);

  if (!hasHydrated || !accessToken) return null;

  return (
    <GlowBackground className="flex flex-col px-6 py-10">
      <h1 className="text-2xl font-bold text-[var(--color-light)]">More</h1>

      <div className="mt-6 flex flex-col">
        <SettingsRow label="Profile" icon={User} href="/profile" />
        <SettingsRow
          label="Beneficiaries"
          icon={Users}
          href="/send/uipay/beneficiaries"
        />
        <SettingsRow label="Support" icon={HelpCircle} href="/more/support" />
        <SettingsRow
          label="Settings"
          icon={SlidersHorizontal}
          href="/more/settings"
        />
      </div>

      <button
        type="button"
        onClick={() => {
          clearAuth();
          router.push('/signin');
        }}
        className="mt-auto mb-6 flex items-center justify-center gap-2 rounded-full border border-red-400/40 py-4 font-semibold text-red-400"
      >
        <LogOut className="h-5 w-5" />
        Sign Out
      </button>
    </GlowBackground>
  );
}
