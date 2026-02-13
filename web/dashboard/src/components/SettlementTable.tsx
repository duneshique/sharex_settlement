"use client";

import { useState } from "react";
import { formatCurrency, formatPercent } from "@/lib/format";
import type { CompanySettlement, CourseSummary, CompanyInfo } from "@/lib/api";

// 발신: 플러스엑스 고정 정보 (PDF generator의 ISSUER_INFO와 동일)
const ISSUER = {
  name: "플러스엑스 주식회사",
  biz_number: "211-88-46851",
  address: "서울시 강남구 언주로 149길 17, 4-5F",
  representative: "유상원, 이재훈",
  bank_account: "우리은행/1005-980-100727",
  email: "finance@plus-ex.com",
};

interface SettlementTableProps {
  companyId: string;
  settlement: CompanySettlement;
  companyInfo?: CompanyInfo;
  period?: string;
  remarks?: string;
  onRemarksChange?: (remarks: string) => void;
}

export default function SettlementTable({
  companyId,
  settlement,
  companyInfo,
  period,
  remarks,
  onRemarksChange,
}: SettlementTableProps) {
  const ratio = settlement.union_payout_ratio ?? 0.5;
  const ratioLabel = `공헌이익x${Math.round(ratio * 100)}%`;

  // period 파싱: "2024-Q4" → "2024년 4분기"
  const periodLabel = period ? formatPeriodLabel(period) : "";

  // 수신 회사 정보
  const receiverName = companyInfo?.name || settlement.company_name || companyId;
  const receiverBiz = companyInfo?.biz_number || "";
  const receiverAddress = companyInfo?.address || "";
  const receiverRep = companyInfo?.representative || "";
  const receiverBank = companyInfo
    ? `${companyInfo.bank || ""}/${companyInfo.account || ""}`
    : "";
  const receiverEmail = companyInfo?.contact_email || "";

  // 기본 Remarks (PDF와 동일)
  const defaultRemarks = `[참고사항]\n[B2C]\n*매출액 = 결제금액 - 환불액\n*공헌이익 = 매출액 - 제작비 - 마케팅비용\n*수익쉐어 강사료 = 공헌이익 x ${Math.round(ratio * 100)}%\n*마케팅비용의 세부내역은 별도 첨부파일에서 확인 가능합니다.\n\n[기타 참고사항]\n*정산서상 모든금액은 부가세포함 금액입니다.\n*수익쉐어 강사료는 세금계산서 발행 후 15일내 입금됩니다.\n*세금계산서 수신이메일: finance@plus-ex.com`;

  const [localRemarks, setLocalRemarks] = useState(remarks ?? defaultRemarks);
  const [isEditingRemarks, setIsEditingRemarks] = useState(false);

  return (
    <div className="bg-white border p-10 shadow-sm rounded-sm text-sm">
      {/* Header: 제목 + 날짜 */}
      <div className="flex justify-between items-start mb-8 pb-2 border-b-2 border-black">
        <h2 className="text-xl font-bold">
          [ {receiverName} ] {periodLabel} 정산서
        </h2>
        <span className="text-xs text-gray-400 whitespace-nowrap">
          [{new Date().toISOString().slice(0, 10).replace(/-/g, ".")}]
        </span>
      </div>

      {/* 발신/수신 사업자 정보 (PDF와 동일한 구조) */}
      <div className="grid grid-cols-2 gap-8 mb-8 text-xs leading-relaxed">
        {/* 발신: 플러스엑스 */}
        <div>
          <div className="font-bold text-sm border-b pb-1 mb-2">{ISSUER.name}</div>
          <p>사업자번호 {ISSUER.biz_number}</p>
          <p>주소 {ISSUER.address}</p>
          <p>대표이사 {ISSUER.representative}</p>
          <p>계좌번호 {ISSUER.bank_account}</p>
          <p>담당자 이메일 {ISSUER.email}</p>
        </div>

        {/* 수신: 거래 상대방 */}
        <div>
          <div className="font-bold text-sm border-b pb-1 mb-2">{receiverName}</div>
          {receiverBiz && <p>사업자번호 {receiverBiz}</p>}
          {receiverAddress && <p>주소 {receiverAddress}</p>}
          {receiverRep && <p>대표이사 {receiverRep}</p>}
          {receiverBank && receiverBank !== "/" && <p>계좌번호 {receiverBank}</p>}
          {receiverEmail && <p>담당자 이메일 {receiverEmail}</p>}
        </div>
      </div>

      {/* Summary Bar */}
      <div className="grid grid-cols-4 border-y py-5 mb-8 text-center bg-gray-50">
        <div>
          <div className="text-[10px] text-gray-500 mb-1">총 매출액</div>
          <div className="font-bold">{formatCurrency(settlement.revenue)}</div>
        </div>
        <div>
          <div className="text-[10px] text-gray-500 mb-1">마케팅비+제작비</div>
          <div className="font-bold">{formatCurrency(settlement.ad_cost)}</div>
        </div>
        <div>
          <div className="text-[10px] text-gray-500 mb-1">공헌이익</div>
          <div className="font-bold">{formatCurrency(settlement.contribution)}</div>
        </div>
        <div>
          <div className="text-[10px] text-gray-500 mb-1">수익쉐어 강사료</div>
          <div className="font-bold text-[var(--color-accent-orange)]">
            {formatCurrency(settlement.settlement_amount)}
          </div>
        </div>
      </div>

      {/* Detail Table */}
      <table className="settlement-table">
        <thead>
          <tr>
            <th>정산월</th>
            <th>강의명</th>
            <th className="text-right">매출액</th>
            <th className="text-right">마케팅비</th>
            <th className="text-right">제작비</th>
            <th className="text-right">공헌이익</th>
            <th className="text-right">
              수익쉐어 강사료
              <br />({ratioLabel})
            </th>
          </tr>
        </thead>
        <tbody>
          {settlement.courses?.map((course: CourseSummary, idx: number) => {
            const c_contribution =
              course.contribution ?? course.revenue - (course.ad_cost ?? 0);
            const c_fee = c_contribution * ratio;
            return (
              <tr key={course.course_id || idx}>
                <td className="text-gray-400 text-xs">합계</td>
                <td className="max-w-[200px] truncate">{course.course_name}</td>
                <td className="text-right">{formatCurrency(course.revenue)}</td>
                <td className="text-right">
                  {formatCurrency(course.ad_cost ?? 0)}
                </td>
                <td className="text-right">0</td>
                <td className="text-right font-medium">
                  {formatCurrency(c_contribution)}
                </td>
                <td className="text-right font-bold">{formatCurrency(c_fee)}</td>
              </tr>
            );
          })}
        </tbody>
        <tfoot>
          <tr className="bg-gray-50 font-bold">
            <td colSpan={2} className="text-center">
              합계
            </td>
            <td className="text-right">
              {formatCurrency(settlement.revenue)}
            </td>
            <td className="text-right">
              {formatCurrency(settlement.ad_cost)}
            </td>
            <td className="text-right">0</td>
            <td className="text-right">
              {formatCurrency(settlement.contribution)}
            </td>
            <td className="text-right text-[var(--color-accent-orange)]">
              {formatCurrency(settlement.settlement_amount)}
            </td>
          </tr>
        </tfoot>
      </table>

      {/* Remarks (편집 가능) */}
      <div className="mt-8 pt-6 border-t">
        <div className="flex justify-between items-center mb-2">
          <span className="text-xs font-semibold text-gray-500">Remarks</span>
          <button
            onClick={() => {
              if (isEditingRemarks && onRemarksChange) {
                onRemarksChange(localRemarks);
              }
              setIsEditingRemarks(!isEditingRemarks);
            }}
            className="text-[10px] text-blue-500 hover:underline"
          >
            {isEditingRemarks ? "저장" : "편집"}
          </button>
        </div>
        {isEditingRemarks ? (
          <textarea
            value={localRemarks}
            onChange={(e) => setLocalRemarks(e.target.value)}
            className="w-full h-40 text-[10px] text-gray-500 border rounded p-3 leading-relaxed resize-y focus:outline-none focus:border-gray-400"
          />
        ) : (
          <div className="text-[10px] text-gray-400 whitespace-pre-line leading-relaxed">
            {localRemarks}
          </div>
        )}
      </div>
    </div>
  );
}

function formatPeriodLabel(period: string): string {
  const match = period.match(/^(\d{4})-Q(\d)$/);
  if (!match) return period;
  return `${match[1]}년 ${match[2]}분기`;
}
