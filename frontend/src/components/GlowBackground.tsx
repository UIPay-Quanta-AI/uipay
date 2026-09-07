export function GlowBackground({
  children,
  className = '',
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <main className="relative flex min-h-screen w-screen flex-col overflow-hidden bg-[var(--color-dark)]">
      <div className="pointer-events-none absolute -left-32 -top-32 h-96 w-96 rounded-full bg-[var(--color-primary)] opacity-30 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-32 -right-32 h-96 w-96 rounded-full bg-[var(--color-primary)] opacity-30 blur-3xl" />
      {/* the caller's className (flex direction, alignment, padding) has to
          land on THIS element, not <main> - it's the actual flex container
          around {children}. flex-1 makes it fill <main>'s full height (so a
          child using mt-auto reaches the real bottom of the viewport);
          <main> itself stays a fixed flex-col base so flex-1 has something
          to grow against, independent of whatever direction/alignment the
          caller asks for here. */}
      <div className={`relative flex-1 ${className}`}>{children}</div>
    </main>
  );
}
