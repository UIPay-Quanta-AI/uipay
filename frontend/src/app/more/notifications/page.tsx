'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { BackButton } from '@/components/BackButton';
import { GlowBackground } from '@/components/GlowBackground';
import api, { getApiErrorMessage } from '@/services/api';
import { useAuthHydration, useAuthStore } from '@/store/auth';

interface Preferences {
  notifyGeneral: boolean;
  notifySmsAlerts: boolean;
  notifyCardTransactions: boolean;
  notifyTransfers: boolean;
  notifyOthers: boolean;
}

const ROWS: { key: keyof Preferences; label: string }[] = [
  { key: 'notifyGeneral', label: 'Notifications' },
  { key: 'notifySmsAlerts', label: 'Credit/Debit SMS alerts' },
  { key: 'notifyCardTransactions', label: 'Card Transactions' },
  { key: 'notifyTransfers', label: 'Transfer/Withdrawals' },
  { key: 'notifyOthers', label: 'Others' },
];

function Toggle({
  checked,
  onChange,
}: {
  checked: boolean;
  onChange: () => void;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={onChange}
      className={`relative h-7 w-12 rounded-full transition-colors ${
        checked ? 'bg-[var(--color-primary)]' : 'bg-white/15'
      }`}
    >
      <span
        className={`absolute top-1 h-5 w-5 rounded-full bg-white transition-transform ${
          checked ? 'translate-x-6' : 'translate-x-1'
        }`}
      />
    </button>
  );
}

export default function NotificationSettingsPage() {
  const router = useRouter();
  const hasHydrated = useAuthHydration();
  const accessToken = useAuthStore((state) => state.accessToken);

  const [preferences, setPreferences] = useState<Preferences | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (hasHydrated && !accessToken) {
      router.replace('/signin');
    }
  }, [hasHydrated, accessToken, router]);

  useEffect(() => {
    if (!accessToken) return;
    api
      .get('/profile/notification-preferences')
      .then((res) => setPreferences(res.data.data))
      .catch((err) => setError(getApiErrorMessage(err)));
  }, [accessToken]);

  const handleToggle = async (key: keyof Preferences) => {
    if (!preferences) return;

    const next = { ...preferences, [key]: !preferences[key] };
    setPreferences(next); // optimistic
    setError(null);
    try {
      await api.patch('/profile/notification-preferences', {
        [key]: next[key],
      });
    } catch (err) {
      setPreferences(preferences); // revert on failure
      setError(getApiErrorMessage(err));
    }
  };

  if (!hasHydrated || !accessToken) return null;

  return (
    <GlowBackground className="flex flex-col px-6 py-10">
      <div className="flex items-center gap-4">
        <BackButton />
        <h1 className="text-xl font-bold text-[var(--color-light)]">
          Notifications
        </h1>
      </div>

      {error && <p className="mt-4 text-sm text-red-400">{error}</p>}

      <div className="mt-6 flex flex-col">
        {ROWS.map(({ key, label }) => (
          <div
            key={key}
            className="flex items-center justify-between border-b border-white/10 py-4"
          >
            <span className="text-[var(--color-light)]">{label}</span>
            {preferences ? (
              <Toggle
                checked={preferences[key]}
                onChange={() => handleToggle(key)}
              />
            ) : (
              <div className="h-7 w-12 animate-pulse rounded-full bg-white/10" />
            )}
          </div>
        ))}
      </div>
    </GlowBackground>
  );
}
