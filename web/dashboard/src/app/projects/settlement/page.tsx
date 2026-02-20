"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import Link from "next/link";
import {
    parsePdf,
    saveArchive,
    getApprovalStatus,
    sendBulkEmail,
    type ParseResponse,
    type CompanyInfo,
    type ApprovalStatus,
} from "@/lib/api";
import { formatCurrency } from "@/lib/format";
import UploadZone from "@/components/UploadZone";

const SESSION_KEY = "settlementData";

export default function SettlementListPage() {
    const [data, setData] = useState<ParseResponse | null>(null);
    const [isUploading, setIsUploading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [isSaving, setIsSaving] = useState(false);
    const [savedMessage, setSavedMessage] = useState<string | null>(null);
    const fileRef = useRef<HTMLInputElement>(null);

    // 승인 상태
    const [approvalStatus, setApprovalStatus] = useState<Record<string, ApprovalStatus>>({});

    // 일괄 이메일 모달
    const [showEmailModal, setShowEmailModal] = useState(false);

    // 뒤로가기 시 데이터 복원 (sessionStorage 캐시)
    useEffect(() => {
        const cached = sessionStorage.getItem(SESSION_KEY);
        if (cached) {
            try {
                const parsed: ParseResponse = JSON.parse(cached);
                setData(parsed);
                // 승인 상태도 로드
                if (parsed.period) {
                    getApprovalStatus(parsed.period)
                        .then(setApprovalStatus)
                        .catch(() => { });
                }
            } catch { /* ignore */ }
        }
    }, []);

    // PDF 업로드 및 파싱
    const handleUpload = useCallback(async (file: File) => {
        setIsUploading(true);
        setError(null);
        setSavedMessage(null);
        try {
            console.log("PDF 파싱 시작:", file.name);
            const result = await parsePdf(file);
            console.log("PDF 파싱 완료:", result);
            setData(result);
            sessionStorage.setItem(SESSION_KEY, JSON.stringify(result));
            // 승인 상태 초기화 (새 업로드)
            setApprovalStatus({});
        } catch (err) {
            const errMsg = err instanceof Error ? err.message : "PDF 파싱 실패";
            console.error("파싱 에러:", errMsg);
            if (errMsg.includes("Failed to fetch") || errMsg.includes("fetch")) {
                setError("API 서버 연결 실패\n\n서버를 시작해주세요:\npython3 scripts/run_api.py\n\n또는 대신 CLI를 사용하세요:\npython3 scripts/run_mvp.py --period 2024-Q4");
            } else if (errMsg.includes("PDF") || errMsg.includes("파싱")) {
                setError(`PDF 파싱 실패: ${errMsg}\n\n- PDF 파일이 정산서 양식인지 확인해주세요\n- 파일 이름에 YYYY년 Q분기 형식이 포함되어 있는지 확인하세요`);
            } else {
                setError(`오류: ${errMsg}`);
            }
        } finally {
            setIsUploading(false);
        }
    }, []);

    // 데이터 저장
    const handleSave = useCallback(async () => {
        if (!data) return;
        setIsSaving(true);
        try {
            const result = await saveArchive({
                period: data.period,
                companies: data.companies,
                summary: data.summary,
                source_file: data.source_file,
            });
            setSavedMessage(`${result.period} 데이터가 저장되었습니다.`);
            // 저장 후 승인 상태 새로고침
            getApprovalStatus(data.period)
                .then(setApprovalStatus)
                .catch(() => { });
        } catch (err) {
            setError(err instanceof Error ? err.message : "저장 실패");
        } finally {
            setIsSaving(false);
        }
    }, [data]);

    // 기업 목록 생성 (plusx 포함, 정산금액 순)
    const companyList = data
        ? Object.entries(data.companies)
            .sort(([, a], [, b]) => b.settlement_amount - a.settlement_amount)
            .map(([id, s], idx) => {
                const info: CompanyInfo | undefined = data.companies_info?.[id];
                const status = approvalStatus[id];
                return {
                    id,
                    idx: idx + 1,
                    period: formatPeriodLabel(data.period),
                    company: info?.name || s.company_name || id,
                    profit: s.contribution,
                    share: s.settlement_amount,
                    ratio: s.union_payout_ratio,
                    type: id === "plusx" ? "운영사" : "유니온",
                    approved: status?.approved === true,
                    contactEmail: info?.contact_email || info?.tax_email || "",
                };
            })
        : [];

    const approvedCount = companyList.filter(c => c.approved).length;

    return (
        <div className="max-w-6xl mx-auto">
            <div className="flex justify-between items-start mb-8">
                <div>
                    <h1 className="text-[32px] font-bold mb-2">쉐어엑스 정산 관리</h1>
                    <p className="text-[14px] text-gray-500">
                        분기별 프로젝트 정산 내역을 생성하고 승인/발송을 관리합니다.<br />
                        쉐어엑스 정산서 PDF를 업로드하면 자동으로 기업별 정산이 계산됩니다.
                    </p>
                </div>
                <div className="flex gap-2">
                    {data && approvedCount > 0 && (
                        <button
                            onClick={() => setShowEmailModal(true)}
                            className="px-6 py-2 bg-blue-500 text-white text-[13px] font-bold rounded-[2px] hover:bg-blue-600 transition-colors"
                        >
                            이메일 발송
                        </button>
                    )}
                    {data && (
                        <button
                            onClick={handleSave}
                            disabled={isSaving}
                            className="px-6 py-2 border border-gray-300 text-[13px] font-bold rounded-[2px] hover:bg-gray-50 transition-colors disabled:opacity-50"
                        >
                            {isSaving ? "저장 중..." : "데이터 저장하기"}
                        </button>
                    )}
                    <button
                        onClick={() => fileRef.current?.click()}
                        disabled={isUploading}
                        className="px-6 py-2 border border-black text-[13px] font-bold rounded-[2px] hover:bg-gray-50 transition-colors disabled:opacity-50"
                    >
                        {isUploading ? "분석 중..." : "정산서 업로드"}
                    </button>
                    <input
                        ref={fileRef}
                        type="file"
                        accept=".pdf"
                        className="hidden"
                        onChange={(e) => {
                            const file = e.target.files?.[0];
                            if (file) handleUpload(file);
                            e.target.value = "";
                        }}
                    />
                </div>
            </div>

            {error && (
                <div className="mb-4 p-4 border border-red-200 bg-red-50 rounded-[2px] text-[13px] text-red-600 whitespace-pre-line">
                    {error}
                </div>
            )}

            {savedMessage && (
                <div className="mb-4 p-4 border border-green-200 bg-green-50 rounded-[2px] text-[13px] text-green-700">
                    {savedMessage}
                </div>
            )}

            {/* 요약 바 (국문) */}
            {data && (
                <div className="grid grid-cols-4 border-y border-black py-8 mb-8 text-center bg-[#FBFBFB]">
                    <div className="border-r border-gray-100 px-4">
                        <div className="text-[11px] font-bold text-gray-400 mb-2">총 매출액</div>
                        <div className="font-bold text-[22px] font-mono tracking-tighter">{formatCurrency(data.summary.total_revenue)}</div>
                    </div>
                    <div className="border-r border-gray-100 px-4">
                        <div className="text-[11px] font-bold text-gray-400 mb-2">마케팅비+제작비</div>
                        <div className="font-bold text-[22px] font-mono tracking-tighter text-gray-400">{formatCurrency(data.summary.total_ad_cost)}</div>
                    </div>
                    <div className="border-r border-gray-100 px-4">
                        <div className="text-[11px] font-bold text-gray-400 mb-2">공헌이익</div>
                        <div className="font-bold text-[22px] font-mono tracking-tighter">{formatCurrency(data.summary.total_contribution)}</div>
                    </div>
                    <div className="px-4">
                        <div className="text-[11px] font-bold text-[#FF5C35] mb-2">수익쉐어 합계</div>
                        <div className="font-bold text-[22px] text-[#FF5C35] font-mono tracking-tighter">{formatCurrency(data.summary.total_settlement)}</div>
                    </div>
                </div>
            )}

            {/* 기업별 테이블 */}
            {!isUploading && companyList.length > 0 ? (
                <div className="bg-white border-t-2 border-black">
                    <table className="w-full text-left border-collapse">
                        <thead>
                            <tr className="border-b text-[12px] text-gray-400 font-medium h-12">
                                <th className="px-6 w-16">#</th>
                                <th className="px-6">정산 기간</th>
                                <th className="px-6">유니온 기업</th>
                                <th className="px-6 text-right">공헌이익</th>
                                <th className="px-6 text-right">수익쉐어 합계</th>
                                <th className="px-6 text-center">비율</th>
                                <th className="px-6 text-center w-20">승인</th>
                                <th className="px-6 text-center w-32">상세</th>
                            </tr>
                        </thead>
                        <tbody>
                            {companyList.map((item) => (
                                <tr key={item.id} className="border-b hover:bg-[#F9FAFB] transition-colors h-[64px]">
                                    <td className="px-6 text-[14px] text-gray-400">{item.idx}</td>
                                    <td className="px-6 text-[14px]">{item.period}</td>
                                    <td className="px-6 text-[14px] font-medium">
                                        {item.id === "plusx" && <span className="text-[10px] text-blue-500 mr-1">운영</span>}
                                        {item.company}
                                    </td>
                                    <td className="px-6 text-[14px] text-right font-mono">{formatCurrency(item.profit)}</td>
                                    <td className="px-6 text-[14px] text-right font-bold text-[#FF5C35] font-mono">{formatCurrency(item.share)}</td>
                                    <td className="px-6 text-center text-[13px] text-gray-400">{Math.round(item.ratio * 100)}%</td>
                                    <td className="px-6 text-center">
                                        {item.approved ? (
                                            <span className="px-2 py-0.5 bg-green-100 text-green-700 text-[10px] font-bold rounded-full">
                                                승인
                                            </span>
                                        ) : (
                                            <span className="px-2 py-0.5 bg-gray-100 text-gray-400 text-[10px] font-bold rounded-full">
                                                미승인
                                            </span>
                                        )}
                                    </td>
                                    <td className="px-6 text-center">
                                        <Link
                                            href={`/projects/settlement/${item.id}?period=${data!.period}`}
                                            className="px-4 py-1.5 border border-black text-[12px] font-medium hover:bg-gray-50 rounded-[2px]"
                                        >
                                            상세
                                        </Link>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>

                    {/* 승인 현황 요약 */}
                    {Object.keys(approvalStatus).length > 0 && (
                        <div className="px-6 py-3 bg-gray-50 border-t text-[12px] text-gray-500">
                            {companyList.length}개 기업 중 <span className="font-bold text-green-600">{approvedCount}개</span> 승인 완료
                        </div>
                    )}
                </div>
            ) : (
                <UploadZone onFileSelect={handleUpload} isLoading={isUploading} />
            )}

            {/* 일괄 이메일 발송 모달 */}
            {showEmailModal && data && (
                <BulkEmailModal
                    period={data.period}
                    companyList={companyList}
                    onClose={() => setShowEmailModal(false)}
                />
            )}
        </div>
    );
}

// ============================================================================
// 일괄 이메일 발송 모달
// ============================================================================

interface CompanyListItem {
    id: string;
    company: string;
    approved: boolean;
    contactEmail: string;
    share: number;
}

function BulkEmailModal({
    period,
    companyList,
    onClose,
}: {
    period: string;
    companyList: CompanyListItem[];
    onClose: () => void;
}) {
    const approvedCompanies = companyList.filter(c => c.approved && c.id !== "plusx");
    const [selected, setSelected] = useState<Set<string>>(
        new Set(approvedCompanies.filter(c => c.contactEmail).map(c => c.id))
    );
    const [isSending, setIsSending] = useState(false);
    const [result, setResult] = useState<Record<string, string> | null>(null);

    const toggleSelect = (id: string) => {
        setSelected(prev => {
            const next = new Set(prev);
            if (next.has(id)) next.delete(id);
            else next.add(id);
            return next;
        });
    };

    const toggleAll = () => {
        const selectable = approvedCompanies.filter(c => c.contactEmail);
        if (selected.size === selectable.length) {
            setSelected(new Set());
        } else {
            setSelected(new Set(selectable.map(c => c.id)));
        }
    };

    const handleSend = async () => {
        if (selected.size === 0) return;
        if (!confirm(`${selected.size}개 기업에 정산서 이메일을 일괄 발송하시겠습니까?`)) return;

        setIsSending(true);
        try {
            const res = await sendBulkEmail(period, Array.from(selected));
            setResult(res.results);
        } catch (err) {
            alert(err instanceof Error ? err.message : "일괄 발송 실패");
        } finally {
            setIsSending(false);
        }
    };

    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[100]" onClick={onClose}>
            <div
                className="bg-white rounded-[2px] shadow-2xl w-[560px] max-h-[80vh] flex flex-col"
                onClick={(e) => e.stopPropagation()}
            >
                {/* 헤더 */}
                <div className="px-6 py-4 border-b flex justify-between items-center">
                    <div>
                        <div className="text-[16px] font-bold">일괄 이메일 발송</div>
                        <div className="text-[12px] text-gray-400 mt-0.5">
                            승인된 기업에 정산서 이메일을 일괄 발송합니다.
                        </div>
                    </div>
                    <button onClick={onClose} className="text-gray-400 hover:text-black text-[20px] leading-none">&times;</button>
                </div>

                {/* 기업 리스트 */}
                <div className="flex-1 overflow-y-auto px-6 py-4">
                    {result ? (
                        // 발송 결과 표시
                        <div className="space-y-2">
                            <div className="text-[13px] font-bold mb-3">발송 결과</div>
                            {Object.entries(result).map(([companyId, status]) => {
                                const company = companyList.find(c => c.id === companyId);
                                return (
                                    <div key={companyId} className="flex justify-between items-center py-2 border-b border-gray-100">
                                        <span className="text-[13px]">{company?.company || companyId}</span>
                                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${status === "sent"
                                                ? "bg-green-100 text-green-700"
                                                : "bg-red-100 text-red-700"
                                            }`}>
                                            {status === "sent" ? "발송 완료" : status}
                                        </span>
                                    </div>
                                );
                            })}
                        </div>
                    ) : (
                        // 기업 선택
                        <>
                            <div className="flex justify-between items-center mb-3">
                                <div className="text-[12px] text-gray-400">
                                    승인된 기업: {approvedCompanies.length}개 / 선택: {selected.size}개
                                </div>
                                <button
                                    onClick={toggleAll}
                                    className="text-[12px] text-blue-500 hover:underline"
                                >
                                    {selected.size === approvedCompanies.filter(c => c.contactEmail).length ? "전체 해제" : "전체 선택"}
                                </button>
                            </div>

                            {approvedCompanies.length === 0 ? (
                                <div className="text-center py-10 text-[13px] text-gray-400">
                                    승인된 기업이 없습니다. 먼저 상세 페이지에서 기업을 승인해주세요.
                                </div>
                            ) : (
                                <div className="space-y-1">
                                    {approvedCompanies.map((company) => {
                                        const hasEmail = !!company.contactEmail;
                                        return (
                                            <label
                                                key={company.id}
                                                className={`flex items-center gap-3 p-3 rounded-[2px] transition-colors ${hasEmail ? "hover:bg-gray-50 cursor-pointer" : "opacity-50 cursor-not-allowed"
                                                    }`}
                                            >
                                                <input
                                                    type="checkbox"
                                                    checked={selected.has(company.id)}
                                                    onChange={() => hasEmail && toggleSelect(company.id)}
                                                    disabled={!hasEmail}
                                                    className="w-4 h-4 rounded border-gray-300"
                                                />
                                                <div className="flex-1">
                                                    <div className="text-[13px] font-medium">{company.company}</div>
                                                    <div className="text-[11px] text-gray-400">
                                                        {hasEmail ? company.contactEmail : "이메일 미등록"}
                                                        {" · "}
                                                        {formatCurrency(company.share)}
                                                    </div>
                                                </div>
                                            </label>
                                        );
                                    })}
                                </div>
                            )}
                        </>
                    )}
                </div>

                {/* 하단 버튼 */}
                <div className="px-6 py-4 border-t flex justify-end gap-2">
                    <button
                        onClick={onClose}
                        className="px-5 py-2 border border-gray-300 text-[13px] font-medium rounded-[2px] hover:bg-gray-50 transition-colors"
                    >
                        {result ? "닫기" : "취소"}
                    </button>
                    {!result && (
                        <button
                            onClick={handleSend}
                            disabled={isSending || selected.size === 0}
                            className="px-5 py-2 bg-blue-500 text-white text-[13px] font-bold rounded-[2px] hover:bg-blue-600 transition-colors disabled:opacity-50"
                        >
                            {isSending ? "발송 중..." : `${selected.size}개 기업 발송`}
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
}

function formatPeriodLabel(period: string): string {
    const match = period.match(/^(\d{4})-Q(\d)$/);
    if (!match) return period;
    return `${match[1]}년 ${match[2]}분기`;
}
