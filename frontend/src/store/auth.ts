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
  setSession: (
    accessToken: string,
    refreshToken: string,
    extra?: { firstName?: string; lastName?: string },
  ) => void;
  clearAuth: () => void;
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
  user: null,
  accessToken: null,
  setSession: (accessToken, refreshToken, extra) => {
    const claims = decodeAccessToken(accessToken);
    if (!claims) return;

    localStorage.setItem('access_token', accessToken);
    localStorage.setItem('refresh_token', refreshToken);

    set({
      accessToken,
      user: { id: claims.sub, email: claims.email, ...extra },
    });
  },
  clearAuth: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    set({ user: null, accessToken: null });
  },
}));
