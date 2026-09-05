import { create } from 'zustand';

interface ForgotPasswordState {
  email: string | null;
  otp: string | null;
  setEmail: (email: string) => void;
  setOtp: (otp: string) => void;
  clear: () => void;
}

// same reasoning as useSignupStore: intentionally not persisted, so a
// refresh mid-flow sends the user back to the start instead of holding a
// stale OTP/email pair
export const useForgotPasswordStore = create<ForgotPasswordState>((set) => ({
  email: null,
  otp: null,
  setEmail: (email) => set({ email }),
  setOtp: (otp) => set({ otp }),
  clear: () => set({ email: null, otp: null }),
}));
