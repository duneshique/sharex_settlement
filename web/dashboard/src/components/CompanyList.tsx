"use client";

import { formatCurrency } from "@/lib/format";
import type { CompanySettlement, CompanyInfo } from "@/lib/api";

interface CompanyListProps {
  companies: Record<string, CompanySettlement>;
  companiesInfo: Record<string, CompanyInfo>;
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export default function CompanyList({
  companies,
  companiesInfo,
  selectedId,
  onSelect,
}: CompanyListProps) {
  // plusx를 맨 위에, 나머지는 정산금액 순으로 정렬
  const plusxEntry = companies["plusx"]
    ? (["plusx", companies["plusx"]] as [string, CompanySettlement])
    : null;
  const others = Object.entries(companies)
    .filter(([id]) => id !== "plusx")
    .sort(([, a], [, b]) => b.settlement_amount - a.settlement_amount);

  const sorted = plusxEntry ? [plusxEntry, ...others] : others;

  return (
    <div className="space-y-1">
      <div className="text-xs font-semibold text-gray-400 px-3 mb-2 uppercase tracking-wider">
        기업별 정산 ({sorted.length}개)
      </div>
      {sorted.map(([id, settlement]) => {
        const info = companiesInfo[id];
        const displayName = info?.name || settlement.company_name || id;
        const isPlusx = id === "plusx";

        return (
          <button
            key={id}
            onClick={() => onSelect(id)}
            className={`w-full text-left px-3 py-2.5 rounded text-sm transition-colors ${
              selectedId === id
                ? "bg-black text-white"
                : "hover:bg-[var(--color-nav-hover)]"
            }`}
          >
            <div className="flex justify-between items-center">
              <span className="truncate font-medium">
                {isPlusx && (
                  <span className={`text-[10px] mr-1 ${selectedId === id ? "text-gray-400" : "text-blue-500"}`}>
                    운영
                  </span>
                )}
                {displayName}
              </span>
              <span
                className={`text-xs tabular-nums ${
                  selectedId === id ? "text-gray-300" : "text-gray-400"
                }`}
              >
                {formatCurrency(settlement.settlement_amount)}
              </span>
            </div>
          </button>
        );
      })}
    </div>
  );
}
