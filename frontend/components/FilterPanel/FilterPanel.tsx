"use client";

import type { MonthOption } from "@/lib/db";

const BANDS = ["All", "Target Met", "Near Miss", "Below Target"] as const;

interface FilterPanelProps {
  months: MonthOption[];
  selectedMonth: string;
  onMonthChange: (value: string) => void;
  selectedBand: string;
  onBandChange: (value: string) => void;
}

export default function FilterPanel({
  months,
  selectedMonth,
  onMonthChange,
  selectedBand,
  onBandChange,
}: FilterPanelProps) {
  return (
    <div className="flex flex-wrap items-center gap-4">
      <div className="flex items-center gap-2">
        <label
          htmlFor="month-select"
          className="text-sm font-medium text-gray-600"
        >
          Month
        </label>
        <select
          id="month-select"
          value={selectedMonth}
          onChange={(e) => onMonthChange(e.target.value)}
          className="rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-sm text-gray-800 shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {months.map((m) => (
            <option key={m.value} value={m.value}>
              {m.label}
            </option>
          ))}
        </select>
      </div>

      <div className="flex items-center gap-2">
        <label
          htmlFor="band-select"
          className="text-sm font-medium text-gray-600"
        >
          Band
        </label>
        <select
          id="band-select"
          value={selectedBand}
          onChange={(e) => onBandChange(e.target.value)}
          className="rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-sm text-gray-800 shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {BANDS.map((b) => (
            <option key={b} value={b}>
              {b}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
