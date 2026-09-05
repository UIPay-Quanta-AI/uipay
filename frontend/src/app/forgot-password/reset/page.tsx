'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { AuthScreenLayout } from '@/components/AuthScreenLayout';
import { TextInput } from '@/components/TextInput';
import api, { getApiErrorMessage } from '@/services/api';
import { useForgotPasswordStore } from '@/store/forgotPassword';

// disallows the punctuation shown in the on-screen password rules
const DISALLOWED_CHARS = /["'!.\-/\\|]/;

const schema = z
  .object({
    password: z
      .string()
      .min(12, 'At least 12 characters')
      .regex(/[A-Z]/, 'At least one uppercase letter')
      .regex(/[a-z]/, 'At least one lowercase letter')
      .refine(
        (value) => !DISALLOWED_CHARS.test(value),
        'That password uses a character that isn\'t allowed',
      ),
    confirmPassword: z.string(),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Passwords don't match",
    path: ['confirmPassword'],
  });

type FormValues = z.infer<typeof schema>;

export default function ForgotPasswordResetPage() {
  const router = useRouter();
  const email = useForgotPasswordStore((state) => state.email);
  const otp = useForgotPasswordStore((state) => state.otp);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  // no pending email/otp means this screen was opened directly (or after a
  // refresh, since the store isn't persisted) - nothing to submit
  useEffect(() => {
    if (!email || !otp) {
      router.replace('/forgot-password');
    }
  }, [email, otp, router]);

  const onSubmit = async (values: FormValues) => {
    if (!email || !otp) return;

    setSubmitError(null);
    try {
      await api.post('/auth/reset-password', {
        email,
        otp,
        newPassword: values.password,
      });
      // not clearing pending here - this page's own guard effect depends on
      // email/otp, and clearing them while still mounted (push doesn't
      // unmount synchronously) fires that guard's redirect to
      // /forgot-password, racing the navigation to /signin below. The OTP
      // is already single-use on the backend (deleted from redis on a
      // successful reset), so leaving this in memory a moment longer is
      // harmless - the store gets a fresh email/otp on the next flow anyway.
      router.push('/signin');
    } catch (error) {
      setSubmitError(getApiErrorMessage(error));
    }
  };

  if (!email || !otp) return null;

  return (
    <AuthScreenLayout>
      <h1 className="text-3xl font-extrabold text-[var(--color-light)]">
        Set New Password
      </h1>

      <form
        onSubmit={handleSubmit(onSubmit)}
        className="mt-8 flex flex-1 flex-col"
      >
        <label className="text-[var(--color-light)]">Input new password</label>
        <div className="mt-2">
          <TextInput
            variant="filled"
            type="password"
            {...register('password')}
            error={errors.password?.message}
          />
        </div>

        <ul className="mt-3 flex flex-col gap-1 text-sm text-[var(--color-primary)]">
          <li>At least One Uppercase</li>
          <li>At least One Lowercase</li>
          <li>At least 12 Characters</li>
          <li>
            Special Characters such as &ldquo;!, ., -, /, \, |, &apos;&rdquo;
            are not allowed
          </li>
        </ul>

        <label className="mt-6 text-[var(--color-light)]">
          Confirm new password
        </label>
        <div className="mt-2">
          <TextInput
            variant="filled"
            type="password"
            {...register('confirmPassword')}
            error={errors.confirmPassword?.message}
          />
        </div>

        {submitError && (
          <p className="mt-4 text-sm text-red-400">{submitError}</p>
        )}

        <button
          type="submit"
          disabled={isSubmitting}
          className="mt-auto mb-6 rounded-full bg-[var(--color-primary)] py-4 font-semibold uppercase text-[var(--color-dark)] disabled:opacity-60"
        >
          {isSubmitting ? 'Saving...' : 'Finish'}
        </button>
      </form>
    </AuthScreenLayout>
  );
}
