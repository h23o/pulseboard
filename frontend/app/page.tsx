import {
  getNationalSummary,
  getNationalTrend,
  getTrustTable,
  getAvailableMonths,
  getLastUpdated,
} from "@/lib/db";
import KPICard from "@/components/KPICard/KPICard";
import TrendChart from "@/components/TrendChart/TrendChart";
import DashboardClient from "./DashboardClient";

const NHS_STATS_URL =
  "https://www.england.nhs.uk/statistics/statistical-work-areas/ae-waiting-times-and-activity/";

function highlight(pct: number): "green" | "amber" | "red" {
  if (pct >= 95) return "green";
  if (pct >= 85) return "amber";
  return "red";
}

function fmtMonth(iso: string): string {
  const d = new Date(iso + "T00:00:00Z");
  return d.toLocaleDateString("en-GB", {
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  });
}

function fmtShortMonth(iso: string): string {
  const d = new Date(iso + "T00:00:00Z");
  return d.toLocaleDateString("en-GB", {
    month: "short",
    year: "2-digit",
    timeZone: "UTC",
  });
}

export default async function HomePage({
  searchParams,
}: {
  searchParams: { month?: string };
}) {
  const [summary, trend, months, lastUpdated] = await Promise.all([
    getNationalSummary(),
    getNationalTrend(36),
    getAvailableMonths(),
    getLastUpdated(),
  ]);

  const selectedMonth =
    searchParams.month && months.some((m) => m.value === searchParams.month)
      ? searchParams.month
      : months[0]?.value ?? summary.latest_month;

  const trustData = await getTrustTable({ month: selectedMonth });

  const earliestMonth = trend[0]?.month_date ?? selectedMonth;

  // Shape trend data for TrendChart (uses avg_4hr_pct key)
  const chartData = trend.map((t) => ({
    month_date: t.month_date,
    avg_4hr_pct: t.avg_4hr_pct,
    total_attendances: t.total_attendances,
  }));

  return (
    <div className="space-y-8">
      {/* ── Header ───────────────────────────────────────────────────── */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-gray-900">
          PulseBoard
        </h1>
        <p className="mt-1 text-base text-gray-500">
          NHS A&amp;E Performance Dashboard
        </p>
        <p className="mt-0.5 text-sm text-gray-400">
          Source:{" "}
          <a
            href={NHS_STATS_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="underline decoration-dotted hover:text-blue-600"
          >
            NHS England A&amp;E Attendance Statistics
          </a>
        </p>
      </div>

      {/* ── KPI cards ────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <KPICard
          title="National 4hr Rate"
          value={`${summary.national_4hr_pct.toFixed(1)}%`}
          subtitle={fmtMonth(summary.latest_month)}
          highlight={highlight(summary.national_4hr_pct)}
        />
        <KPICard
          title="Total Attendances"
          value={summary.total_attendances.toLocaleString("en-GB")}
          subtitle={fmtMonth(summary.latest_month)}
        />
        <KPICard
          title="Trusts At Target"
          value={`${summary.trusts_at_target} / ${summary.total_trusts}`}
          subtitle="≥ 95% 4-hour rate"
          highlight={
            summary.trusts_at_target / summary.total_trusts > 0.5
              ? "green"
              : "amber"
          }
        />
        <KPICard
          title="Data Coverage"
          value={`${fmtShortMonth(earliestMonth)} – ${fmtShortMonth(summary.latest_month)}`}
          subtitle={`${months.length} months`}
        />
      </div>

      {/* ── National trend chart ─────────────────────────────────────── */}
      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <h2 className="mb-1 text-base font-semibold text-gray-800">
          National 4-Hour Performance — 36 Months
        </h2>
        <p className="mb-4 text-xs text-gray-400">
          Average across all reporting trusts. The 95% NHS target is shown as a
          dashed red line.
        </p>
        <TrendChart data={chartData} height={320} />
      </div>

      {/* ── Filter + Trust table ─────────────────────────────────────── */}
      <div className="space-y-3">
        <h2 className="text-base font-semibold text-gray-800">
          Trust Performance —{" "}
          {months.find((m) => m.value === selectedMonth)?.label ?? selectedMonth}
        </h2>
        <DashboardClient
          initialData={trustData}
          months={months}
          initialMonth={selectedMonth}
        />
      </div>

      {/* ── Footer ───────────────────────────────────────────────────── */}
      <footer className="border-t border-gray-100 pt-4 text-xs text-gray-400">
        Last ingested: {lastUpdated} ·{" "}
        <a
          href={NHS_STATS_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="underline decoration-dotted"
        >
          NHS England
        </a>
      </footer>
    </div>
  );
}
