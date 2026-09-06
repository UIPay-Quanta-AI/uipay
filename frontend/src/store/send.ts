import { create } from 'zustand';

interface Recipient {
  userId: string;
  accountName: string;
  accountNumber: string;
}

interface LastTransaction {
  amount: number;
  accountName: string;
  reference: string;
}

interface SendState {
  recipient: Recipient | null;
  amount: number | null;
  lastTransaction: LastTransaction | null;
  lastError: string | null;
  setRecipient: (recipient: Recipient) => void;
  setAmount: (amount: number) => void;
  setLastTransaction: (lastTransaction: LastTransaction) => void;
  setLastError: (message: string) => void;
  clear: () => void;
}

// in-memory only, same reasoning as useSignupStore/useForgotPasswordStore -
// a refresh mid-flow should send the user back to the start, not resume
// with stale recipient/amount data
export const useSendStore = create<SendState>((set) => ({
  recipient: null,
  amount: null,
  lastTransaction: null,
  lastError: null,
  setRecipient: (recipient) => set({ recipient }),
  setAmount: (amount) => set({ amount }),
  setLastTransaction: (lastTransaction) => set({ lastTransaction }),
  setLastError: (lastError) => set({ lastError }),
  clear: () =>
    set({ recipient: null, amount: null, lastTransaction: null, lastError: null }),
}));
