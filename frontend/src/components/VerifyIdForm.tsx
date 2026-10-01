'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { AuthScreenLayout } from './AuthScreenLayout';
import { TextInput } from './TextInput';
import api, { getApiErrorMessage } from '@/services/api';
import { useAuthHydration, useAuthStore } from '@/store/auth';

const COPY = {
  bvn: {
    title: 'Enter your BVN',
    subtitle: 'Upload your Bank Verification Number',
    placeholder: 'Input BVN',
  },
  nin: {
    title: 'Enter your NIN',
    subtitle: 'Upload your National Identification Number',
    placeholder: 'Input NIN',
  },
};

export function VerifyIdForm({ idType }: { idType: 'bvn' | 'nin' }) {
  const router = useRouter();
  const hasHydrated = useAuthHydration();
  const accessToken = useAuthStore((state) => state.accessToken);
  const [value, setValue] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { title, subtitle, placeholder } = COPY[idType];

  useEffect(() => {
    if (hasHydrated && !accessToken) {
      router.replace('/profile-setup');
    }
  }, [hasHydrated, accessToken, router]);

  const handleVerify = async () => {
    if (!/^\d{11}$/.test(value)) {
      setError(`${idType.toUpperCase()} must be exactly 11 digits`);
      return;
    }

    setError(null);
    setIsSubmitting(true);
    try {
      await api.post('/profile/verify-id', { idType, idNumber: value });
      router.push('/dashboard');
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!hasHydrated || !accessToken) return null;

  return (
    <AuthScreenLayout>
      <h1 className="text-3xl font-extrabold text-[var(--color-light)]">
        {title}
      </h1>
      <p className="mt-2 text-[var(--color-primary)]">{subtitle}</p>

      <div className="mt-8">
        <TextInput
          value={value}
          onChange={(event) =>
            setValue(event.target.value.replace(/\D/g, '').slice(0, 11))
          }
          placeholder={placeholder}
          inputMode="numeric"
        />
      </div>

      {error && <p className="mt-4 text-sm text-red-400">{error}</p>}

      <button
        type="button"
        onClick={handleVerify}
        disabled={isSubmitting}
        className="mt-auto mb-6 rounded-full bg-[var(--color-primary)] py-4 font-semibold uppercase text-[var(--color-dark)] disabled:opacity-60"
      >
        {isSubmitting ? 'Verifying...' : 'Verify'}
      </button>
    </AuthScreenLayout>
  );
}
