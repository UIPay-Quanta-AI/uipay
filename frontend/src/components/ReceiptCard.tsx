import { forwardRef } from 'react';

function formatNaira(amount: number) {
  return `₦${amount.toLocaleString('en-NG', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleString('en-NG', {
    dateStyle: 'long',
    timeStyle: 'short',
  });
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-1 border-b border-white/10 pb-3">
      <span className="text-xs text-white/40">{label}</span>
      <span className="text-sm font-semibold text-[var(--color-light)]">{value}</span>
    </div>
  );
}

export interface ReceiptData {
  amount: number;
  reference: string;
  date: string;
  methodLabel: string;
  senderName: string | null;
  beneficiaryName: string;
  beneficiaryDetail: string | null;
}

// Forwards a ref to the outer node so html2canvas (in the success page) can
// capture exactly this element - the on-screen receipt and the
// shared/downloaded image are the same markup, not two things to keep in
// sync. Plain solid colors and a row of circle divs for the scalloped edge
// are deliberate - html2canvas renders gradients/masks inconsistently, but
// flat shapes like these are its reliable case.
export const ReceiptCard = forwardRef<HTMLDivElement, ReceiptData>(
  function ReceiptCard(
    { amount, reference, date, methodLabel, senderName, beneficiaryName, beneficiaryDetail },
    ref,
  ) {
    return (
      <div ref={ref} className="w-full max-w-sm bg-[var(--color-dark)] pb-3">
        <div className="bg-[var(--color-primary)] px-6 pb-10 pt-7">
          <div className="flex items-center justify-between">
            <span className="text-xl font-extrabold tracking-wide text-white">
              UIPay
            </span>
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white">
              {/* plain <img>, not next/image - avoids the optimizer's
                  query-string URL, which can taint the canvas html2canvas
                  captures */}
              <img src="/logo-icon.png" alt="" className="h-6 w-6 object-contain" />
            </div>
          </div>
        </div>

        <div className="-mt-6 rounded-t-3xl bg-[#0d1929] px-6 pb-6 pt-6">
          <span className="inline-block rounded-md bg-red-500/15 px-2 py-1 text-xs font-bold tracking-wide text-red-400">
            DEBIT
          </span>
          <p className="mt-2 text-4xl font-extrabold text-[var(--color-light)]">
            {formatNaira(amount)}
          </p>

          <div className="mt-6 flex flex-col gap-3">
            <Row label="Transaction Type" value={methodLabel} />
            <Row label="Transaction Status" value="Successful" />
            {senderName && <Row label="Sender Name" value={senderName} />}
            <Row
              label="Beneficiary"
              value={
                beneficiaryDetail
                  ? `${beneficiaryName} | ${beneficiaryDetail}`
                  : beneficiaryName
              }
            />
            <Row label="Transaction Date" value={formatDate(date)} />
            <Row label="Transaction Reference" value={reference} />
          </div>

          <p className="mt-6 text-center text-xs text-white/30">
            Thank you for using UIPay
          </p>
        </div>

        <div className="flex justify-center gap-1.5">
          {Array.from({ length: 16 }).map((_, index) => (
            <span
              key={index}
              className="-mt-2.5 h-5 w-5 rounded-full bg-[var(--color-dark)]"
            />
          ))}
        </div>
      </div>
    );
  },
);
