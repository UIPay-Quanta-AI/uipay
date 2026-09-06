import { useEffect } from 'react';
import { create } from 'zustand';

interface User {
  id: string;
  email: string;
  firstName?: string;
  lastName?: string;
}

interface AuthState {
  user: User | null;
  accessToken: string | null;
  // false until hydrate() has run once on the client - lets a guard wait
  // for that instead of judging accessToken before we've even checked
  // localStorage (see hydrate() below)
  hasHydrated: boolean;
  setSession: (
    accessToken: string,
    refreshToken: string,
    extra?: { firstName?: string; lastName?: string },
  ) => void;
  clearAuth: () => void;
  hydrate: () => void;
}

// reads the id and email straight out of the access token instead of
// needing a separate "who am i" endpoint, since the backend already puts
// them in the token payload
function decodeAccessToken(
  token: string,
): { sub: string; email: string } | null {
  try {
    const payload = token.split('.')[1];
    return JSON.parse(atob(payload));
  } catch {
    return null;
  }
}

export const useAuthStore = create<AuthState>((set) => ({
  // always null/false on both server and first client render - reading
  // localStorage here instead would make the server-rendered HTML (which
  // has no localStorage) disagree with the client's first paint, and
  // Next.js throws that away as a hydration mismatch on any hard reload
  // of a page gated on accessToken. hydrate() (below) does the real read,
  // client-only, after mount.
  user: null,
  accessToken: null,
  hasHydrated: false,
  setSession: (accessToken, refreshToken, extra) => {
    const claims = decodeAccessToken(accessToken);
    if (!claims) return;

    localStorage.setItem('access_token', accessToken);
    localStorage.setItem('refresh_token', refreshToken);

    set({
      accessToken,
      user: { id: claims.sub, email: claims.email, ...extra },
      hasHydrated: true,
    });
  },
  clearAuth: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    set({ user: null, accessToken: null, hasHydrated: true });
  },
  hydrate: () => {
    const accessToken = localStorage.getItem('access_token');
    const claims = accessToken ? decodeAccessToken(accessToken) : null;

    set({
      accessToken: claims ? accessToken : null,
      user: claims ? { id: claims.sub, email: claims.email } : null,
      hasHydrated: true,
    });
  },
}));

// call once at the top of any page that gates on accessToken, then wait
// for hasHydrated before deciding to redirect - judging accessToken before
// hydrate() has run would incorrectly treat "haven't checked yet" as
// "not logged in" and bounce a genuinely signed-in user (see the store's
// own comment above for why the read can't just happen at store creation)
export function useAuthHydration() {
  const hasHydrated = useAuthStore((state) => state.hasHydrated);

  useEffect(() => {
    useAuthStore.getState().hydrate();
  }, []);

  return hasHydrated;
}
