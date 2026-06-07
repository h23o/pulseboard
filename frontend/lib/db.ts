/**
 * lib/db.ts – Typed PostgreSQL client for PulseBoard.
 *
 * Uses the 'postgres' npm package which auto-parameterises every
 * tagged-template value, preventing SQL injection.
 *
 * The singleton pattern prevents connection-pool exhaustion during
 * Next.js hot reloads in development.
 */

import postgres from "postgres";

// ── Singleton connection ────────────────────────────────────────────────────

const globalForSql = globalThis as unknown as {
  sql?: ReturnType<typeof postgres>;
};

export const sql =
  globalForSql.sql ??
  postgres(process.env.POSTGRES_URL!, {
    max: 10,
    idle_timeout: 20,
    connect_timeout: 10,
  });

if (process.env.NODE_ENV !== "production") {
  globalForSql.sql = sql;
}

// ── Types ───────────────────────────────────────────────────────────────────

export interface NationalSummary {
  latest_month: string;
  national_4hr_pct: number;
  total_attendances: number;
  trusts_at_target: number;
  trusts_below_target: number;
  total_trusts: number;
}

export interface TrendPoint {
  month_date: string;
  avg_4hr_pct: number;
  total_attendances: number;
}

export interface TrustRow {
  org_code: string;
  trust_name: string;
  pct_within_4hrs: number | null;
  total_attendances: number;
  performance_band: string;
  rank_in_month: number;
}

export interface TrustTrendPoint {
  month_date: string;
  pct_within_4hrs: number | null;
  total_attendances: number;
  national_avg_4hr_pct: number | null;
  trust_name: string;
  rank_in_month: number | null;
}

export interface MonthOption {
  value: string; // 'YYYY-MM-DD'
  label: string; // 'September 2025'
}

// ── Query functions ─────────────────────────────────────────────────────────

/**
 * KPI summary for the latest available month.
 */
export async function getNationalSummary(): Promise<NationalSummary> {
  const rows = await sql`
    SELECT
      (SELECT TO_CHAR(MAX(month_date), 'YYYY-MM-DD') FROM marts.fct_ae_performance) AS latest_month,
      ROUND(AVG(pct_within_4hrs)::numeric, 1)                         AS national_4hr_pct,
      SUM(total_attendances)                                           AS total_attendances,
      COUNT(*) FILTER (WHERE performance_band = 'Target Met')         AS trusts_at_target,
      COUNT(*) FILTER (WHERE performance_band = 'Below Target')       AS trusts_below_target,
      COUNT(*)                                                         AS total_trusts
    FROM marts.fct_ae_performance
    WHERE month_date = (SELECT MAX(month_date) FROM marts.fct_ae_performance)
  `;
  const r = rows[0];
  return {
    latest_month: r.latest_month as string,
    national_4hr_pct: Number(r.national_4hr_pct),
    total_attendances: Number(r.total_attendances),
    trusts_at_target: Number(r.trusts_at_target),
    trusts_below_target: Number(r.trusts_below_target),
    total_trusts: Number(r.total_trusts),
  };
}

/**
 * Month-by-month national average 4-hour rate, last N months.
 */
export async function getNationalTrend(months = 36): Promise<TrendPoint[]> {
  const rows = await sql`
    SELECT
      TO_CHAR(month_date, 'YYYY-MM-DD')           AS month_date,
      ROUND(AVG(pct_within_4hrs)::numeric, 1)     AS avg_4hr_pct,
      SUM(total_attendances)                       AS total_attendances
    FROM marts.fct_ae_performance
    WHERE month_date >= (
      SELECT MAX(month_date) - ${months} * INTERVAL '1 month'
      FROM marts.fct_ae_performance
    )
    GROUP BY month_date
    ORDER BY month_date
  `;
  return rows.map((r) => ({
    month_date: r.month_date as string,
    avg_4hr_pct: Number(r.avg_4hr_pct),
    total_attendances: Number(r.total_attendances),
  }));
}

/**
 * All trusts for a given month (defaults to latest).
 * Band filter is applied by the caller client-side to avoid a round-trip.
 */
export async function getTrustTable(
  filters: { month?: string } = {}
): Promise<TrustRow[]> {
  const rows = filters.month
    ? await sql`
        SELECT
          org_code, trust_name, pct_within_4hrs,
          total_attendances, performance_band, rank_in_month
        FROM marts.fct_ae_performance
        WHERE month_date = ${filters.month}::date
        ORDER BY rank_in_month NULLS LAST, org_code
      `
    : await sql`
        SELECT
          org_code, trust_name, pct_within_4hrs,
          total_attendances, performance_band, rank_in_month
        FROM marts.fct_ae_performance
        WHERE month_date = (SELECT MAX(month_date) FROM marts.fct_ae_performance)
        ORDER BY rank_in_month NULLS LAST, org_code
      `;

  return rows.map((r) => ({
    org_code: r.org_code as string,
    trust_name: r.trust_name as string,
    pct_within_4hrs:
      r.pct_within_4hrs === null ? null : Number(r.pct_within_4hrs),
    total_attendances: Number(r.total_attendances),
    performance_band: r.performance_band as string,
    rank_in_month: Number(r.rank_in_month),
  }));
}

/**
 * Month-by-month trend for a single trust vs national average.
 */
export async function getTrustTrend(
  orgCode: string,
  months = 36
): Promise<TrustTrendPoint[]> {
  const rows = await sql`
    SELECT
      TO_CHAR(month_date, 'YYYY-MM-DD')   AS month_date,
      pct_within_4hrs,
      total_attendances,
      national_avg_4hr_pct,
      trust_name,
      rank_in_month
    FROM marts.fct_ae_performance
    WHERE org_code = ${orgCode}
      AND month_date >= (
        SELECT MAX(month_date) - ${months} * INTERVAL '1 month'
        FROM marts.fct_ae_performance
      )
    ORDER BY month_date
  `;
  return rows.map((r) => ({
    month_date: r.month_date as string,
    pct_within_4hrs:
      r.pct_within_4hrs === null ? null : Number(r.pct_within_4hrs),
    total_attendances: Number(r.total_attendances),
    national_avg_4hr_pct:
      r.national_avg_4hr_pct === null ? null : Number(r.national_avg_4hr_pct),
    trust_name: r.trust_name as string,
    rank_in_month: r.rank_in_month === null ? null : Number(r.rank_in_month),
  }));
}

/**
 * Sorted list of all months present in the mart for the month selector.
 */
export async function getAvailableMonths(): Promise<MonthOption[]> {
  const rows = await sql`
    SELECT DISTINCT
      TO_CHAR(month_date, 'YYYY-MM-DD')                                   AS value,
      TRIM(TO_CHAR(month_date, 'Month')) || ' ' || TO_CHAR(month_date, 'YYYY') AS label
    FROM marts.fct_ae_performance
    ORDER BY value DESC
  `;
  return rows.map((r) => ({
    value: r.value as string,
    label: r.label as string,
  }));
}

/**
 * Latest _ingested_at timestamp across the entire raw table.
 */
export async function getLastUpdated(): Promise<string> {
  const rows = await sql`
    SELECT TO_CHAR(MAX(_ingested_at) AT TIME ZONE 'UTC', 'DD Mon YYYY HH24:MI UTC')
      AS last_updated
    FROM raw.ae_attendances
  `;
  return (rows[0].last_updated as string) ?? "Unknown";
}
