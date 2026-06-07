"use client";

import { useState, useMemo } from "react";
import type { TrustRow } from "@/lib/db";

interface TrustTableProps {
  data: TrustRow[];
  onTrustClick: (orgCode: string) => void;
}

type SortKey = keyof Pick<
  TrustRow,
  "rank_in_month" | "trust_name" | "pct_within_4hrs" | "total_attendances"
>;

const BAND_PILL: Record<string, string> = {
  "Target Met":    "bg-green-100 text-green-800",
  "Near Miss":     "bg-amber-100 text-amber-800",
  "Below Target":  "bg-red-100 text-red-800",
};

function fmtPct(v: number | null): string {
  return v === null ? "—" : `${v.toFixed(1)}%`;
}

function fmtNum(v: number): string {
  return v.toLocaleString("en-GB");
}

export default function TrustTable({ data, onTrustClick }: TrustTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>("rank_in_month");
  const [sortAsc, setSortAsc] = useState(true);

  function toggleSort(key: SortKey) {
    if (key === sortKey) {
      setSortAsc((a) => !a);
    } else {
      setSortKey(key);
      setSortAsc(key === "trust_name"); // alpha asc for name, numeric asc otherwise
    }
  }

  const sorted = useMemo(() => {
    return [...data].sort((a, b) => {
      const av = a[sortKey] ?? (sortAsc ? Infinity : -Infinity);
      const bv = b[sortKey] ?? (sortAsc ? Infinity : -Infinity);
      if (typeof av === "string" && typeof bv === "string") {
        return sortAsc ? av.localeCompare(bv) : bv.localeCompare(av);
      }
      return sortAsc ? (av as number) - (bv as number) : (bv as number) - (av as number);
    });
  }, [data, sortKey, sortAsc]);

  function SortHeader({
    label,
    col,
    className = "",
  }: {
    label: string;
    col: SortKey;
    className?: string;
  }) {
    const active = sortKey === col;
    return (
      <th
        scope="col"
        className={`cursor-pointer select-none whitespace-nowrap px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500 hover:text-gray-800 ${className}`}
        onClick={() => toggleSort(col)}
      >
        {label}
        <span className="ml-1 text-gray-300">
          {active ? (sortAsc ? "↑" : "↓") : "↕"}
        </span>
      </th>
    );
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white shadow-sm">
      <table className="min-w-full divide-y divide-gray-100">
        <thead className="bg-gray-50">
          <tr>
            <SortHeader label="Rank"        col="rank_in_month"     className="w-16" />
            <SortHeader label="Trust"       col="trust_name" />
            <SortHeader label="4hr Rate"    col="pct_within_4hrs"   className="text-right" />
            <SortHeader label="Attendances" col="total_attendances"  className="text-right" />
            <th scope="col" className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
              Band
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-50">
          {sorted.map((row) => (
            <tr
              key={row.org_code}
              className="cursor-pointer transition-colors hover:bg-blue-50"
              onClick={() => onTrustClick(row.org_code)}
            >
              <td className="px-4 py-3 text-sm tabular-nums text-gray-400">
                {row.rank_in_month ?? "—"}
              </td>
              <td className="px-4 py-3">
                <p className="text-sm font-medium text-gray-900">
                  {row.trust_name}
                </p>
                <p className="text-xs text-gray-400">{row.org_code}</p>
              </td>
              <td className="px-4 py-3 text-right text-sm tabular-nums font-medium text-gray-800">
                {fmtPct(row.pct_within_4hrs)}
              </td>
              <td className="px-4 py-3 text-right text-sm tabular-nums text-gray-600">
                {fmtNum(row.total_attendances)}
              </td>
              <td className="px-4 py-3">
                <span
                  className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
                    BAND_PILL[row.performance_band] ?? "bg-gray-100 text-gray-600"
                  }`}
                >
                  {row.performance_band}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="border-t border-gray-100 px-4 py-2 text-xs text-gray-400">
        {sorted.length} trusts
      </p>
    </div>
  );
}
