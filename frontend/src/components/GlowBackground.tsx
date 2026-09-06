export function GlowBackground({
  children,
  className = '',
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <main
      className={`relative min-h-screen w-screen overflow-hidden bg-[var(--color-dark)] ${className}`}
    >
      <div className="pointer-events-none absolute -left-32 -top-32 h-96 w-96 rounded-full bg-[var(--color-primary)] opacity-30 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-32 -right-32 h-96 w-96 rounded-full bg-[var(--color-primary)] opacity-30 blur-3xl" />
      {/* flex-1 flex-col so a direct child using mt-auto (a bottom-pinned
          button, say) actually reaches the bottom of the viewport - without
          this the wrapper only sizes to its content, same as
          AuthScreenLayout's own inner wrapper already does for the same
          reason */}
      <div className="relative flex flex-1 flex-col">{children}</div>
    </main>
  );
}
