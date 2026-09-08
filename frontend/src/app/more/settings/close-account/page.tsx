'use client';

import { AlertTriangle } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { BackButton } from '@/components/BackButton';
import { GlowBackground } from '@/components/GlowBackground';
import { TextInput } from '@/components/TextInput';
import api, { getApiErrorMessage } from '@/services/api';
import { useAuthHydration, useAuthStore } from '@/store/auth';

export default function CloseAccountPage() {
  const router = useRouter();
  const hasHydrated = useAuthHydration();
  const accessToken = useAuthStore((state) => state.accessToken);
  const clearAuth = useAuthStore((state) => state.clearAuth);

  const [password, setPassword] = useState('');
  const [confirmText, setConfirmText] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (hasHydrated && !accessToken) {
      router.replace('/signin');
    }
  }, [hasHydrated, accessToken, router]);

  const canSubmit = password.length > 0 && confirmText === 'DELETE';

  const handleDelete = async () => {
    if (!canSubmit) return;

    setError(null);
    setIsSubmitting(true);
    try {
      await api.delete('/profile/me', { data: { password } });
      clearAuth();
      // a hard navigation, not router.push - this page's own guard effect
      // depends on accessToken, and clearAuth() flips it to null while
      // still mounted (push doesn't unmount synchronously), so a client-side
      // push here races that guard's own redirect to /signin and can lose.
      // Same bug class as the send/reset-password nav race found earlier;
      // this time the fix is a full page unload instead of reordering.
      window.location.href = '/onboarding';
    } catch (err) {
      setError(getApiErrorMessage(err));
      setIsSubmitting(false);
    }
  };

  if (!hasHydrated || !accessToken) return null;

  return (
    <GlowBackground className="flex flex-col px-6 py-10">
      <BackButton />

      <div className="animate-rise-in mt-6 flex flex-col items-center gap-3 text-center">
        <span className="flex h-16 w-16 items-center justify-center rounded-full bg-red-500/15">
          <AlertTriangle className="h-8 w-8 text-red-400" />
        </span>
        <h1 className="text-2xl font-bold text-[var(--color-light)]">
          Close Account
        </h1>
        <p className="text-sm text-white/60">
          This permanently deletes your account, wallet, transaction
          history, beneficiaries, and everything else tied to it. This
          can&apos;t be undone.
        </p>
      </div>

      <div className="mt-8 flex flex-col gap-4">
        <TextInput
          label="Enter your password to confirm"
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />
        <TextInput
          label='Type "DELETE" to confirm'
          value={confirmText}
          onChange={(event) => setConfirmText(event.target.value)}
        />
      </div>

      {error && <p className="mt-4 text-sm text-red-400">{error}</p>}

      <button
        type="button"
        onClick={handleDelete}
        disabled={!canSubmit || isSubmitting}
        className="mt-auto mb-6 rounded-full bg-red-500 py-4 font-semibold text-white disabled:opacity-40"
      >
        {isSubmitting ? 'Deleting...' : 'Permanently Delete My Account'}
      </button>
    </GlowBackground>
  );
}
