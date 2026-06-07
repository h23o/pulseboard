"use client";

import { useState, useMemo, useTransition } from "react";
import { useRouter } from "next/navigation";
import FilterPanel from "@/components/FilterPanel/FilterPanel";
import TrustTable from "@/components/TrustTable/TrustTable";
import type { TrustRow, MonthOption } from "@/lib/db";

interface DashboardClientProps {
  initialData: TrustRow[];
  months: MonthOption[];
  initialMonth: string;
}

export default function DashboardClient({
  initialData,
  months,
  initialMonth,
}: DashboardClientProps) {
  const router = useRouter();
  const [, startTransition] = useTransition();
  const [selectedMonth, setSelectedMonth] = useState(initialMonth);
  const [selectedBand, setSelectedBand] = useState("All");

  function handleMonthChange(month: string) {
    setSelectedMonth(month);
    // Push to URL so the server component re-fetches data for the new month
    startTransition(() => {
      router.push(`/?month=${month}`, { scroll: false });
    });
  }

  const filtered = useMemo(() => {
    if (selectedBand === "All") return initialData;
    return initialData.filter((r) => r.performance_band === selectedBand);
  }, [initialData, selectedBand]);

  function handleTrustClick(orgCode: string) {
    router.push(`/trust/${encodeURIComponent(orgCode)}`);
  }

  return (
    <div className="space-y-4">
      <FilterPanel
        months={months}
        selectedMonth={selectedMonth}
        onMonthChange={handleMonthChange}
        selectedBand={selectedBand}
        onBandChange={setSelectedBand}
      />
      <TrustTable data={filtered} onTrustClick={handleTrustClick} />
    </div>
  );
}
