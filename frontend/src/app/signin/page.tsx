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
  const [method, setMethod] = useState<'email' | 'phone'>('email');
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
    <GlowBackground className="flex justify-center px-8 py-12">
      <div className="flex w-full max-w-sm flex-col items-center gap-6">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/signin.svg" alt="uipay" className="h-40 w-40" />

        <div className="flex flex-col items-center gap-1 text-center">
          <h1 className="text-3xl font-extrabold text-[var(--color-light)]">
            Login
          </h1>
          <p className="text-[var(--color-primary)]">
            Let&apos;s get you started in a few steps
          </p>
        </div>

        <div className="relative flex w-full border-b border-white/20">
          <button
            type="button"
            onClick={() => setMethod('email')}
            className={`flex-1 pb-2 text-left font-semibold transition-colors duration-300 ${
              method === 'email'
                ? 'text-[var(--color-primary)]'
                : 'text-[var(--color-light)]'
            }`}
          >
            Email
          </button>
          <button
            type="button"
            onClick={() => setMethod('phone')}
            className={`flex-1 pb-2 text-right font-semibold transition-colors duration-300 ${
              method === 'phone'
                ? 'text-[var(--color-primary)]'
                : 'text-[var(--color-light)]'
            }`}
          >
            Phone number
          </button>
          <span
            className="absolute bottom-0 h-0.5 w-1/2 bg-[var(--color-primary)] transition-transform duration-300 ease-out"
            style={{
              transform:
                method === 'phone' ? 'translateX(100%)' : 'translateX(0%)',
            }}
          />
        </div>

        <form
          onSubmit={handleSubmit(onSubmit)}
          className="flex w-full flex-col gap-4"
        >
          <div key={method} className="animate-fade-slide-in">
            {method === 'email' ? (
              <TextInput
                type="email"
                placeholder="example@gmail.com"
                {...register('email')}
                error={errors.email?.message}
              />
            ) : (
              <div className="flex flex-col gap-2">
                <div className="flex items-center gap-3 rounded-xl border border-white/20 px-4 py-3 focus-within:border-[var(--color-primary)]">
                  <span className="text-[var(--color-light)]">+234</span>
                  <span className="h-5 w-px bg-white/20" />
                  <input
                    placeholder="0000000000"
                    inputMode="numeric"
                    className="w-full bg-transparent text-[var(--color-light)] placeholder:text-white/30 focus:outline-none"
                  />
                </div>
                <p className="text-sm text-white/50">
                  Sign in with a phone number isn&apos;t available yet, use
                  email for now.
                </p>
              </div>
            )}
          </div>

          <TextInput
            label="Password"
            type="password"
            placeholder="************"
            {...register('password')}
            error={errors.password?.message}
          />

          <Link
            href="/forgot-password"
            className="text-right text-sm text-[var(--color-primary)]"
          >
            Forgot Password?
          </Link>

          {submitError && (
            <p className="text-sm text-red-400">{submitError}</p>
          )}

          <button
            type="submit"
            disabled={isSubmitting || method !== 'email'}
            className="mt-2 rounded-full bg-[var(--color-primary)] py-4 font-semibold uppercase text-[var(--color-dark)] disabled:opacity-60"
          >
            {isSubmitting ? 'Logging in...' : 'Login'}
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
