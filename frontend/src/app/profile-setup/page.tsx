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
import { useSignupStore } from '@/store/signup';

const schema = z
  .object({
    firstName: z.string().min(1, 'First name is required'),
    lastName: z.string().min(1, 'Last name is required'),
    // 0?[1-9] accepts both "7" and "07" for the same day/month - previously
    // only one form matched depending on the value (a bare [1-9] alternative
    // requires exactly one character, so "07" failed it even though "7"
    // passed, while two-digit values like "15" only ever worked unpadded)
    dobDay: z.string().regex(/^(0?[1-9]|[12]\d|3[01])$/, 'Invalid day'),
    dobMonth: z.string().regex(/^(0?[1-9]|1[0-2])$/, 'Invalid month'),
    dobYear: z.string().regex(/^(19|20)\d{2}$/, 'Invalid year'),
    email: z.string().email('Enter a valid email'),
    phoneNumber: z
      .string()
      .regex(/^[789][01]\d{8}$/, 'Enter a valid 10 digit Nigerian number'),
    password: z.string().min(8, 'Password must be at least 8 characters'),
    confirmPassword: z.string(),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Passwords don't match",
    path: ['confirmPassword'],
  });

type FormValues = z.infer<typeof schema>;

export default function CreateAccountPage() {
  const router = useRouter();
  const setPending = useSignupStore((state) => state.setPending);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const onSubmit = async (values: FormValues) => {
    setSubmitError(null);

    const payload = {
      emailAddress: values.email,
      password: values.password,
      firstName: values.firstName,
      lastName: values.lastName,
      dob: `${values.dobYear}-${values.dobMonth.padStart(2, '0')}-${values.dobDay.padStart(2, '0')}`,
      phoneNumber: `+234${values.phoneNumber}`,
    };

    try {
      await api.post('/auth/register', payload);
      setPending(payload);
      router.push('/profile-setup/verify-otp');
    } catch (error) {
      setSubmitError(getApiErrorMessage(error));
    }
  };

  return (
    <GlowBackground className="flex justify-center px-8 py-12">
      <div className="flex w-full max-w-sm flex-col gap-6">
        <div className="flex flex-col items-center gap-1 text-center">
          <span className="text-sm font-semibold tracking-widest text-[var(--color-primary)]">
            CREATE AN ACCOUNT
          </span>
          <h1 className="text-3xl font-extrabold text-[var(--color-light)]">
            Let&apos;s Create Your Account
          </h1>
        </div>

        <form
          onSubmit={handleSubmit(onSubmit)}
          className="flex flex-col gap-4"
        >
          <TextInput
            label="First name"
            {...register('firstName')}
            error={errors.firstName?.message}
          />
          <TextInput
            label="Last name"
            {...register('lastName')}
            error={errors.lastName?.message}
          />

          <div className="flex flex-col gap-2">
            <label className="text-sm text-[var(--color-light)]">
              Date of Birth
            </label>
            <div className="flex gap-3">
              <input
                {...register('dobDay')}
                placeholder="DD"
                inputMode="numeric"
                className="w-full rounded-xl border border-white/20 bg-transparent px-4 py-3 text-center text-[var(--color-light)] placeholder:text-white/30 focus:border-[var(--color-primary)] focus:outline-none"
              />
              <input
                {...register('dobMonth')}
                placeholder="MM"
                inputMode="numeric"
                className="w-full rounded-xl border border-white/20 bg-transparent px-4 py-3 text-center text-[var(--color-light)] placeholder:text-white/30 focus:border-[var(--color-primary)] focus:outline-none"
              />
              <input
                {...register('dobYear')}
                placeholder="YYYY"
                inputMode="numeric"
                className="w-full rounded-xl border border-white/20 bg-transparent px-4 py-3 text-center text-[var(--color-light)] placeholder:text-white/30 focus:border-[var(--color-primary)] focus:outline-none"
              />
            </div>
            {(errors.dobDay || errors.dobMonth || errors.dobYear) && (
              <p className="text-sm text-red-400">
                Enter a valid date of birth
              </p>
            )}
          </div>

          <TextInput
            label="Email"
            type="email"
            placeholder="example@gmail.com"
            {...register('email')}
            error={errors.email?.message}
          />

          <div className="flex flex-col gap-2">
            <label className="text-sm text-[var(--color-light)]">
              Phone number
            </label>
            <div className="flex items-center gap-3 rounded-xl border border-white/20 px-4 py-3 focus-within:border-[var(--color-primary)]">
              <span className="text-[var(--color-light)]">+234</span>
              <span className="h-5 w-px bg-white/20" />
              <input
                {...register('phoneNumber')}
                placeholder="0000000000"
                inputMode="numeric"
                className="w-full bg-transparent text-[var(--color-light)] placeholder:text-white/30 focus:outline-none"
              />
            </div>
            {errors.phoneNumber && (
              <p className="text-sm text-red-400">
                {errors.phoneNumber.message}
              </p>
            )}
          </div>

          <TextInput
            label="Password"
            type="password"
            placeholder="************"
            {...register('password')}
            error={errors.password?.message}
          />
          <TextInput
            label="Confirm Password"
            type="password"
            placeholder="************"
            {...register('confirmPassword')}
            error={errors.confirmPassword?.message}
          />

          {submitError && (
            <p className="text-sm text-red-400">{submitError}</p>
          )}

          <button
            type="submit"
            disabled={isSubmitting}
            className="mt-2 rounded-full bg-[var(--color-primary)] py-4 font-semibold uppercase text-[var(--color-dark)] disabled:opacity-60"
          >
            {isSubmitting ? 'Signing up...' : 'Sign Up'}
          </button>

          <p className="text-center text-sm text-[var(--color-light)]">
            Already have an account?{' '}
            <Link
              href="/signin"
              className="text-[var(--color-primary)] underline"
            >
              Sign in
            </Link>
          </p>
        </form>
      </div>
    </GlowBackground>
  );
}
