'use client';

import { Award } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { AuthScreenLayout } from '@/components/AuthScreenLayout';
import { TextInput } from '@/components/TextInput';
import api, { getApiErrorMessage } from '@/services/api';
import { useAuthHydration, useAuthStore } from '@/store/auth';

interface Profile {
  firstName: string;
  lastName: string;
  dob: string;
  email: string;
  phoneNumber: string;
  identityVerifiedAt: string | null;
}

export default function ProfilePage() {
  const router = useRouter();
  const hasHydrated = useAuthHydration();
  const accessToken = useAuthStore((state) => state.accessToken);

  const [profile, setProfile] = useState<Profile | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [isEditing, setIsEditing] = useState(false);
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [phoneDigits, setPhoneDigits] = useState('');
  const [saveError, setSaveError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (hasHydrated && !accessToken) {
      router.replace('/signin');
    }
  }, [hasHydrated, accessToken, router]);

  useEffect(() => {
    if (!accessToken) return;

    api
      .get('/profile/me')
      .then((response) => setProfile(response.data.data))
      .catch((err) => setError(getApiErrorMessage(err)));
  }, [accessToken]);

  if (!hasHydrated || !accessToken) return null;

  const [year, month, day] = profile?.dob.split('-') ?? ['', '', ''];
  const phoneWithoutCountryCode = profile?.phoneNumber.replace(/^\+234/, '');

  const startEditing = () => {
    if (!profile) return;
    setFirstName(profile.firstName);
    setLastName(profile.lastName);
    setPhoneDigits(phoneWithoutCountryCode ?? '');
    setSaveError(null);
    setIsEditing(true);
  };

  const handleSave = async () => {
    if (!firstName.trim() || !lastName.trim()) {
      setSaveError('First and last name cannot be empty');
      return;
    }

    setSaveError(null);
    setIsSaving(true);
    try {
      const response = await api.patch('/profile/me', {
        firstName: firstName.trim(),
        lastName: lastName.trim(),
        phoneNumber: `+234${phoneDigits}`,
      });
      setProfile((prev) => (prev ? { ...prev, ...response.data.data } : prev));
      setIsEditing(false);
    } catch (err) {
      setSaveError(getApiErrorMessage(err));
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <AuthScreenLayout>
      <div className="flex flex-col items-center gap-2">
        <div className="relative">
          <span className="flex h-24 w-24 items-center justify-center rounded-full bg-[rgba(var(--color-primary-rgb),0.15)] text-3xl font-bold text-[var(--color-primary)]">
            {profile?.firstName?.charAt(0).toUpperCase() ?? ''}
          </span>
          {profile?.identityVerifiedAt && (
            <span className="absolute -right-1 -top-1 flex h-8 w-8 items-center justify-center rounded-full bg-[var(--color-light)] text-[var(--color-primary)]">
              <Award className="h-5 w-5" />
            </span>
          )}
        </div>
        <h1 className="text-2xl font-bold text-[var(--color-light)]">
          {profile?.firstName}
        </h1>
      </div>

      {error && <p className="mt-4 text-sm text-red-400">{error}</p>}

      <div className="mt-8 flex flex-col gap-4">
        <TextInput
          label="First name"
          value={isEditing ? firstName : (profile?.firstName ?? '')}
          onChange={(event) => setFirstName(event.target.value)}
          readOnly={!isEditing}
        />
        <TextInput
          label="Last name"
          value={isEditing ? lastName : (profile?.lastName ?? '')}
          onChange={(event) => setLastName(event.target.value)}
          readOnly={!isEditing}
        />

        <div className="flex flex-col gap-2">
          <label className="text-sm text-[var(--color-light)]">
            Date of Birth
          </label>
          <div className="flex gap-3">
            <input
              value={day}
              readOnly
              className="w-full rounded-xl border border-white/20 bg-transparent px-4 py-3 text-center text-[var(--color-light)] focus:outline-none"
            />
            <input
              value={month}
              readOnly
              className="w-full rounded-xl border border-white/20 bg-transparent px-4 py-3 text-center text-[var(--color-light)] focus:outline-none"
            />
            <input
              value={year}
              readOnly
              className="w-full rounded-xl border border-white/20 bg-transparent px-4 py-3 text-center text-[var(--color-light)] focus:outline-none"
            />
          </div>
        </div>

        <TextInput label="Email" value={profile?.email ?? ''} readOnly />

        <div className="flex flex-col gap-2">
          <label className="text-sm text-[var(--color-light)]">
            Phone number
          </label>
          <div className="flex items-center gap-3 rounded-xl border border-white/20 px-4 py-3 focus-within:border-[var(--color-primary)]">
            <span className="text-[var(--color-light)]">+234</span>
            <span className="h-5 w-px bg-white/20" />
            {isEditing ? (
              <input
                value={phoneDigits}
                onChange={(event) =>
                  setPhoneDigits(event.target.value.replace(/\D/g, '').slice(0, 10))
                }
                inputMode="numeric"
                className="w-full bg-transparent text-[var(--color-light)] focus:outline-none"
              />
            ) : (
              <span className="text-[var(--color-light)]">
                {phoneWithoutCountryCode}
              </span>
            )}
          </div>
        </div>
      </div>

      {saveError && <p className="mt-4 text-sm text-red-400">{saveError}</p>}

      {isEditing ? (
        <div className="mt-auto mb-6 flex flex-col gap-3">
          <button
            type="button"
            onClick={handleSave}
            disabled={isSaving}
            className="rounded-full bg-[var(--color-primary)] py-4 font-semibold text-[var(--color-dark)] transition-transform active:scale-95 disabled:opacity-60"
          >
            {isSaving ? 'Saving...' : 'Save Changes'}
          </button>
          <button
            type="button"
            onClick={() => setIsEditing(false)}
            disabled={isSaving}
            className="rounded-full border border-white/20 py-4 font-semibold text-[var(--color-light)]"
          >
            Cancel
          </button>
        </div>
      ) : (
        <button
          type="button"
          onClick={startEditing}
          className="mt-auto mb-6 rounded-full border border-[var(--color-primary)] py-4 font-semibold text-[var(--color-primary)] transition-transform active:scale-95"
        >
          Edit Profile
        </button>
      )}
    </AuthScreenLayout>
  );
}
