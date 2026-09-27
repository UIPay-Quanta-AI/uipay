'use client';

import QRCode from 'qrcode';
import { useState } from 'react';
import { AdminBackground } from '@/components/admin/AdminBackground';
import { AdminHeader } from '@/components/admin/AdminHeader';
import { TextInput } from '@/components/TextInput';
import api, { getApiErrorMessage } from '@/services/api';

interface ResolvedAccount {
  userId: string;
  accountName: string;
}

interface GeneratedQr {
  qrCode: string;
  amount: number;
  expiresIn: number;
  recipientName: string;
}

export default function AdminCreateQrPage() {
  const [accountNumber, setAccountNumber] = useState('');
  const [amount, setAmount] = useState('');
  const [resolved, setResolved] = useState<ResolvedAccount | null>(null);
  const [generated, setGenerated] = useState<GeneratedQr | null>(null);
  const [qrImage, setQrImage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const resolveAccount = async () => {
    setError(null);
    setResolved(null);
    setGenerated(null);
    if (!accountNumber.trim()) return;
    setBusy(true);
    try {
      const res = await api.get(`/wallet/resolve/${accountNumber.trim()}`);
      setResolved(res.data.data);
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const generate = async () => {
    if (!resolved || !amount) return;
    setBusy(true);
    setError(null);
    setQrImage(null);
    try {
      const res = await api.post('/admin/qr/generate', {
        recipientId: resolved.userId,
        amount: Number(amount),
      });
      setGenerated(res.data.data);

      // Encode the exact same raw string the customer's scanner decodes and
      // sends to /qr/validate - a real scannable image, not just the code
      // printed as text.
      const dataUrl = await QRCode.toDataURL(res.data.data.qrCode, {
        width: 260,
        margin: 2,
        color: { dark: '#081020', light: '#ffffff' },
      });
      setQrImage(dataUrl);
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <AdminBackground>
      <AdminHeader title="Create QR" />

      <div className="flex flex-col gap-4 px-6">
        <p className="text-sm text-white/50">
          Generate a one-time payment code for any UIPay account number - the
          customer scans it in the app and pays the exact amount, no merchant
          application required.
        </p>

        <TextInput
          label="Recipient account number"
          placeholder="10-digit account number"
          value={accountNumber}
          onChange={(e) => setAccountNumber(e.target.value)}
          onBlur={resolveAccount}
        />

        {resolved && (
          <p className="text-[var(--color-primary)]">
            Paying: {resolved.accountName}
          </p>
        )}

        <TextInput
          label="Amount (NGN)"
          type="number"
          placeholder="5000"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
        />

        {error && <p className="text-sm text-red-400">{error}</p>}

        <button
          type="button"
          disabled={!resolved || !amount || busy}
          onClick={generate}
          className="rounded-full bg-[var(--color-primary)] py-4 font-semibold text-[var(--color-dark)] disabled:opacity-50"
        >
          Generate QR
        </button>

        {generated && (
          <div className="mt-4 rounded-2xl bg-[rgba(var(--color-primary-rgb),0.15)] p-5 text-center text-[var(--color-light)]">
            {qrImage ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={qrImage}
                alt="Scannable payment QR code"
                className="mx-auto rounded-xl bg-white p-2"
                width={260}
                height={260}
              />
            ) : (
              <p className="text-sm text-white/60">Rendering code…</p>
            )}
            <p className="mt-3 text-lg font-semibold">
              ₦{generated.amount.toLocaleString()} → {generated.recipientName}
            </p>
            <p className="mt-1 text-sm text-white/50">
              Expires in {Math.round(generated.expiresIn / 60)} minutes
            </p>
            <details className="mt-3 text-left">
              <summary className="cursor-pointer text-xs text-white/40">
                Raw code value (for manual entry)
              </summary>
              <p className="mt-1 break-all font-mono text-xs text-white/50">
                {generated.qrCode}
              </p>
            </details>
          </div>
        )}
      </div>
    </AdminBackground>
  );
}
