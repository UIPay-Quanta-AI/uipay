import { create } from 'zustand';

// what's being paid, and how the final PIN step should submit it - one
// shared amount/confirm/pin/success flow serves all three payment methods
// instead of duplicating those screens per method
export type PaymentSource =
  | { method: 'wallet'; recipientId: string; name: string; detail: string }
  | { method: 'nfc'; tagId: string; name: string; detail: string }
  | {
      method: 'qr';
      qrCode: string;
      name: string;
      detail: string;
      fixedAmount?: number;
    };

interface LastTransaction {
  amount: number;
  name: string;
  reference: string;
  date: string;
}

interface SendState {
  source: PaymentSource | null;
  amount: number | null;
  lastTransaction: LastTransaction | null;
  lastError: string | null;
  setSource: (source: PaymentSource) => void;
  setAmount: (amount: number) => void;
  setLastTransaction: (lastTransaction: LastTransaction) => void;
  setLastError: (message: string) => void;
  clear: () => void;
}

// in-memory only, same reasoning as useSignupStore/useForgotPasswordStore -
// a refresh mid-flow should send the user back to the start, not resume
// with a stale payment source/amount
export const useSendStore = create<SendState>((set) => ({
  source: null,
  amount: null,
  lastTransaction: null,
  lastError: null,
  setSource: (source) => set({ source }),
  setAmount: (amount) => set({ amount }),
  setLastTransaction: (lastTransaction) => set({ lastTransaction }),
  setLastError: (lastError) => set({ lastError }),
  clear: () =>
    set({ source: null, amount: null, lastTransaction: null, lastError: null }),
}));
