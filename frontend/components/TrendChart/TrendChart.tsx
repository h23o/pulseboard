"use client";

import {
  ComposedChart,
  Line,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  Legend,
  ResponsiveContainer,
} from "recharts";

interface TrendDataPoint {
  month_date: string;
  avg_4hr_pct: number | null;
  total_attendances: number;
  trust_4hr_pct?: number | null;   // optional second line (trust page)
}

interface TrendChartProps {
  data: TrendDataPoint[];
  height?: number;
  showTrustLine?: boolean;        // render the trust vs national comparison
  trustName?: string;
}

/** Format 'YYYY-MM-DD' → 'Sep 25' */
function fmtMonth(iso: string): string {
  const d = new Date(iso + "T00:00:00Z");
  return d.toLocaleDateString("en-GB", {
    month: "short",
    year: "2-digit",
    timeZone: "UTC",
  });
}

function fmtNumber(n: number): string {
  return n.toLocaleString("en-GB");
}

// Custom tooltip
const CustomTooltip = ({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ name: string; value: number; color: string }>;
  label?: string;
}) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-3 shadow-lg text-sm">
      <p className="mb-1.5 font-semibold text-gray-700">{fmtMonth(label ?? "")}</p>
      {payload.map((entry) => (
        <p key={entry.name} style={{ color: entry.color }} className="leading-5">
          {entry.name}:{" "}
          <span className="font-medium">
            {entry.name.includes("Attendances")
              ? fmtNumber(entry.value)
              : `${entry.value?.toFixed(1)}%`}
          </span>
        </p>
      ))}
    </div>
  );
};

export default function TrendChart({
  data,
  height = 320,
  showTrustLine = false,
  trustName = "This Trust",
}: TrendChartProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <ComposedChart
        data={data}
        margin={{ top: 8, right: 24, left: 0, bottom: 0 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />

        <XAxis
          dataKey="month_date"
          tickFormatter={fmtMonth}
          tick={{ fontSize: 11, fill: "#6b7280" }}
          tickLine={false}
          axisLine={false}
          interval="preserveStartEnd"
        />

        {/* Left Y axis — percentage */}
        <YAxis
          yAxisId="pct"
          domain={[0, 100]}
          tickFormatter={(v) => `${v}%`}
          tick={{ fontSize: 11, fill: "#6b7280" }}
          tickLine={false}
          axisLine={false}
          width={44}
        />

        {/* Right Y axis — attendances */}
        <YAxis
          yAxisId="att"
          orientation="right"
          tickFormatter={(v) =>
            v >= 1_000_000
              ? `${(v / 1_000_000).toFixed(1)}M`
              : v >= 1_000
              ? `${(v / 1_000).toFixed(0)}k`
              : String(v)
          }
          tick={{ fontSize: 11, fill: "#9ca3af" }}
          tickLine={false}
          axisLine={false}
          width={44}
        />

        <Tooltip content={<CustomTooltip />} />
        <Legend
          wrapperStyle={{ fontSize: 12, paddingTop: 8 }}
          iconType="plainline"
        />

        {/* NHS 95% target reference line */}
        <ReferenceLine
          yAxisId="pct"
          y={95}
          stroke="#dc2626"
          strokeDasharray="6 3"
          strokeWidth={1.5}
          label={{
            value: "NHS Target 95%",
            position: "insideTopRight",
            fontSize: 11,
            fill: "#dc2626",
          }}
        />

        {/* Attendances bar (background, muted) */}
        <Bar
          yAxisId="att"
          dataKey="total_attendances"
          name="Total Attendances"
          fill="#e5e7eb"
          radius={[2, 2, 0, 0]}
          maxBarSize={20}
        />

        {/* National average line */}
        <Line
          yAxisId="pct"
          type="monotone"
          dataKey="avg_4hr_pct"
          name={showTrustLine ? "National Average" : "Avg 4hr Rate"}
          stroke="#2563eb"
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4 }}
        />

        {/* Trust-specific line (trust page only) */}
        {showTrustLine && (
          <Line
            yAxisId="pct"
            type="monotone"
            dataKey="trust_4hr_pct"
            name={trustName}
            stroke="#f59e0b"
            strokeWidth={2.5}
            dot={false}
            activeDot={{ r: 4 }}
          />
        )}
      </ComposedChart>
    </ResponsiveContainer>
  );
}
