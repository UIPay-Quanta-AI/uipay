'use client';

import { Bell, HelpCircle, Monitor, Shield, Trash2 } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { BackButton } from '@/components/BackButton';
import { GlowBackground } from '@/components/GlowBackground';
import { SettingsRow } from '@/components/SettingsRow';
import { useAuthHydration, useAuthStore } from '@/store/auth';

export default function SettingsHubPage() {
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
          Settings
        </h1>
      </div>

      <div className="mt-8 flex flex-col">
        <SettingsRow
          label="Security Settings"
          icon={Shield}
          href="/more/security"
        />
        <SettingsRow
          label="Notification Settings"
          icon={Bell}
          href="/more/notifications"
        />
        <SettingsRow
          label="Display Settings"
          icon={Monitor}
          disabled
          disabledNote="Coming soon - only dark mode exists right now"
        />
        <SettingsRow label="FAQ" icon={HelpCircle} href="/more/support" />
        <SettingsRow
          label="Close Account"
          icon={Trash2}
          href="/more/settings/close-account"
          destructive
        />
      </div>
    </GlowBackground>
  );
}
