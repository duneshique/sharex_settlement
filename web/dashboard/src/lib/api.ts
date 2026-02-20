const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

export interface CourseSummary {
    course_id: string;
    course_name: string;
    revenue: number;
    ad_cost: number;
    contribution: number;
    revenue_share: number;
    section: string;
    rs_ratio: number;
    monthly_revenue?: Record<string, number>;
}

export interface CompanySettlement {
    company_name: string;
    revenue: number;
    ad_cost: number;
    contribution: number;
    revenue_share: number;
    settlement_amount: number;
    union_payout: number;
    union_payout_ratio: number;
    courses: CourseSummary[];
}

export interface CompanyInfo {
    company_id: string;
    name: string;
    type: string;
    biz_number: string;
    bank: string;
    account: string;
    contact_name: string;
    contact_email: string;
    tax_email: string;
    phone: string;
    address: string;
    representative: string;
    account_holder: string;
    contract_start: string;
    contract_end: string;
    revenue_share_ratio: number;
    union_payout_ratio: number;
}

export interface ApprovalStatus {
    approved: boolean;
    approved_at: string | null;
    approved_by: string | null;
}

export interface ParseResponse {
    period: string;
    extraction_date: string;
    courses: CourseSummary[];
    course_count: number;
    companies: Record<string, CompanySettlement>;
    company_count: number;
    summary: {
        total_revenue: number;
        total_ad_cost: number;
        total_contribution: number;
        total_settlement: number;
    };
    source_file: string;
    has_monthly_breakdown: boolean;
    companies_info: Record<string, CompanyInfo>;
}

export async function parsePdf(file: File): Promise<ParseResponse> {
    const formData = new FormData();
    formData.append("file", file);

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 60000);

    try {
        const res = await fetch(`${API_BASE}/api/settlements/parse`, {
            method: "POST",
            body: formData,
            signal: controller.signal,
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || `API 에러 (${res.status}): ${res.statusText}`);
        }

        return await res.json();
    } catch (error) {
        if (error instanceof TypeError && error.message.includes("fetch")) {
            throw new Error("API 서버 연결 실패");
        }
        throw error;
    } finally {
        clearTimeout(timeout);
    }
}

export async function saveArchive(data: any): Promise<any> {
    const res = await fetch(`${API_BASE}/api/archive/save`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error("저장 실패");
    return res.json();
}

export async function listArchives(): Promise<any> {
    const res = await fetch(`${API_BASE}/api/archive/list`);
    if (!res.ok) throw new Error("목록 조회 실패");
    return res.json();
}

export async function loadArchive(period: string): Promise<any> {
    const res = await fetch(`${API_BASE}/api/archive/${period}`);
    if (!res.ok) throw new Error("로드 실패");
    return res.json();
}

export async function getApprovalStatus(period: string): Promise<any> {
    const res = await fetch(`${API_BASE}/api/archive/${period}/approval-status`);
    if (!res.ok) return {};
    return res.json();
}

export async function sendBulkEmail(period: string, companyIds: string[]): Promise<any> {
    const res = await fetch(`${API_BASE}/api/settlements/send-bulk-email`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ period, company_ids: companyIds }),
    });
    if (!res.ok) throw new Error("발송 실패");
    return res.json();
}
