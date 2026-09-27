// @paystack/inline-js ships no TypeScript definitions. This covers only the
// small slice of its API this app actually uses.
declare module '@paystack/inline-js' {
  interface PaystackTransactionOptions {
    key: string;
    email: string;
    amount: number;
    reference?: string;
    currency?: string;
    onSuccess?: (transaction: { id: number; reference: string; message: string }) => void;
    onCancel?: () => void;
    onError?: (error: { message: string }) => void;
  }

  export default class PaystackPop {
    newTransaction(options: PaystackTransactionOptions): void;
  }
}
