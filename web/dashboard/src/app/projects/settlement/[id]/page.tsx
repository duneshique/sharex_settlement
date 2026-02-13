"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams, useSearchParams } from "next/navigation";
import Link from "next/link";
import {
    loadArchive,
    saveArchive,
    approveCompany,
    unapproveCompany,
    sendEmail,
    getDownloadUrl,
    type ParseResponse,
    type CompanyInfo,
    type CompanySettlement,
    type CourseSummary,
    type ApprovalStatus,
    type EmailLogEntry,
} from "@/lib/api";
import { formatCurrency } from "@/lib/format";

// ============================================================================
// 플러스엑스 정보 (발신자 - PDF 양식과 동일)
// ============================================================================
const ISSUER = {
    name: "플러스엑스 주식회사",
    biz_number: "211-88-46851",
    representative: "유상원 이사",
    address: "서울시 강남구 언주로 149길 17, 4-5F",
    bank: "우리은행",
    account: "1005-980-100727",
    contact: "finance@plus-ex.com",
};

// ============================================================================
// 교차검증: 수치 불일치 탐지
// ============================================================================
interface ValidationIssue {
    field: string;
    expected: number;
    actual: number;
    diff: number;
    message: string;
}

function validateSettlement(s: CompanySettlement): ValidationIssue[] {
    const issues: ValidationIssue[] = [];
    const threshold = 2; // ±2원 허용 (반올림 오차)

    // 1) 강의별 합산 vs 회사 합계
    const sumRevenue = s.courses.reduce((acc, c) => acc + (c.revenue ?? 0), 0);
    const sumAdCost = s.courses.reduce((acc, c) => acc + (c.ad_cost ?? 0), 0);
    const sumContribution = s.courses.reduce((acc, c) => acc + (c.contribution ?? 0), 0);

    if (Math.abs(sumRevenue - s.revenue) > threshold) {
        issues.push({
            field: "매출액",
            expected: s.revenue,
            actual: sumRevenue,
            diff: sumRevenue - s.revenue,
            message: `강의별 매출액 합산(${formatCurrency(sumRevenue)})이 회사 합계(${formatCurrency(s.revenue)})와 ${formatCurrency(Math.abs(sumRevenue - s.revenue))}원 차이납니다.`,
        });
    }

    if (Math.abs(sumAdCost - s.ad_cost) > threshold) {
        issues.push({
            field: "마케팅비",
            expected: s.ad_cost,
            actual: sumAdCost,
            diff: sumAdCost - s.ad_cost,
            message: `강의별 마케팅비 합산(${formatCurrency(sumAdCost)})이 회사 합계(${formatCurrency(s.ad_cost)})와 ${formatCurrency(Math.abs(sumAdCost - s.ad_cost))}원 차이납니다.`,
        });
    }

    if (Math.abs(sumContribution - s.contribution) > threshold) {
        issues.push({
            field: "공헌이익",
            expected: s.contribution,
            actual: sumContribution,
            diff: sumContribution - s.contribution,
            message: `강의별 공헌이익 합산(${formatCurrency(sumContribution)})이 회사 합계(${formatCurrency(s.contribution)})와 ${formatCurrency(Math.abs(sumContribution - s.contribution))}원 차이납니다.`,
        });
    }

    // 2) 공헌이익 = 매출액 - 마케팅비 검증
    const expectedContribution = s.revenue - s.ad_cost;
    if (Math.abs(expectedContribution - s.contribution) > threshold) {
        issues.push({
            field: "공헌이익 공식",
            expected: expectedContribution,
            actual: s.contribution,
            diff: s.contribution - expectedContribution,
            message: `공헌이익(${formatCurrency(s.contribution)})이 "매출액 - 마케팅비"(${formatCurrency(expectedContribution)})와 일치하지 않습니다. 제작비 등 추가 비용이 포함되었을 수 있습니다.`,
        });
    }

    // 3) 수익쉐어 = 공헌이익 × 비율 검증
    const expectedSettlement = Math.round(s.contribution * s.union_payout_ratio);
    if (Math.abs(expectedSettlement - s.settlement_amount) > threshold) {
        issues.push({
            field: "수익쉐어 금액",
            expected: expectedSettlement,
            actual: s.settlement_amount,
            diff: s.settlement_amount - expectedSettlement,
            message: `수익쉐어(${formatCurrency(s.settlement_amount)})가 "공헌이익 × ${Math.round(s.union_payout_ratio * 100)}%"(${formatCurrency(expectedSettlement)})와 ${formatCurrency(Math.abs(s.settlement_amount - expectedSettlement))}원 차이납니다.`,
        });
    }

    // 4) 개별 강의 공헌이익 검증
    s.courses.forEach((c) => {
        const cExpected = (c.revenue ?? 0) - (c.ad_cost ?? 0);
        if (Math.abs(cExpected - (c.contribution ?? 0)) > threshold) {
            issues.push({
                field: `[${c.course_name}] 공헌이익`,
                expected: cExpected,
                actual: c.contribution ?? 0,
                diff: (c.contribution ?? 0) - cExpected,
                message: `"${c.course_name}" 강의의 공헌이익(${formatCurrency(c.contribution ?? 0)})이 "매출-마케팅비"(${formatCurrency(cExpected)})와 불일치합니다.`,
            });
        }
    });

    return issues;
}

// ============================================================================
// 메인 컴포넌트
// ============================================================================
export default function SettlementDetailPage() {
    const params = useParams();
    const searchParams = useSearchParams();
    const companyId = params.id as string;
    const period = searchParams.get("period") || "";

    const [settlement, setSettlement] = useState<CompanySettlement | null>(null);
    const [companyInfo, setCompanyInfo] = useState<CompanyInfo | null>(null);
    const [fullData, setFullData] = useState<ParseResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Remarks 상태
    const [remarks, setRemarks] = useState("");
    const [allRemarks, setAllRemarks] = useState<Record<string, string>>({});
    const [isSaving, setIsSaving] = useState(false);
    const [saveMessage, setSaveMessage] = useState<string | null>(null);

    // 검증 결과
    const [validationIssues, setValidationIssues] = useState<ValidationIssue[]>([]);

    // 편집 모드
    const [isEditing, setIsEditing] = useState(false);
    const [editCourses, setEditCourses] = useState<CourseSummary[]>([]);

    // 승인 상태
    const [approvalStatus, setApprovalStatus] = useState<ApprovalStatus | null>(null);
    const [allApprovalStatus, setAllApprovalStatus] = useState<Record<string, ApprovalStatus>>({});
    const [isApproving, setIsApproving] = useState(false);
    const [pdfFilename, setPdfFilename] = useState<string | null>(null);

    // 이메일 상태
    const [emailLog, setEmailLog] = useState<EmailLogEntry[]>([]);
    const [isSendingEmail, setIsSendingEmail] = useState(false);

    const isApproved = approvalStatus?.approved === true;

    // 편집 시작
    const handleStartEdit = useCallback(() => {
        if (!settlement) return;
        if (isApproved) {
            alert("승인된 정산서는 수정할 수 없습니다. 먼저 승인을 해제해주세요.");
            return;
        }
        setEditCourses(settlement.courses.map(c => ({ ...c })));
        setIsEditing(true);
    }, [settlement, isApproved]);

    // 편집 중 개별 강의 값 변경
    const handleEditCourse = useCallback((idx: number, field: "revenue" | "ad_cost", value: number) => {
        setEditCourses(prev => {
            const updated = [...prev];
            const course = { ...updated[idx] };
            course[field] = value;
            // 공헌이익 자동 재계산
            course.contribution = course.revenue - course.ad_cost;
            updated[idx] = course;
            return updated;
        });
    }, []);

    // 편집 적용 → settlement, fullData, sessionStorage 업데이트
    const handleApplyEdits = useCallback(() => {
        if (!settlement || !fullData) return;
        const ratio = settlement.union_payout_ratio;

        // 새 courses 기반으로 회사 합계 재계산
        const newRevenue = editCourses.reduce((s, c) => s + c.revenue, 0);
        const newAdCost = editCourses.reduce((s, c) => s + c.ad_cost, 0);
        const newContribution = editCourses.reduce((s, c) => s + c.contribution, 0);
        const newSettlementAmount = Math.round(newContribution * ratio);

        // 각 강의별 revenue_share 재계산
        const updatedCourses = editCourses.map(c => ({
            ...c,
            revenue_share: Math.round(c.contribution * ratio),
        }));

        const updatedSettlement: CompanySettlement = {
            ...settlement,
            revenue: newRevenue,
            ad_cost: newAdCost,
            contribution: newContribution,
            settlement_amount: newSettlementAmount,
            union_payout: newSettlementAmount,
            revenue_share: updatedCourses.reduce((s, c) => s + c.revenue_share, 0),
            courses: updatedCourses,
        };

        // fullData 업데이트
        const updatedCompanies = { ...fullData.companies, [companyId]: updatedSettlement };
        const totalSettlement = Object.values(updatedCompanies).reduce((s, c) => s + c.settlement_amount, 0);
        const updatedFullData: ParseResponse = {
            ...fullData,
            companies: updatedCompanies,
            summary: {
                ...fullData.summary,
                total_revenue: Object.values(updatedCompanies).reduce((s, c) => s + c.revenue, 0),
                total_ad_cost: Object.values(updatedCompanies).reduce((s, c) => s + c.ad_cost, 0),
                total_contribution: Object.values(updatedCompanies).reduce((s, c) => s + c.contribution, 0),
                total_settlement: totalSettlement,
            },
        };

        setSettlement(updatedSettlement);
        setFullData(updatedFullData);
        setValidationIssues(validateSettlement(updatedSettlement));
        sessionStorage.setItem("settlementData", JSON.stringify(updatedFullData));
        setIsEditing(false);
        setSaveMessage("수정이 적용되었습니다. '임시 저장'을 눌러 서버에 저장하세요.");
        setTimeout(() => setSaveMessage(null), 5000);
    }, [settlement, fullData, companyId, editCourses]);

    useEffect(() => {
        async function loadData() {
            setLoading(true);
            setError(null);

            // 1차: sessionStorage에서 파싱 데이터 조회
            const cached = sessionStorage.getItem("settlementData");
            if (cached) {
                try {
                    const parsed: ParseResponse = JSON.parse(cached);
                    if (parsed.period === period && parsed.companies[companyId]) {
                        setFullData(parsed);
                        setSettlement(parsed.companies[companyId]);
                        setCompanyInfo(parsed.companies_info?.[companyId] || null);
                        setValidationIssues(validateSettlement(parsed.companies[companyId]));
                        setLoading(false);
                        // sessionStorage에는 승인 정보가 없으므로 아카이브에서 추가 로드
                        try {
                            const archiveData = await loadArchive(period);
                            if (archiveData.approval_status) {
                                setAllApprovalStatus(archiveData.approval_status);
                                setApprovalStatus(archiveData.approval_status[companyId] || null);
                            }
                            if (archiveData.email_log?.[companyId]) {
                                setEmailLog(archiveData.email_log[companyId]);
                            }
                            if (archiveData.remarks) {
                                setAllRemarks(archiveData.remarks);
                                setRemarks(archiveData.remarks[companyId] || "");
                            }
                        } catch { /* archive not found yet, OK */ }
                        return;
                    }
                } catch { /* fallthrough */ }
            }

            // 2차: 아카이브 API에서 로드
            if (period) {
                try {
                    const archiveData = await loadArchive(period);
                    if (archiveData.companies[companyId]) {
                        setFullData(archiveData);
                        setSettlement(archiveData.companies[companyId]);
                        setCompanyInfo(archiveData.companies_info?.[companyId] || null);
                        setValidationIssues(validateSettlement(archiveData.companies[companyId]));
                        // 아카이브에서 remarks 복원
                        const savedRemarks = archiveData.remarks;
                        if (savedRemarks) {
                            setAllRemarks(savedRemarks);
                            setRemarks(savedRemarks[companyId] || "");
                        }
                        // 승인 상태 복원
                        if (archiveData.approval_status) {
                            setAllApprovalStatus(archiveData.approval_status);
                            setApprovalStatus(archiveData.approval_status[companyId] || null);
                        }
                        // 이메일 로그 복원
                        if (archiveData.email_log?.[companyId]) {
                            setEmailLog(archiveData.email_log[companyId]);
                        }
                        setLoading(false);
                        return;
                    }
                } catch { /* fallthrough */ }
            }

            setError("정산 데이터를 찾을 수 없습니다. 정산 목록에서 PDF를 업로드하거나 데이터를 저장해주세요.");
            setLoading(false);
        }

        loadData();
    }, [companyId, period]);

    // 임시 저장 (remarks 포함 아카이브 저장)
    const handleSave = useCallback(async () => {
        if (!fullData) return;
        setIsSaving(true);
        setSaveMessage(null);
        try {
            const updatedRemarks = { ...allRemarks, [companyId]: remarks };
            await saveArchive({
                period: fullData.period,
                companies: fullData.companies,
                summary: fullData.summary,
                source_file: fullData.source_file,
                remarks: updatedRemarks,
            });
            setAllRemarks(updatedRemarks);
            setSaveMessage("저장되었습니다.");
            setTimeout(() => setSaveMessage(null), 3000);
        } catch (err) {
            setSaveMessage(err instanceof Error ? err.message : "저장 실패");
        } finally {
            setIsSaving(false);
        }
    }, [fullData, companyId, remarks, allRemarks]);

    // 최종 승인
    const handleApprove = useCallback(async () => {
        if (!fullData) return;
        const name = companyInfo?.name || companyId;
        if (!confirm(`${name} 정산서를 최종 승인하시겠습니까?\n승인 시 아카이브 저장 및 PDF가 생성됩니다.`)) return;

        setIsApproving(true);
        setSaveMessage(null);
        try {
            // 1) 아카이브 저장 (최신 데이터 반영)
            const updatedRemarks = { ...allRemarks, [companyId]: remarks };
            await saveArchive({
                period: fullData.period,
                companies: fullData.companies,
                summary: fullData.summary,
                source_file: fullData.source_file,
                remarks: updatedRemarks,
            });
            setAllRemarks(updatedRemarks);

            // 2) 승인 API 호출 (PDF 자동 생성 포함)
            const result = await approveCompany(period, companyId);

            // 상태 업데이트
            const newStatus: ApprovalStatus = {
                approved: true,
                approved_at: result.approved_at,
                approved_by: "admin",
            };
            setApprovalStatus(newStatus);
            setAllApprovalStatus(prev => ({ ...prev, [companyId]: newStatus }));
            setPdfFilename(result.pdf_file || null);

            setSaveMessage("승인 완료. PDF가 생성되었습니다.");
            setTimeout(() => setSaveMessage(null), 5000);
        } catch (err) {
            setSaveMessage(err instanceof Error ? err.message : "승인 처리 실패");
        } finally {
            setIsApproving(false);
        }
    }, [fullData, companyId, companyInfo, remarks, allRemarks, period]);

    // 승인 해제
    const handleUnapprove = useCallback(async () => {
        if (!confirm("승인을 해제하시겠습니까?\n해제 후 데이터를 수정할 수 있습니다.")) return;

        setIsApproving(true);
        setSaveMessage(null);
        try {
            await unapproveCompany(period, companyId);

            const newStatus: ApprovalStatus = {
                approved: false,
                approved_at: null,
                approved_by: null,
            };
            setApprovalStatus(newStatus);
            setAllApprovalStatus(prev => ({ ...prev, [companyId]: newStatus }));
            setPdfFilename(null);

            setSaveMessage("승인이 해제되었습니다.");
            setTimeout(() => setSaveMessage(null), 3000);
        } catch (err) {
            setSaveMessage(err instanceof Error ? err.message : "승인 해제 실패");
        } finally {
            setIsApproving(false);
        }
    }, [period, companyId]);

    // PDF 다운로드
    const handleDownloadPdf = useCallback(() => {
        if (!period) return;
        const name = companyInfo?.name || settlement?.company_name || companyId;
        const yearMatch = period.match(/^(\d{4})-Q(\d)$/);
        const yearShort = yearMatch ? yearMatch[1].slice(2) : "";
        const q = yearMatch ? yearMatch[2] : "";
        const filename = pdfFilename || `쉐어엑스_ ${name} ${yearShort}년 ${q}Q 정산서.pdf`;
        const url = getDownloadUrl(period, filename);
        window.open(url, "_blank");
    }, [period, companyInfo, settlement, companyId, pdfFilename]);

    // 이메일 발송
    const handleSendEmail = useCallback(async () => {
        if (!period) return;
        const name = companyInfo?.name || companyId;
        const email = companyInfo?.contact_email || companyInfo?.tax_email;

        if (!email) {
            alert(`${name}의 이메일 주소가 등록되어 있지 않습니다.`);
            return;
        }

        // 재발송 경고
        if (emailLog.length > 0) {
            const lastSent = emailLog[emailLog.length - 1];
            if (!confirm(
                `${name}에 이미 ${emailLog.length}회 발송한 이력이 있습니다.\n` +
                `마지막 발송: ${formatDateTime(lastSent.sent_at)}\n\n` +
                `다시 발송하시겠습니까?`
            )) return;
        } else {
            if (!confirm(`${name} (${email})에 정산서 이메일을 발송하시겠습니까?`)) return;
        }

        setIsSendingEmail(true);
        setSaveMessage(null);
        try {
            const result = await sendEmail(period, companyId);

            // 발송 성공 시 로그 추가
            const newLogEntry: EmailLogEntry = {
                sent_at: new Date().toISOString(),
                recipient: result.recipient || email,
                subject: result.subject || "",
                status: "sent",
                pdf_filename: "",
            };
            setEmailLog(prev => [...prev, newLogEntry]);

            setSaveMessage(`이메일 발송 완료 (${result.recipient || email})`);
            setTimeout(() => setSaveMessage(null), 5000);
        } catch (err) {
            setSaveMessage(err instanceof Error ? err.message : "이메일 발송 실패");
        } finally {
            setIsSendingEmail(false);
        }
    }, [period, companyId, companyInfo, emailLog]);

    const periodLabel = formatPeriodLabel(period);
    const ratioPercent = settlement ? Math.round(settlement.union_payout_ratio * 100) : 50;
    const companyName = companyInfo?.name || settlement?.company_name || companyId;
    const today = formatToday();
    const totalCompanyCount = fullData ? Object.keys(fullData.companies).length : 0;
    const approvedCount = Object.values(allApprovalStatus).filter(s => s.approved).length;

    if (loading) {
        return (
            <div className="max-w-5xl mx-auto flex items-center justify-center min-h-[60vh]">
                <div className="text-gray-400 text-sm animate-pulse">정산 데이터 로딩 중...</div>
            </div>
        );
    }

    if (error || !settlement) {
        return (
            <div className="max-w-5xl mx-auto">
                <Breadcrumb />
                <div className="border-2 border-dashed border-gray-200 rounded-[2px] p-20 text-center mt-8">
                    <div className="text-[15px] font-medium mb-2">{error || "정산 데이터를 찾을 수 없습니다."}</div>
                    <Link href="/projects/settlement" className="text-[13px] text-blue-500 hover:underline mt-4 inline-block">
                        ← 정산 목록으로 돌아가기
                    </Link>
                </div>
            </div>
        );
    }

    return (
        <div className="max-w-4xl mx-auto">
            <Breadcrumb />

            <div className="flex justify-between items-end mb-6">
                <div className="flex items-center gap-3">
                    <h1 className="text-[26px] font-bold">상세 정산서 리뷰</h1>
                    {isApproved && (
                        <span className="px-3 py-1 bg-green-100 text-green-700 text-[11px] font-bold rounded-full">
                            승인됨
                        </span>
                    )}
                </div>
                <Link
                    href="/projects/settlement"
                    className="px-5 py-1.5 border border-gray-300 text-[12px] font-medium rounded-[2px] hover:bg-gray-50 transition-colors"
                >
                    목록으로
                </Link>
            </div>

            {/* 교차검증 결과 */}
            {validationIssues.length > 0 && (
                <ValidationPanel issues={validationIssues} />
            )}

            {/* 정산서 본문 */}
            <div className="bg-white border p-12 shadow-[0_4px_20px_rgba(0,0,0,0.05)] rounded-[2px] mb-6">

                {/* 제목 + 발행일 */}
                <div className="flex justify-between items-start mb-10">
                    <div className="text-[22px] font-bold leading-tight">
                        [ {companyName} ] {periodLabel} 정산서
                    </div>
                    <div className="text-[12px] text-gray-400 font-medium whitespace-nowrap ml-6">[{today}]</div>
                </div>

                {/* 발신 / 수신 정보 — PDF 양식 동일 */}
                <div className="grid grid-cols-2 gap-8 mb-10 text-[12px]">
                    <CompanyInfoBlock
                        label="발신"
                        name={ISSUER.name}
                        bizNumber={ISSUER.biz_number}
                        address={ISSUER.address}
                        representative={ISSUER.representative}
                        bankAccount={`${ISSUER.bank} / ${ISSUER.account}`}
                        contact={ISSUER.contact}
                    />
                    <CompanyInfoBlock
                        label="수신"
                        accent
                        name={companyName}
                        bizNumber={companyInfo?.biz_number}
                        address={companyInfo?.address}
                        representative={companyInfo?.representative}
                        bankAccount={companyInfo ? `${companyInfo.bank} / ${companyInfo.account}` : undefined}
                        contact={companyInfo?.contact_email || companyInfo?.contact_name}
                    />
                </div>

                {/* 요약 (국문 라벨, 균등 크기) */}
                <div className="grid grid-cols-4 border-y border-black py-6 mb-10 text-center bg-[#FBFBFB]">
                    <SummaryCell label="총 매출액" value={settlement.revenue} />
                    <SummaryCell label="마케팅비+제작비" value={settlement.ad_cost} dimmed border />
                    <SummaryCell label="공헌이익" value={settlement.contribution} border />
                    <SummaryCell label="수익쉐어 강사료" value={settlement.settlement_amount} highlight />
                </div>

                {/* 상세 테이블 */}
                <div className="flex justify-between items-center mb-2">
                    <div className="text-[11px] text-gray-400">강의별 상세 내역</div>
                    {!isEditing ? (
                        <button
                            onClick={handleStartEdit}
                            disabled={isApproved}
                            className={`px-3 py-1 border border-gray-300 text-[11px] rounded-[2px] transition-colors ${
                                isApproved
                                    ? "text-gray-300 cursor-not-allowed"
                                    : "text-gray-500 hover:bg-gray-50 hover:text-black"
                            }`}
                            title={isApproved ? "승인 해제 후 수정 가능" : undefined}
                        >
                            수정하기
                        </button>
                    ) : (
                        <div className="flex gap-2">
                            <button
                                onClick={() => setIsEditing(false)}
                                className="px-3 py-1 border border-gray-300 text-[11px] text-gray-500 rounded-[2px] hover:bg-gray-50 transition-colors"
                            >
                                취소
                            </button>
                            <button
                                onClick={handleApplyEdits}
                                className="px-4 py-1 bg-[#FF5C35] text-white text-[11px] font-bold rounded-[2px] hover:bg-[#ff7a5c] transition-colors"
                            >
                                적용
                            </button>
                        </div>
                    )}
                </div>
                <table className="w-full text-left border-collapse text-[12px]">
                    <thead>
                        <tr className="border-y-2 border-black bg-white h-10 text-[11px] text-gray-400 font-bold">
                            <th className="px-4 text-center w-10">#</th>
                            <th className="px-4">강의명</th>
                            <th className="px-4 text-right w-24">매출액</th>
                            <th className="px-4 text-right w-24">마케팅비</th>
                            <th className="px-4 text-right w-24">공헌이익</th>
                            <th className="px-4 text-right w-28">수익쉐어<br /><span className="text-[10px]">(공헌이익x{ratioPercent}%)</span></th>
                        </tr>
                    </thead>
                    <tbody>
                        {isEditing
                            ? editCourses.map((course, idx) => (
                                <EditableCourseRow
                                    key={`${course.course_id}-${idx}`}
                                    course={course}
                                    idx={idx + 1}
                                    ratio={settlement.union_payout_ratio}
                                    onChange={(field: "revenue" | "ad_cost", value: number) => handleEditCourse(idx, field, value)}
                                />
                            ))
                            : settlement.courses.map((course, idx) => (
                                <CourseRow key={`${course.course_id}-${idx}`} course={course} idx={idx + 1} />
                            ))
                        }
                    </tbody>
                    <tfoot>
                        {isEditing ? (
                            <tr className="bg-blue-50 font-bold h-12 border-t-2 border-black">
                                <td colSpan={2} className="px-4 text-center text-[11px] tracking-wide">수정 합계</td>
                                <td className="px-4 text-right font-mono">{formatCurrency(editCourses.reduce((s, c) => s + c.revenue, 0))}</td>
                                <td className="px-4 text-right font-mono">{formatCurrency(editCourses.reduce((s, c) => s + c.ad_cost, 0))}</td>
                                <td className="px-4 text-right font-mono">{formatCurrency(editCourses.reduce((s, c) => s + c.contribution, 0))}</td>
                                <td className="px-4 text-right font-mono text-[#FF5C35]">{formatCurrency(Math.round(editCourses.reduce((s, c) => s + c.contribution, 0) * settlement.union_payout_ratio))}</td>
                            </tr>
                        ) : (
                            <tr className="bg-[#F9FAFB] font-bold h-12 border-t-2 border-black">
                                <td colSpan={2} className="px-4 text-center text-[11px] tracking-wide">합계</td>
                                <td className="px-4 text-right font-mono">{formatCurrency(settlement.revenue)}</td>
                                <td className="px-4 text-right font-mono">{formatCurrency(settlement.ad_cost)}</td>
                                <td className="px-4 text-right font-mono">{formatCurrency(settlement.contribution)}</td>
                                <td className="px-4 text-right font-mono text-[#FF5C35]">{formatCurrency(settlement.settlement_amount)}</td>
                            </tr>
                        )}
                    </tfoot>
                </table>

                {/* 참고사항 — PDF 양식 동일 */}
                <div className="mt-10 pt-8 border-t border-dashed border-gray-200 text-[11px] text-gray-400 space-y-1.5">
                    <p className="font-bold text-gray-500">[참고사항]</p>
                    <p className="font-bold text-gray-500 mt-2">[B2C]</p>
                    <p className="ml-2">*매출액 = 결제금액 - 환불액</p>
                    <p className="ml-2">*공헌이익 = 매출액 - 제작비 - 마케팅비용</p>
                    <p className="ml-2">*수익쉐어 강사료 = 공헌이익 x {ratioPercent}%</p>
                    <p className="ml-2">*마케팅비용의 세부내역은 별도 첨부파일에서 확인 가능합니다.</p>
                    <p className="font-bold text-gray-500 mt-3">[기타 참고사항]</p>
                    <p className="ml-2">*정산서상 모든금액은 부가세포함 금액입니다.</p>
                    <p className="ml-2">*수익쉐어 강사료는 세금계산서 발행 후 15일이내 입금됩니다.</p>
                    <p className="ml-2">*세금계산서 수신이메일: finance@plus-ex.com</p>
                </div>
            </div>

            {/* Remarks 입력 영역 */}
            <div className="bg-white border p-6 rounded-[2px] mb-6">
                <div className="flex items-center justify-between mb-3">
                    <div className="text-[13px] font-bold">Remarks</div>
                    {saveMessage && (
                        <div className={`text-[12px] ${
                            saveMessage.includes("완료") || saveMessage === "저장되었습니다."
                                ? "text-green-600"
                                : saveMessage.includes("실패") ? "text-red-500" : "text-blue-600"
                        }`}>
                            {saveMessage}
                        </div>
                    )}
                </div>
                <textarea
                    value={remarks}
                    onChange={(e) => setRemarks(e.target.value)}
                    placeholder="이 기업에 대한 특이사항, 검토 메모를 입력하세요..."
                    className="w-full border border-gray-200 rounded-[2px] p-3 text-[13px] min-h-[80px] resize-y focus:outline-none focus:border-gray-400 transition-colors"
                />
            </div>

            {/* 이메일 발송 이력 */}
            {emailLog.length > 0 && (
                <div className="bg-white border p-6 rounded-[2px] mb-24">
                    <div className="text-[13px] font-bold mb-3">이메일 발송 이력</div>
                    <table className="w-full text-[12px] border-collapse">
                        <thead>
                            <tr className="border-b border-gray-200 text-[11px] text-gray-400 font-bold">
                                <th className="px-3 py-2 text-left">발송일시</th>
                                <th className="px-3 py-2 text-left">수신자</th>
                                <th className="px-3 py-2 text-left">제목</th>
                                <th className="px-3 py-2 text-center">상태</th>
                            </tr>
                        </thead>
                        <tbody>
                            {emailLog.map((log, i) => (
                                <tr key={i} className="border-b border-gray-100 hover:bg-gray-50">
                                    <td className="px-3 py-2 text-gray-600 font-mono text-[11px]">
                                        {formatDateTime(log.sent_at)}
                                    </td>
                                    <td className="px-3 py-2">{log.recipient}</td>
                                    <td className="px-3 py-2 text-gray-500 truncate max-w-[200px]">{log.subject}</td>
                                    <td className="px-3 py-2 text-center">
                                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                                            log.status === "sent"
                                                ? "bg-green-100 text-green-700"
                                                : "bg-red-100 text-red-700"
                                        }`}>
                                            {log.status === "sent" ? "발송" : "실패"}
                                        </span>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}

            {/* mb-24 spacer if no email log */}
            {emailLog.length === 0 && <div className="mb-24" />}

            {/* Floating Action Bar */}
            <div className="fixed bottom-8 left-[calc(50%+120px)] -translate-x-1/2 bg-black text-white px-6 py-4 rounded-[2px] flex items-center gap-6 z-50 shadow-2xl">
                <div className="flex flex-col">
                    <div className="text-[10px] text-gray-400 font-bold tracking-wide mb-0.5">검토 현황</div>
                    <div className="text-[12px] font-medium">
                        {totalCompanyCount}개 기업 중 <span className="text-[#FF5C35] font-bold">{approvedCount}개</span> 승인 완료
                    </div>
                </div>
                <div className="h-8 w-[1px] bg-gray-700"></div>
                <div className="flex gap-2">
                    <button
                        onClick={handleSave}
                        disabled={isSaving}
                        className="px-6 py-2 border border-white text-[12px] font-bold hover:bg-white hover:text-black transition-all disabled:opacity-50"
                    >
                        {isSaving ? "저장 중..." : "임시 저장"}
                    </button>

                    {isApproved ? (
                        <>
                            <button
                                onClick={handleDownloadPdf}
                                className="px-4 py-2 bg-white text-black text-[12px] font-bold hover:bg-gray-200 transition-all"
                            >
                                PDF
                            </button>
                            <button
                                onClick={handleSendEmail}
                                disabled={isSendingEmail}
                                className="px-4 py-2 bg-blue-500 text-white text-[12px] font-bold hover:bg-blue-600 transition-all disabled:opacity-50"
                            >
                                {isSendingEmail ? "발송 중..." : "이메일"}
                            </button>
                            <button
                                onClick={handleUnapprove}
                                disabled={isApproving}
                                className="px-4 py-2 border border-red-400 text-red-400 text-[12px] font-bold hover:bg-red-500 hover:text-white hover:border-red-500 transition-all disabled:opacity-50"
                            >
                                승인 해제
                            </button>
                        </>
                    ) : (
                        <button
                            onClick={handleApprove}
                            disabled={isApproving}
                            className="px-6 py-2 bg-[#FF5C35] text-white text-[12px] font-bold hover:bg-[#ff7a5c] transition-all disabled:opacity-50"
                        >
                            {isApproving ? "승인 처리 중..." : "최종 승인"}
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
}

// ============================================================================
// 서브 컴포넌트
// ============================================================================

function Breadcrumb() {
    return (
        <div className="flex gap-2 text-[12px] text-gray-400 mb-4">
            <Link href="/projects/settlement" className="hover:text-black">프로젝트</Link>
            <span>&gt;</span>
            <Link href="/projects/settlement" className="hover:text-black">프로젝트 정산</Link>
            <span>&gt;</span>
            <span className="text-black font-medium">상세 정산서</span>
        </div>
    );
}

function CompanyInfoBlock({ label, name, bizNumber, address, representative, bankAccount, contact, accent }: {
    label: string;
    name: string;
    bizNumber?: string;
    address?: string;
    representative?: string;
    bankAccount?: string;
    contact?: string;
    accent?: boolean;
}) {
    return (
        <div className="space-y-1.5">
            <div className={`font-bold pb-1.5 border-b text-[10px] tracking-tight ${accent ? "border-[#FF5C35] text-[#FF5C35]" : "border-black text-black"}`}>
                {label}
            </div>
            <div className="font-bold text-[13px]">{name}</div>
            {bizNumber && <div className="text-gray-500">사업자번호 {bizNumber}</div>}
            {address && <div className="text-gray-500">주소 {address}</div>}
            {representative && <div className="text-gray-500">대표이사 {representative}</div>}
            {bankAccount && <div className="text-gray-500">계좌번호 {bankAccount}</div>}
            {contact && <div className="text-gray-500">담당자 {contact}</div>}
        </div>
    );
}

function SummaryCell({ label, value, dimmed, highlight, border }: {
    label: string;
    value: number;
    dimmed?: boolean;
    highlight?: boolean;
    border?: boolean;
}) {
    return (
        <div className={`px-3 ${border ? "border-r border-gray-100" : ""}`}>
            <div className={`text-[11px] font-bold mb-2 ${highlight ? "text-[#FF5C35]" : "text-gray-400"}`}>
                {label}
            </div>
            <div className={`font-bold text-[18px] font-mono tracking-tighter ${highlight ? "text-[#FF5C35]" : dimmed ? "text-gray-400" : "text-black"}`}>
                {formatCurrency(value)}
            </div>
        </div>
    );
}

function CourseRow({ course, idx }: { course: CourseSummary; idx: number }) {
    return (
        <tr className="border-b h-12 hover:bg-gray-50 transition-colors">
            <td className="px-4 text-center text-gray-400 font-mono">{idx}</td>
            <td className="px-4 font-medium leading-snug">
                {course.course_name}
                {course.section && (
                    <span className="block text-gray-400 text-[10px]">{course.section}</span>
                )}
            </td>
            <td className="px-4 text-right font-mono">{formatCurrency(course.revenue ?? 0)}</td>
            <td className="px-4 text-right font-mono text-gray-400">{formatCurrency(course.ad_cost ?? 0)}</td>
            <td className="px-4 text-right font-mono">{formatCurrency(course.contribution ?? 0)}</td>
            <td className="px-4 text-right font-mono font-bold">{formatCurrency(course.revenue_share ?? 0)}</td>
        </tr>
    );
}

function EditableCourseRow({ course, idx, ratio, onChange }: {
    course: CourseSummary;
    idx: number;
    ratio: number;
    onChange: (field: "revenue" | "ad_cost", value: number) => void;
}) {
    return (
        <tr className="border-b h-12 bg-blue-50/30">
            <td className="px-4 text-center text-gray-400 font-mono">{idx}</td>
            <td className="px-4 font-medium leading-snug text-[11px]">
                {course.course_name}
            </td>
            <td className="px-2 text-right">
                <input
                    type="number"
                    value={course.revenue}
                    onChange={(e) => onChange("revenue", Number(e.target.value) || 0)}
                    className="w-full text-right font-mono text-[12px] border border-blue-300 rounded-[2px] px-2 py-1 bg-white focus:outline-none focus:border-blue-500"
                />
            </td>
            <td className="px-2 text-right">
                <input
                    type="number"
                    value={course.ad_cost}
                    onChange={(e) => onChange("ad_cost", Number(e.target.value) || 0)}
                    className="w-full text-right font-mono text-[12px] border border-blue-300 rounded-[2px] px-2 py-1 bg-white focus:outline-none focus:border-blue-500"
                />
            </td>
            <td className="px-4 text-right font-mono text-[12px]">{formatCurrency(course.contribution)}</td>
            <td className="px-4 text-right font-mono font-bold text-[12px]">{formatCurrency(Math.round(course.contribution * ratio))}</td>
        </tr>
    );
}

function ValidationPanel({ issues }: { issues: ValidationIssue[] }) {
    const [open, setOpen] = useState(true);
    return (
        <div className="mb-4 border border-amber-300 bg-amber-50 rounded-[2px] text-[12px]">
            <button
                onClick={() => setOpen(!open)}
                className="w-full flex justify-between items-center px-4 py-3 text-left font-bold text-amber-800"
            >
                <span>교차검증 결과: {issues.length}건의 불일치 감지</span>
                <span className="text-[10px] text-amber-500">{open ? "접기" : "펼치기"}</span>
            </button>
            {open && (
                <div className="px-4 pb-4 space-y-2">
                    {issues.map((issue, i) => (
                        <div key={i} className="bg-white border border-amber-200 rounded-[2px] p-3">
                            <div className="font-bold text-amber-700 mb-1">{issue.field}</div>
                            <div className="text-gray-600">{issue.message}</div>
                            <div className="mt-1 text-[11px] text-gray-400">
                                기대값: {formatCurrency(issue.expected)} / 실제값: {formatCurrency(issue.actual)} / 차이: {issue.diff > 0 ? "+" : ""}{formatCurrency(issue.diff)}
                            </div>
                        </div>
                    ))}
                    <div className="text-[11px] text-amber-600 mt-2 pl-1">
                        * ±2원 이내의 차이는 반올림으로 인한 정상 오차입니다. 위 항목들은 그 이상의 차이가 감지된 것입니다.
                    </div>
                </div>
            )}
        </div>
    );
}

// ============================================================================
// 유틸리티
// ============================================================================

function formatPeriodLabel(period: string): string {
    const match = period.match(/^(\d{4})-Q(\d)$/);
    if (!match) return period;
    return `${match[1]}년 ${match[2]}분기`;
}

function formatToday(): string {
    const d = new Date();
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${y}.${m}.${day}`;
}

function formatDateTime(isoString: string): string {
    try {
        const d = new Date(isoString);
        const y = d.getFullYear();
        const m = String(d.getMonth() + 1).padStart(2, "0");
        const day = String(d.getDate()).padStart(2, "0");
        const h = String(d.getHours()).padStart(2, "0");
        const min = String(d.getMinutes()).padStart(2, "0");
        return `${y}.${m}.${day} ${h}:${min}`;
    } catch {
        return isoString;
    }
}
