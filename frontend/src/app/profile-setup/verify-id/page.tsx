'use client';

import { ChevronRight } from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { AuthScreenLayout } from '@/components/AuthScreenLayout';
import { useAuthHydration, useAuthStore } from '@/store/auth';

export default function VerifyIdPage() {
  const router = useRouter();
  const hasHydrated = useAuthHydration();
  const accessToken = useAuthStore((state) => state.accessToken);

  // this screen only makes sense once the account is created and verified
  useEffect(() => {
    if (hasHydrated && !accessToken) {
      router.replace('/profile-setup');
    }
  }, [hasHydrated, accessToken, router]);

  if (!hasHydrated || !accessToken) return null;

  return (
    <AuthScreenLayout>
      <h1 className="text-3xl font-extrabold text-[var(--color-light)]">
        Choose a Verified ID
      </h1>
      <p className="mt-4 text-[var(--color-primary)]">
        We require a government certified means of identification
      </p>

      <div className="mt-8 flex flex-col gap-4">
        <Link
          href="/profile-setup/verify-id/nin"
          className="flex items-center justify-between rounded-xl bg-[rgba(var(--color-primary-rgb),0.1)] px-5 py-4 text-[var(--color-light)]"
        >
          NIN
          <ChevronRight className="h-5 w-5" />
        </Link>
        <Link
          href="/profile-setup/verify-id/bvn"
          className="flex items-center justify-between rounded-xl bg-[rgba(var(--color-primary-rgb),0.1)] px-5 py-4 text-[var(--color-light)]"
        >
          BVN
          <ChevronRight className="h-5 w-5" />
        </Link>
      </div>

      <button
        type="button"
        onClick={() => router.push('/signin')}
        className="mt-auto pb-6 text-center text-white/50 underline"
      >
        Skip
      </button>
    </AuthScreenLayout>
  );
}
