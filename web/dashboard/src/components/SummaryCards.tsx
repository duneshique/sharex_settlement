"use client";

import { formatCurrency } from "@/lib/format";

interface SummaryCardsProps {
  totalRevenue: number;
  totalAdCost: number;
  totalContribution: number;
  totalSettlement: number;
  companyCount: number;
  courseCount: number;
}

export default function SummaryCards({
  totalRevenue,
  totalAdCost,
  totalContribution,
  totalSettlement,
  companyCount,
  courseCount,
}: SummaryCardsProps) {
  return (
    <div className="grid grid-cols-5 gap-4 mb-8">
      <Card label="총 매출액" value={formatCurrency(totalRevenue)} unit="원" />
      <Card label="마케팅비" value={formatCurrency(totalAdCost)} unit="원" />
      <Card label="공헌이익" value={formatCurrency(totalContribution)} unit="원" />
      <Card
        label="총 정산 금액"
        value={formatCurrency(totalSettlement)}
        unit="원"
        accent
      />
      <Card label="기업 / 강의" value={`${companyCount} / ${courseCount}`} unit="개" />
    </div>
  );
}

function Card({
  label,
  value,
  unit,
  accent = false,
}: {
  label: string;
  value: string;
  unit: string;
  accent?: boolean;
}) {
  return (
    <div className="border rounded-lg p-4">
      <div className="text-[10px] text-gray-500 mb-2">{label}</div>
      <div className={`text-lg font-bold tabular-nums ${accent ? "text-[var(--color-accent-orange)]" : ""}`}>
        {value}
        <span className="text-xs font-normal text-gray-400 ml-1">{unit}</span>
      </div>
    </div>
  );
}
