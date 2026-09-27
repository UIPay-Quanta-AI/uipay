import { WalletMinimal } from 'lucide-react';

export interface Transaction {
  id: string;
  type: 'transfer' | 'funding';
  senderId: string | null;
  recipientId: string | null;
  senderName: string;
  recipientName: string;
  amount: string;
  method: string;
  reference: string;
  status: string;
  createdAt: string;
}

function formatNaira(amount: number | string) {
  return `₦${Number(amount).toLocaleString('en-NG', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

// Shared between the dashboard's "Recent Transactions" (top 5) and the full
// /history page, so the two never drift apart on how a row looks.
export function TransactionRow({
  tx,
  userId,
}: {
  tx: Transaction;
  userId: string | undefined;
}) {
  if (tx.type === 'funding') {
    return (
      <div className="flex items-center justify-between rounded-2xl bg-[#0d1929] px-4 py-3">
        <div className="flex items-center gap-3">
          <span className="flex h-9 w-9 items-center justify-center rounded-full bg-orange-400/15 text-orange-400">
            <WalletMinimal className="h-4 w-4" />
          </span>
          <div className="flex flex-col">
            <span className="text-sm text-[var(--color-light)]">
              Wallet funding via Paystack
            </span>
            <span className="text-xs text-white/40">
              {tx.reference.slice(0, 10)}...
            </span>
          </div>
        </div>
        <span className="text-sm font-semibold text-[var(--color-primary)]">
          +{formatNaira(tx.amount)}
        </span>
      </div>
    );
  }

  const isDebit = tx.senderId === userId;
  const counterpartName = isDebit ? tx.recipientName : tx.senderName;
  const verb =
    tx.method === 'nfc' ? 'NFC payment' : tx.method === 'qr' ? 'QR payment' : 'Transfer';
  const label = isDebit
    ? `${verb} to ${counterpartName}`
    : `${verb} from ${counterpartName}`;

  return (
    <div className="flex items-center justify-between rounded-2xl bg-[#0d1929] px-4 py-3">
      <div className="flex items-center gap-3">
        <span className="flex h-9 w-9 items-center justify-center rounded-full bg-[rgba(var(--color-primary-rgb),0.15)] text-sm font-bold text-[var(--color-primary)]">
          {counterpartName.charAt(0).toUpperCase()}
        </span>
        <div className="flex flex-col">
          <span className="text-sm text-[var(--color-light)]">{label}</span>
          <span className="text-xs text-white/40">
            {tx.reference.slice(0, 10)}...
          </span>
        </div>
      </div>
      <span
        className={`text-sm font-semibold ${
          isDebit ? 'text-red-400' : 'text-[var(--color-primary)]'
        }`}
      >
        {isDebit ? '-' : '+'}
        {formatNaira(tx.amount)}
      </span>
    </div>
  );
}
