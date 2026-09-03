import { BackButton } from './BackButton';
import { GlowBackground } from './GlowBackground';

export function AuthScreenLayout({
  children,
  topLabel,
  onBack,
}: {
  children: React.ReactNode;
  topLabel?: string;
  onBack?: () => void;
}) {
  return (
    <GlowBackground className="flex flex-col px-8 py-10">
      <div className="flex items-center justify-between">
        <BackButton onClick={onBack} />
        {topLabel && (
          <span className="text-sm font-semibold tracking-widest text-[var(--color-primary)]">
            {topLabel}
          </span>
        )}
        <span className="h-6 w-6" />
      </div>

      <div className="flex flex-1 flex-col pt-10">{children}</div>
    </GlowBackground>
  );
}
