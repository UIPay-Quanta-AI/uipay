'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { AuthScreenLayout } from '@/components/AuthScreenLayout';
import api, { getApiErrorMessage } from '@/services/api';
import { useForgotPasswordStore } from '@/store/forgotPassword';

const OTP_LENGTH = 6;
const OTP_SECONDS = 600;

export default function ForgotPasswordVerifyOtpPage() {
  const router = useRouter();
  const email = useForgotPasswordStore((state) => state.email);
  const setOtp = useForgotPasswordStore((state) => state.setOtp);

  const [digits, setDigits] = useState<string[]>(Array(OTP_LENGTH).fill(''));
  const [secondsLeft, setSecondsLeft] = useState(OTP_SECONDS);
  const [error, setError] = useState<string | null>(null);
  const [isResending, setIsResending] = useState(false);
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  // no pending email means this screen was opened directly (or after a
  // refresh, since the store isn't persisted) - nothing to verify
  useEffect(() => {
    if (!email) {
      router.replace('/forgot-password');
    }
  }, [email, router]);

  useEffect(() => {
    if (secondsLeft <= 0) return;
    const timer = setTimeout(() => setSecondsLeft((value) => value - 1), 1000);
    return () => clearTimeout(timer);
  }, [secondsLeft]);

  const minutes = Math.floor(secondsLeft / 60)
    .toString()
    .padStart(2, '0');
  const seconds = (secondsLeft % 60).toString().padStart(2, '0');

  const handleChange = (index: number, value: string) => {
    const digit = value.replace(/\D/g, '').slice(-1);
    const next = [...digits];
    next[index] = digit;
    setDigits(next);

    if (digit && index < OTP_LENGTH - 1) {
      inputRefs.current[index + 1]?.focus();
    }
  };

  const handleKeyDown = (
    index: number,
    event: React.KeyboardEvent<HTMLInputElement>,
  ) => {
    if (event.key === 'Backspace' && !digits[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  };

  // there's no separate "verify" endpoint for password reset - the OTP is
  // only actually checked once it's submitted together with the new
  // password, so this step just collects it and moves on
  const handleContinue = () => {
    const otp = digits.join('');
    if (otp.length !== OTP_LENGTH) {
      setError('Enter the full 6 digit code');
      return;
    }

    setError(null);
    setOtp(otp);
    router.push('/forgot-password/reset');
  };

  const handleResend = async () => {
    if (!email) return;

    setError(null);
    setIsResending(true);
    try {
      await api.post('/auth/forgot-password', { email });
      setSecondsLeft(OTP_SECONDS);
      setDigits(Array(OTP_LENGTH).fill(''));
      inputRefs.current[0]?.focus();
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setIsResending(false);
    }
  };

  if (!email) return null;

  return (
    <AuthScreenLayout>
      <h1 className="text-3xl font-extrabold text-[var(--color-light)]">
        Confirm Passcode
      </h1>
      <p className="mt-4 text-[var(--color-light)]">
        A one-time code has been sent to your email. Please check your inbox
        or spam. The OTP will expire in{' '}
        <span className="text-[var(--color-primary)]">
          {minutes}:{seconds}
        </span>
      </p>

      <div className="mt-8 flex justify-between gap-2">
        {digits.map((digit, index) => (
          <input
            key={index}
            ref={(el) => {
              inputRefs.current[index] = el;
            }}
            value={digit}
            onChange={(event) => handleChange(index, event.target.value)}
            onKeyDown={(event) => handleKeyDown(index, event)}
            inputMode="numeric"
            maxLength={1}
            className="h-16 w-12 rounded-xl border border-[rgba(var(--color-primary-rgb),0.5)] bg-[rgba(var(--color-primary-rgb),0.1)] text-center text-2xl font-bold text-[var(--color-primary)] focus:border-[var(--color-primary)] focus:outline-none"
          />
        ))}
      </div>

      {error && <p className="mt-4 text-sm text-red-400">{error}</p>}

      <div className="mt-auto flex flex-col gap-4 pb-6">
        <button
          type="button"
          onClick={handleContinue}
          className="rounded-full bg-[var(--color-primary)] py-4 font-semibold uppercase text-[var(--color-dark)]"
        >
          Verify
        </button>
        <button
          type="button"
          onClick={handleResend}
          disabled={isResending || secondsLeft > 0}
          className="text-center text-sm text-[var(--color-light)] underline disabled:opacity-40"
        >
          Didn&apos;t receive any code?
        </button>
      </div>
    </AuthScreenLayout>
  );
}
