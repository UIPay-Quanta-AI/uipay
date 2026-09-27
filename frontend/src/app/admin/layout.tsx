'use client';

import { usePathname, useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import api from '@/services/api';
import { useAuthHydration, useAuthStore } from '@/store/auth';

type GuardState = 'checking' | 'ok' | 'denied';

// Every /admin/* route except the login page itself must be signed in AND
// hold an admin-role account. The access token has no role claim in it
// (see backend JwtPayload), so the only way to know is to actually ask an
// admin-only endpoint and see whether it accepts or 403s.
export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const hasHydrated = useAuthHydration();
  const accessToken = useAuthStore((state) => state.accessToken);
  const clearAuth = useAuthStore((state) => state.clearAuth);
  const [guard, setGuard] = useState<GuardState>('checking');

  const isLoginPage = pathname === '/admin/login';

  useEffect(() => {
    if (isLoginPage) return;
    if (!hasHydrated) return;

    if (!accessToken) {
      router.replace('/admin/login');
      return;
    }

    let cancelled = false;

    api
      .get('/admin/nfc-qr-count')
      .then(() => {
        if (!cancelled) setGuard('ok');
      })
      .catch((error) => {
        if (cancelled) return;
        // a stale/regular-user token: clear it so the login form isn't
        // sitting behind a token that will just 403 again
        if (error?.response?.status === 401 || error?.response?.status === 403) {
          clearAuth();
        }
        setGuard('denied');
        router.replace('/admin/login');
      });

    return () => {
      cancelled = true;
    };
  }, [isLoginPage, hasHydrated, accessToken, router, clearAuth]);

  if (isLoginPage) return <>{children}</>;

  if (guard !== 'ok') {
    return (
      <main className="flex h-screen w-screen items-center justify-center bg-[var(--color-dark)]">
        <p className="text-[var(--color-light)]">Checking admin access…</p>
      </main>
    );
  }

  return <>{children}</>;
}
