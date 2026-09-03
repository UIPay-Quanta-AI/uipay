// placeholder landing spot for the "Forgot Password?" link - the backend
// already has POST /auth/forgot-password and /auth/reset-password, this
// screen just isn't built yet
export default function ForgotPasswordPage() {
  return (
    <main className="flex h-screen w-screen items-center justify-center bg-[var(--color-dark)]">
      <p className="text-[var(--color-light)]">
        Password reset coming soon
      </p>
    </main>
  );
}
