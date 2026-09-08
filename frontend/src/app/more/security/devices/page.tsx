'use client';

import { Monitor, X } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { BackButton } from '@/components/BackButton';
import { GlowBackground } from '@/components/GlowBackground';
import api, { getApiErrorMessage } from '@/services/api';
import { useAuthHydration, useAuthStore } from '@/store/auth';

interface Session {
  id: string;
  userAgent: string | null;
  ipAddress: string | null;
  createdAt: string;
}

// a real user-agent string is a mouthful ("Mozilla/5.0 (Windows NT 10.0;
// Win64; x64) AppleWebKit/537.36...") - pull out just the browser/OS,
// which is all the mockup's "device" label actually needs
function describeDevice(userAgent: string | null): string {
  if (!userAgent) return 'Unknown device';

  const os = /Windows/.test(userAgent)
    ? 'Windows'
    : /Android/.test(userAgent)
      ? 'Android'
      : /iPhone|iPad/.test(userAgent)
        ? 'iOS'
        : /Mac OS/.test(userAgent)
          ? 'Mac'
          : /Linux/.test(userAgent)
            ? 'Linux'
            : 'Unknown OS';

  const browser = /Edg\//.test(userAgent)
    ? 'Edge'
    : /Chrome\//.test(userAgent)
      ? 'Chrome'
      : /Firefox\//.test(userAgent)
        ? 'Firefox'
        : /Safari\//.test(userAgent)
          ? 'Safari'
          : 'a browser';

  return `${browser} on ${os}`;
}

export default function DevicesPage() {
  const router = useRouter();
  const hasHydrated = useAuthHydration();
  const accessToken = useAuthStore((state) => state.accessToken);

  const [sessions, setSessions] = useState<Session[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [revokingId, setRevokingId] = useState<string | null>(null);

  useEffect(() => {
    if (hasHydrated && !accessToken) {
      router.replace('/signin');
    }
  }, [hasHydrated, accessToken, router]);

  useEffect(() => {
    if (!accessToken) return;
    api
      .get('/profile/sessions')
      .then((res) => setSessions(res.data.data))
      .catch((err) => setError(getApiErrorMessage(err)))
      .finally(() => setIsLoading(false));
  }, [accessToken]);

  const handleRevoke = async (id: string) => {
    setRevokingId(id);
    try {
      await api.delete(`/profile/sessions/${id}`);
      setSessions((prev) => prev.filter((session) => session.id !== id));
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setRevokingId(null);
    }
  };

  if (!hasHydrated || !accessToken) return null;

  return (
    <GlowBackground className="flex flex-col px-6 py-10">
      <div className="flex items-center gap-4">
        <BackButton />
        <h1 className="text-xl font-bold text-[var(--color-light)]">
          Active Devices
        </h1>
      </div>

      {error && <p className="mt-4 text-sm text-red-400">{error}</p>}

      <div className="mt-6 flex flex-col gap-3">
        {isLoading && (
          <p className="text-sm text-white/40">Loading...</p>
        )}
        {!isLoading && sessions.length === 0 && (
          <p className="text-sm text-white/40">No active sessions found.</p>
        )}
        {sessions.map((session) => (
          <div
            key={session.id}
            className="flex items-center justify-between rounded-xl bg-[#0d1929] px-4 py-4"
          >
            <div className="flex items-center gap-3">
              <span className="flex h-10 w-10 items-center justify-center rounded-full bg-[rgba(var(--color-primary-rgb),0.15)]">
                <Monitor className="h-5 w-5 text-[var(--color-primary)]" />
              </span>
              <div className="flex flex-col">
                <span className="text-sm font-semibold text-[var(--color-light)]">
                  {describeDevice(session.userAgent)}
                </span>
                <span className="text-xs text-white/40">
                  Signed in {new Date(session.createdAt).toLocaleDateString()}
                </span>
              </div>
            </div>
            <button
              type="button"
              aria-label="Sign out this device"
              onClick={() => handleRevoke(session.id)}
              disabled={revokingId === session.id}
              className="flex h-8 w-8 items-center justify-center rounded-full bg-red-500/15 text-red-400 disabled:opacity-40"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        ))}
      </div>
    </GlowBackground>
  );
}
