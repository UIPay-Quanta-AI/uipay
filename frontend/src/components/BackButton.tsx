'use client';

import { ArrowLeft } from 'lucide-react';
import { useRouter } from 'next/navigation';

export function BackButton({ onClick }: { onClick?: () => void }) {
  const router = useRouter();

  return (
    <button
      type="button"
      onClick={onClick ?? (() => router.back())}
      aria-label="Go back"
      className="text-[var(--color-light)]"
    >
      <ArrowLeft className="h-6 w-6" />
    </button>
  );
}
