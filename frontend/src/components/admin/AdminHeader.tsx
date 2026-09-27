'use client';

import { ArrowLeft } from 'lucide-react';
import { useRouter } from 'next/navigation';

interface AdminHeaderProps {
  title: string;
  rightSlot?: React.ReactNode;
  onBack?: () => void;
}

// shared back-arrow + centered-title header used across every inner admin
// screen (merchants/users/transactions list & detail) - the mockups repeat
// this exact layout everywhere
export function AdminHeader({ title, rightSlot, onBack }: AdminHeaderProps) {
  const router = useRouter();

  return (
    <div className="relative flex items-center justify-center px-6 pb-6 pt-8">
      <button
        type="button"
        onClick={onBack ?? (() => router.back())}
        aria-label="Go back"
        className="absolute left-6 text-[var(--color-light)]"
      >
        <ArrowLeft className="h-6 w-6" />
      </button>
      <h1 className="text-lg font-bold uppercase tracking-wide text-[var(--color-light)]">
        {title}
      </h1>
      {rightSlot && <div className="absolute right-6">{rightSlot}</div>}
    </div>
  );
}
