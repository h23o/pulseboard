interface KPICardProps {
  title: string;
  value: string;
  subtitle?: string;
  trend?: "up" | "down" | "neutral";
  highlight?: "green" | "amber" | "red";
}

const HIGHLIGHT_DOT: Record<string, string> = {
  green: "bg-green-500",
  amber: "bg-amber-400",
  red: "bg-red-500",
};

const TREND_ICON: Record<string, string> = {
  up: "↑",
  down: "↓",
  neutral: "→",
};

const TREND_COLOUR: Record<string, string> = {
  up: "text-green-600",
  down: "text-red-600",
  neutral: "text-gray-400",
};

export default function KPICard({
  title,
  value,
  subtitle,
  trend,
  highlight,
}: KPICardProps) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white px-6 py-5 shadow-sm">
      <div className="flex items-start justify-between">
        <p className="text-sm font-medium text-gray-500">{title}</p>
        {highlight && (
          <span
            className={`mt-0.5 h-2.5 w-2.5 rounded-full ${HIGHLIGHT_DOT[highlight]}`}
          />
        )}
      </div>

      <p className="mt-2 text-3xl font-bold tracking-tight text-gray-900">
        {value}
      </p>

      {(subtitle || trend) && (
        <p className="mt-1 flex items-center gap-1 text-sm text-gray-500">
          {trend && (
            <span className={`font-semibold ${TREND_COLOUR[trend]}`}>
              {TREND_ICON[trend]}
            </span>
          )}
          {subtitle}
        </p>
      )}
    </div>
  );
}
