'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { BackButton } from '@/components/BackButton';
import { GlowBackground } from '@/components/GlowBackground';
import { TextInput } from '@/components/TextInput';
import api, { getApiErrorMessage } from '@/services/api';
import { useAuthHydration, useAuthStore } from '@/store/auth';

// same rule enforced server-side and on the forgot-password reset screen
const DISALLOWED_CHARS = /["'!.\-/\\|]/;

function validate(newPassword: string, confirmPassword: string): string | null {
  if (newPassword.length < 12) return 'At least 12 characters';
  if (!/[A-Z]/.test(newPassword)) return 'At least one uppercase letter';
  if (!/[a-z]/.test(newPassword)) return 'At least one lowercase letter';
  if (DISALLOWED_CHARS.test(newPassword)) {
    return 'That password uses a character that isn\'t allowed';
  }
  if (newPassword !== confirmPassword) return "Passwords don't match";
  return null;
}

export default function ChangePasswordPage() {
  const router = useRouter();
  const hasHydrated = useAuthHydration();
  const accessToken = useAuthStore((state) => state.accessToken);
  const clearAuth = useAuthStore((state) => state.clearAuth);

  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (hasHydrated && !accessToken) {
      router.replace('/signin');
    }
  }, [hasHydrated, accessToken, router]);

  const handleSubmit = async () => {
    const validationError = validate(newPassword, confirmPassword);
    if (validationError) {
      setError(validationError);
      return;
    }

    setError(null);
    setIsSubmitting(true);
    try {
      await api.post('/profile/password', { currentPassword, newPassword });
      // changing the password logs out every other device - this one
      // stays signed in until its access token naturally expires, then
      // needs a fresh sign-in since its session was cleared too
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
      <BackButton />

      <h1 className="animate-rise-in mt-6 text-2xl font-bold text-[var(--color-light)]">
        Change Password
      </h1>

      <div className="mt-8 flex flex-col gap-4">
        <TextInput
          label="Current password"
          type="password"
          value={currentPassword}
          onChange={(event) => setCurrentPassword(event.target.value)}
        />
        <TextInput
          label="New password"
          type="password"
          value={newPassword}
          onChange={(event) => setNewPassword(event.target.value)}
        />
        <ul className="flex flex-col gap-1 text-sm text-[var(--color-primary)]">
          <li>At least One Uppercase</li>
          <li>At least One Lowercase</li>
          <li>At least 12 Characters</li>
          <li>
            Special Characters such as &ldquo;!, ., -, /, \, |, &apos;&rdquo;
            are not allowed
          </li>
        </ul>
        <TextInput
          label="Confirm new password"
          type="password"
          value={confirmPassword}
          onChange={(event) => setConfirmPassword(event.target.value)}
        />
      </div>

      {error && <p className="mt-4 text-sm text-red-400">{error}</p>}

      <button
        type="button"
        onClick={handleSubmit}
        disabled={
          isSubmitting || !currentPassword || !newPassword || !confirmPassword
        }
        className="mt-auto mb-6 rounded-full bg-[var(--color-primary)] py-4 font-semibold uppercase text-[var(--color-dark)] disabled:opacity-40"
      >
        {isSubmitting ? 'Saving...' : 'Save'}
      </button>
    </GlowBackground>
  );
}
