export function AdminBackground({
  children,
  className = '',
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <main className="min-h-screen w-screen bg-[var(--color-dark)]">
      <div
        className="pointer-events-none absolute left-0 right-0 top-0 h-72 bg-gradient-to-b from-[rgba(var(--color-primary-rgb),0.4)] to-transparent"
        aria-hidden
      />
      <div className={`relative flex flex-col ${className}`}>{children}</div>
    </main>
  );
}
