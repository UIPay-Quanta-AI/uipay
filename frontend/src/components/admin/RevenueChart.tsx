interface RevenuePoint {
  label: string;
  amount: number;
}

function formatK(value: number): string {
  if (value === 0) return '0';
  return `${Math.round(value / 1000)}k`;
}

// Simple dependency-free bar chart matching the admin dashboard mockup -
// no interactivity/tooltips are asked for, so a small library isn't worth
// the bundle weight.
export function RevenueChart({ data }: { data: RevenuePoint[] }) {
  const max = Math.max(0, ...data.map((d) => d.amount));
  // no data at all yet: fall back to a plain 10k scale rather than a
  // degenerate near-zero ceiling that makes every axis label read "0k"
  if (max < 1000) {
    const axisLabels = ['10k', '8k', '6k', '4k', '2k', '0'];
    return (
      <div className="flex gap-3">
        <div className="flex flex-col justify-between py-1 text-xs text-white/50">
          {axisLabels.map((label, i) => (
            <span key={i}>{label}</span>
          ))}
        </div>
        <div className="flex flex-1 flex-col">
          <div className="flex h-40 items-end gap-3 border-l border-white/20 pl-3" />
          <div className="flex gap-3 border-t border-white/20 pl-3 pt-2">
            {data.map((point, i) => (
              <span key={i} className="flex-1 text-center text-xs text-white/60">
                {point.label}
              </span>
            ))}
          </div>
        </div>
      </div>
    );
  }

  // round the axis ceiling up to a clean step so labels read like 10k/20k/...
  const step = Math.pow(10, Math.max(0, String(Math.ceil(max)).length - 2)) || 1;
  const ceiling = Math.ceil(max / step) * step || step;
  const axisSteps = 6;
  const axisLabels = Array.from({ length: axisSteps }, (_, i) =>
    formatK((ceiling * (axisSteps - i)) / axisSteps),
  );

  return (
    <div className="flex gap-3">
      <div className="flex flex-col justify-between py-1 text-xs text-white/50">
        {axisLabels.map((label, i) => (
          <span key={i}>{label}</span>
        ))}
      </div>
      <div className="flex flex-1 flex-col">
        <div className="flex h-40 items-end gap-3 border-l border-white/20 pl-3">
          {data.map((point, i) => (
            <div
              key={i}
              className="flex h-full flex-1 flex-col items-center justify-end gap-2"
            >
              <div
                className="w-full max-w-6 rounded-t bg-white/85"
                style={{
                  height: `${Math.max(2, (point.amount / ceiling) * 100)}%`,
                }}
                title={`${point.label}: ₦${point.amount.toLocaleString()}`}
              />
            </div>
          ))}
        </div>
        <div className="flex gap-3 border-t border-white/20 pl-3 pt-2">
          {data.map((point, i) => (
            <span
              key={i}
              className="flex-1 text-center text-xs text-white/60"
            >
              {point.label}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
