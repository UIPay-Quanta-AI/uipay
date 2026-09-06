'use client';

import { Landmark, PieChart, PiggyBank, Smartphone } from 'lucide-react';
import Image from 'next/image';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { BackButton } from '@/components/BackButton';
import { GlowBackground } from '@/components/GlowBackground';
import { useAuthHydration, useAuthStore } from '@/store/auth';

export default function TransferMoneyHubPage() {
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
      <BackButton />

      <div className="mt-8 grid grid-cols-2 gap-4">
        <Link
          href="/send/uipay"
          className="col-span-2 flex items-center justify-between rounded-2xl bg-[rgba(var(--color-primary-rgb),0.1)] p-6"
        >
          <span className="text-2xl font-bold text-[var(--color-light)]">
            To
            <br />
            UIPay Account
          </span>
          <span className="flex h-20 w-20 items-center justify-center rounded-full bg-[var(--color-dark)]">
            <Image
              src="/logo-icon.png"
              alt=""
              width={40}
              height={40}
              className="h-10 w-10"
            />
          </span>
        </Link>

        <div
          title="Coming soon"
          className="flex flex-col items-center justify-center gap-4 rounded-2xl bg-[#0d1929] p-6 opacity-40"
        >
          <Landmark className="h-12 w-12 text-[var(--color-primary)]" />
          <span className="text-center text-[var(--color-light)]">
            To Other Bank
          </span>
        </div>

        <div
          title="Coming soon"
          className="flex flex-col items-center justify-center gap-4 rounded-2xl bg-[#0d1929] p-6 opacity-40"
        >
          <Smartphone className="h-12 w-12 text-[var(--color-primary)]" />
          <span className="text-center text-[var(--color-light)]">
            Airtime/Data
          </span>
        </div>

        <div
          title="Coming soon"
          className="flex flex-col items-center justify-center gap-4 rounded-2xl bg-[#0d1929] p-6 opacity-40"
        >
          <PieChart className="h-12 w-12 text-[var(--color-primary)]" />
          <span className="text-center text-[var(--color-light)]">
            Report
          </span>
        </div>

        <div
          title="Coming soon"
          className="flex flex-col items-center justify-center gap-4 rounded-2xl bg-[#0d1929] p-6 opacity-40"
        >
          <PiggyBank className="h-12 w-12 text-[var(--color-primary)]" />
          <span className="text-center text-[var(--color-light)]">
            Savings
          </span>
        </div>
      </div>
    </GlowBackground>
  );
}
