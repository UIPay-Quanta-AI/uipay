'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { GlowBackground } from '@/components/GlowBackground';
import { TextInput } from '@/components/TextInput';
import api, { getApiErrorMessage } from '@/services/api';
import { useAuthStore } from '@/store/auth';

const schema = z.object({
  email: z.string().email('Enter a valid email'),
  password: z.string().min(1, 'Password is required'),
});

type FormValues = z.infer<typeof schema>;

interface SignInResponse {
  status: string;
  message: string;
  data: { accessToken: string; refreshToken: string };
}

export default function SignInPage() {
  const router = useRouter();
  const setSession = useAuthStore((state) => state.setSession);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const onSubmit = async (values: FormValues) => {
    setSubmitError(null);
    try {
      const response = await api.post<SignInResponse>('/auth/signin', values);
      setSession(
        response.data.data.accessToken,
        response.data.data.refreshToken,
      );
      router.push('/dashboard');
    } catch (error) {
      setSubmitError(getApiErrorMessage(error));
    }
  };

  return (
    <GlowBackground className="flex min-h-screen items-center justify-center px-8">
      <div className="flex w-full max-w-sm flex-col gap-6">
        <h1 className="text-center text-3xl font-extrabold text-[var(--color-light)]">
          Welcome Back
        </h1>

        <form
          onSubmit={handleSubmit(onSubmit)}
          className="flex flex-col gap-4"
        >
          <TextInput
            label="Email"
            type="email"
            placeholder="example@gmail.com"
            {...register('email')}
            error={errors.email?.message}
          />
          <TextInput
            label="Password"
            type="password"
            placeholder="************"
            {...register('password')}
            error={errors.password?.message}
          />

          {submitError && (
            <p className="text-sm text-red-400">{submitError}</p>
          )}

          <button
            type="submit"
            disabled={isSubmitting}
            className="mt-2 rounded-full bg-[var(--color-primary)] py-4 font-semibold uppercase text-[var(--color-dark)] disabled:opacity-60"
          >
            {isSubmitting ? 'Signing in...' : 'Sign In'}
          </button>

          <p className="text-center text-sm text-[var(--color-light)]">
            Don&apos;t have an account?{' '}
            <Link
              href="/profile-setup"
              className="text-[var(--color-primary)] underline"
            >
              Sign up
            </Link>
          </p>
        </form>
      </div>
    </GlowBackground>
  );
}
