import type { Metadata } from 'next';
import { Nunito_Sans } from 'next/font/google';
import './globals.css';

const nunitoSans = Nunito_Sans({
  subsets: ['latin'],
  variable: '--font-nunito-sans',
  // Next.js can't find precomputed fallback-font metrics for this font in
  // its own database, so it logs "Failed to find font override values" on
  // every build. Harmless (confirmed non-blocking on a real build) but
  // noisy - this just turns off the metric lookup that's failing.
  adjustFontFallback: false,
});

export const metadata: Metadata = {
  title: 'uipay',
  description: 'uipay',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={nunitoSans.variable}>
      <body>{children}</body>
    </html>
  );
}
