import { create } from 'zustand';

export interface PendingSignup {
  emailAddress: string;
  password: string;
  firstName: string;
  lastName: string;
  dob: string;
  phoneNumber: string;
}

interface SignupState {
  pending: PendingSignup | null;
  setPending: (data: PendingSignup) => void;
  clear: () => void;
}

// holds the just-submitted signup form in memory so the OTP screen can
// resend the code (register has to be called again with the full form,
// not just the email) and so we know the person's name once they verify.
// this is intentionally not persisted anywhere, so a page refresh mid-flow
// sends the user back to the start
export const useSignupStore = create<SignupState>((set) => ({
  pending: null,
  setPending: (data) => set({ pending: data }),
  clear: () => set({ pending: null }),
}));
