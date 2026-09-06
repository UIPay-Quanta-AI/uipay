import axios, { isAxiosError } from 'axios';

const BACKEND_PORT = 3001;

const api = axios.create();

api.interceptors.request.use((config) => {
  // NEXT_PUBLIC_API_URL is baked in at build/dev-start time, so it goes
  // stale the moment your machine's IP changes (switching wifi networks,
  // reconnecting, etc). Deriving from window.location.hostname instead
  // means the backend URL always matches whatever address you actually
  // used to load the frontend - no config to update when the network
  // changes. NEXT_PUBLIC_API_URL still works as an explicit override for
  // anything that doesn't fit that pattern (a different backend port, a
  // real deployment).
  config.baseURL =
    process.env.NEXT_PUBLIC_API_URL ??
    `${window.location.protocol}//${window.location.hostname}:${BACKEND_PORT}`;

  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Nest's default error shape puts the message in `message`, either as a
// single string or, for validation errors, an array of strings
export function getApiErrorMessage(error: unknown): string {
  if (isAxiosError(error)) {
    const message = (error.response?.data as { message?: unknown })?.message;
    if (Array.isArray(message)) return message.join(', ');
    if (typeof message === 'string') return message;
  }

  return 'Something went wrong. Please try again.';
}

export default api;
