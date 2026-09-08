import { ChevronRight, LucideIcon } from 'lucide-react';
import Link from 'next/link';

interface SettingsRowProps {
  label: string;
  icon?: LucideIcon;
  href?: string;
  onClick?: () => void;
  disabled?: boolean;
  disabledNote?: string;
  destructive?: boolean;
}

export function SettingsRow({
  label,
  icon: Icon,
  href,
  onClick,
  disabled,
  disabledNote,
  destructive,
}: SettingsRowProps) {
  const content = (
    <>
      <span className="flex items-center gap-3">
        {Icon && (
          <Icon
            className={`h-5 w-5 ${destructive ? 'text-red-400' : 'text-[var(--color-primary)]'}`}
          />
        )}
        <span
          className={
            destructive ? 'text-red-400' : 'text-[var(--color-light)]'
          }
        >
          {label}
        </span>
      </span>
      {!disabled && (
        <ChevronRight className="h-5 w-5 text-white/30" />
      )}
    </>
  );

  const className =
    'flex w-full items-center justify-between border-b border-white/10 py-4 text-left transition-transform active:scale-[0.99] disabled:opacity-40';

  if (disabled) {
    return (
      <div title={disabledNote ?? 'Coming soon'} className={`${className} opacity-40`}>
        {content}
      </div>
    );
  }

  if (href) {
    return (
      <Link href={href} className={className}>
        {content}
      </Link>
    );
  }

  return (
    <button type="button" onClick={onClick} className={className}>
      {content}
    </button>
  );
}
