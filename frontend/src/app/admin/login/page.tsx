'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import { AlertCircle } from 'lucide-react';
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

export default function AdminLoginPage() {
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

      // /auth/signin succeeds for ANY valid account, not just admins - the
      // admin layout does the real role check right after this redirect and
      // bounces back here if this turns out not to be an admin account.
      router.push('/admin');
    } catch (error) {
      setSubmitError(getApiErrorMessage(error));
    }
  };

  return (
    <GlowBackground className="flex justify-center px-8 py-12">
      <div className="flex w-full max-w-sm flex-col gap-6 pt-16">
        <div className="flex flex-col items-center gap-1 text-center">
          <h1 className="text-4xl font-extrabold text-[var(--color-light)]">
            Admin
          </h1>
          <p className="text-xl font-semibold text-[var(--color-light)]">
            Sign In
          </p>
        </div>

        <div className="h-24" />

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

          {submitError && (
            <div className="flex items-center justify-between rounded-xl border border-red-500 px-4 py-3">
              <span className="text-sm uppercase tracking-wide text-red-400">
                {submitError}
              </span>
              <AlertCircle className="h-5 w-5 shrink-0 rounded-full bg-red-500 p-0.5 text-[var(--color-dark)]" />
            </div>
          )}

          <Link
            href="/forgot-password"
            className="text-right text-sm text-[var(--color-primary)]"
          >
            Forgot Password?
          </Link>

          <button
            type="submit"
            disabled={isSubmitting || method !== 'email'}
            className="mt-2 rounded-full bg-[var(--color-primary)] py-4 font-semibold uppercase text-[var(--color-dark)] disabled:opacity-60"
          >
            {isSubmitting ? 'Logging in...' : 'Login'}
          </button>

          <p className="text-center text-sm text-[var(--color-light)]">
            Don&apos;t have an account?{' '}
            <span
              className="text-[var(--color-primary)] underline decoration-[var(--color-primary)]"
              title="Admin accounts are created directly by another admin, not through self-signup"
            >
              Sign up
            </span>
          </p>
        </form>
      </div>
    </GlowBackground>
  );
}
