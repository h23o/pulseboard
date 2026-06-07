import Link from "next/link";
import { notFound } from "next/navigation";
import { getTrustTrend } from "@/lib/db";
import KPICard from "@/components/KPICard/KPICard";
import TrendChart from "@/components/TrendChart/TrendChart";

function fmtShortMonth(iso: string): string {
  const d = new Date(iso + "T00:00:00Z");
  return d.toLocaleDateString("en-GB", {
    month: "short",
    year: "2-digit",
    timeZone: "UTC",
  });
}

function fmtLongMonth(iso: string): string {
  const d = new Date(iso + "T00:00:00Z");
  return d.toLocaleDateString("en-GB", {
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  });
}

function highlight(pct: number | null): "green" | "amber" | "red" {
  if (pct === null) return "red";
  if (pct >= 95) return "green";
  if (pct >= 85) return "amber";
  return "red";
}

export default async function TrustPage({
  params,
}: {
  params: { code: string };
}) {
  const orgCode = decodeURIComponent(params.code).toUpperCase();
  const trend = await getTrustTrend(orgCode, 36);

  if (trend.length === 0) notFound();

  const latest = trend[trend.length - 1];
  const trustName = latest.trust_name ?? orgCode;

  // Shape data for the chart: both trust line and national avg line
  const chartData = trend.map((t) => ({
    month_date: t.month_date,
    avg_4hr_pct: t.national_avg_4hr_pct,        // national line
    total_attendances: t.total_attendances,
    trust_4hr_pct: t.pct_within_4hrs,           // trust line
  }));

  // Last 12 months for the table
  const last12 = trend.slice(-12).reverse();

  return (
    <div className="space-y-8">
      {/* ── Back + heading ───────────────────────────────────────────── */}
      <div>
        <Link
          href="/"
          className="inline-flex items-center gap-1 text-sm text-blue-600 hover:underline"
        >
          ← All Trusts
        </Link>
        <h1 className="mt-2 text-2xl font-bold tracking-tight text-gray-900">
          {trustName}
        </h1>
        <p className="text-xs font-mono text-gray-400">{orgCode}</p>
        <p className="text-sm text-gray-500">
          Latest data: {fmtLongMonth(latest.month_date)}
        </p>
      </div>

      {/* ── KPI cards ────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <KPICard
          title="4hr Rate (Latest Month)"
          value={
            latest.pct_within_4hrs === null
              ? "—"
              : `${latest.pct_within_4hrs.toFixed(1)}%`
          }
          subtitle={fmtLongMonth(latest.month_date)}
          highlight={highlight(latest.pct_within_4hrs)}
        />
        <KPICard
          title="Total Attendances"
          value={latest.total_attendances.toLocaleString("en-GB")}
          subtitle={fmtLongMonth(latest.month_date)}
        />
        <KPICard
          title="National Average"
          value={
            latest.national_avg_4hr_pct === null
              ? "—"
              : `${latest.national_avg_4hr_pct.toFixed(1)}%`
          }
          subtitle={fmtLongMonth(latest.month_date)}
        />
      </div>

      {/* ── Trend chart ──────────────────────────────────────────────── */}
      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <h2 className="mb-1 text-base font-semibold text-gray-800">
          4-Hour Performance vs National Average — 36 Months
        </h2>
        <p className="mb-4 text-xs text-gray-400">
          Amber line = this trust. Blue line = national average. Dashed red =
          95% NHS target.
        </p>
        <TrendChart
          data={chartData}
          height={320}
          showTrustLine
          trustName={orgCode}
        />
      </div>

      {/* ── Last 12 months table ─────────────────────────────────────── */}
      <div className="rounded-xl border border-gray-200 bg-white shadow-sm">
        <div className="px-6 py-4">
          <h2 className="text-base font-semibold text-gray-800">
            Last 12 Months
          </h2>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-100">
            <thead className="bg-gray-50">
              <tr>
                {["Month", "4hr Rate", "Attendances", "National Avg"].map(
                  (h) => (
                    <th
                      key={h}
                      scope="col"
                      className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500"
                    >
                      {h}
                    </th>
                  )
                )}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {last12.map((row) => (
                <tr key={row.month_date} className="hover:bg-gray-50">
                  <td className="px-6 py-3 text-sm text-gray-700">
                    {fmtLongMonth(row.month_date)}
                  </td>
                  <td className="px-6 py-3 text-sm tabular-nums font-medium text-gray-900">
                    {row.pct_within_4hrs === null
                      ? "—"
                      : `${row.pct_within_4hrs.toFixed(1)}%`}
                  </td>
                  <td className="px-6 py-3 text-sm tabular-nums text-gray-600">
                    {row.total_attendances.toLocaleString("en-GB")}
                  </td>
                  <td className="px-6 py-3 text-sm tabular-nums text-gray-400">
                    {row.national_avg_4hr_pct === null
                      ? "—"
                      : `${row.national_avg_4hr_pct.toFixed(1)}%`}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
