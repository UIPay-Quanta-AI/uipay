import Image from 'next/image';

export function LogoIcon({ className }: { className?: string }) {
  return (
    <Image
      src="/logo-icon.png"
      alt="uipay"
      width={69}
      height={72}
      priority
      className={className}
    />
  );
}

export function LogoWordmark({ className }: { className?: string }) {
  return (
    <Image
      src="/logo-wordmark.png"
      alt="UIPay"
      width={361}
      height={128}
      priority
      className={className}
    />
  );
}
