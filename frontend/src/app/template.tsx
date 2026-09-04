'use client';

// re-mounts on every navigation (layout.tsx doesn't), so this gives
// every page a consistent fade-in instead of an instant cut
export default function RootTemplate({
  children,
}: {
  children: React.ReactNode;
}) {
  return <div className="animate-page-in">{children}</div>;
}
