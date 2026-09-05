'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { AuthScreenLayout } from '@/components/AuthScreenLayout';
import { TextInput } from '@/components/TextInput';
import api, { getApiErrorMessage } from '@/services/api';
import { useForgotPasswordStore } from '@/store/forgotPassword';

const schema = z.object({
  email: z.string().email('Enter a valid email'),
});

type FormValues = z.infer<typeof schema>;

export default function ForgotPasswordPage() {
  const router = useRouter();
  const setEmail = useForgotPasswordStore((state) => state.setEmail);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const onSubmit = async (values: FormValues) => {
    setSubmitError(null);
    try {
      await api.post('/auth/forgot-password', { email: values.email });
      setEmail(values.email);
      router.push('/forgot-password/verify-otp');
    } catch (error) {
      setSubmitError(getApiErrorMessage(error));
    }
  };

  return (
    <AuthScreenLayout>
      <h1 className="text-3xl font-extrabold text-[var(--color-light)]">
        Forgot Password?
      </h1>
      <p className="mt-2 text-[var(--color-primary)]">
        Input your email to receive a password recovery pin
      </p>

      <form
        onSubmit={handleSubmit(onSubmit)}
        className="mt-8 flex flex-1 flex-col"
      >
        <TextInput
          variant="filled"
          type="email"
          placeholder="example@gmail.com"
          {...register('email')}
          error={errors.email?.message}
        />

        {submitError && (
          <p className="mt-4 text-sm text-red-400">{submitError}</p>
        )}

        <button
          type="submit"
          disabled={isSubmitting}
          className="mt-auto mb-6 rounded-full bg-[var(--color-primary)] py-4 font-semibold uppercase text-[var(--color-dark)] disabled:opacity-60"
        >
          {isSubmitting ? 'Sending...' : 'Send Code'}
        </button>
      </form>
    </AuthScreenLayout>
  );
}
