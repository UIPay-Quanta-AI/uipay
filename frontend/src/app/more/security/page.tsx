'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { BackButton } from '@/components/BackButton';
import { GlowBackground } from '@/components/GlowBackground';
import { SettingsRow } from '@/components/SettingsRow';
import api, { getApiErrorMessage } from '@/services/api';
import { useAuthHydration, useAuthStore } from '@/store/auth';

export default function SecuritySettingsPage() {
  const router = useRouter();
  const hasHydrated = useAuthHydration();
  const accessToken = useAuthStore((state) => state.accessToken);
  const clearAuth = useAuthStore((state) => state.clearAuth);

  const [showConfirm, setShowConfirm] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (hasHydrated && !accessToken) {
      router.replace('/signin');
    }
  }, [hasHydrated, accessToken, router]);

  const handleLogoutAll = async () => {
    setIsSubmitting(true);
    setError(null);
    try {
      await api.post('/profile/sessions/logout-all');
      clearAuth();
      router.push('/signin');
    } catch (err) {
      setError(getApiErrorMessage(err));
      setIsSubmitting(false);
    }
  };

  if (!hasHydrated || !accessToken) return null;

  return (
    <GlowBackground className="flex flex-col px-6 py-10">
      <div className="flex items-center gap-4">
        <BackButton />
        <h1 className="text-xl font-bold text-[var(--color-light)]">
          Security
        </h1>
      </div>

      <div className="mt-8 flex flex-col">
        <SettingsRow
          label="Change Transaction PIN"
          href="/more/security/change-pin"
        />
        <SettingsRow
          label="Biometric Login"
          disabled
          disabledNote="Coming soon - needs a passkey/WebAuthn setup"
        />
        <SettingsRow label="Active Device List" href="/more/security/devices" />

        {showConfirm ? (
          <div className="flex flex-col gap-3 border-b border-white/10 py-4">
            <p className="text-sm text-white/60">
              This signs every device (including this one) out. Sure?
            </p>
            {error && <p className="text-sm text-red-400">{error}</p>}
            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => setShowConfirm(false)}
                className="flex-1 rounded-full bg-white/10 py-2 text-sm font-semibold text-[var(--color-light)]"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleLogoutAll}
                disabled={isSubmitting}
                className="flex-1 rounded-full bg-red-500 py-2 text-sm font-semibold text-white disabled:opacity-60"
              >
                {isSubmitting ? 'Signing out...' : 'Confirm'}
              </button>
            </div>
          </div>
        ) : (
          <SettingsRow
            label="Log out All Devices"
            onClick={() => setShowConfirm(true)}
          />
        )}

        <SettingsRow
          label="Change Password"
          href="/more/security/change-password"
        />
      </div>
    </GlowBackground>
  );
}
