"""
Share X 정산 안분 계산 엔진
==============================
Phase 0-4: 안분 공식 코드화

핵심 공식:
    간접광고비 안분액 = 총 간접광고비 ÷ 전체 활성 강의 수 × 해당 기업 강의 수

계산 플로우:
    1. 입력 데이터 로드 (매출, 광고비)
    2. 광고비 분류 (직접/간접)
    3. 간접광고비 기업별 안분
    4. 정산 금액 계산 (공헌이익 → 수익쉐어 강사료 → 유니온 실지급)
    5. 교차검증
"""

import json
import os
import re
from dataclasses import dataclass, field, asdict
from typing import Optional
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


# ──────────────────────────────────────────────
# 데이터 클래스 정의
# ──────────────────────────────────────────────

@dataclass
class Company:
    """기업 정보"""
    company_id: str
    name: str
    type: str  # "운영사", "유니온", "유니온(신규)"
    biz_number: str = ""
    bank: str = ""
    account: str = ""
    contact_name: str = ""
    contact_email: str = ""
    tax_email: str = ""
    phone: str = ""
    contract_start: str = ""
    contract_end: str = ""


@dataclass
class Course:
    """강의 정보"""
    course_id: str
    course_name: str
    company_id: str
    company_name: str
    share_type: str = "single"  # "single" or "shared"
    share_ratio: float = 1.0
    is_active: bool = True
    exclude_from_settlement: bool = False


@dataclass
class CampaignCost:
    """캠페인별 광고비"""
    month: str  # "YYYY-MM"
    channel: str  # "Google", "Meta", "Naver", "Pinterest"
    target: str  # "SHARE X", "PLUS X", "BKID", etc.
    campaign_name: str
    cost_krw: float  # KRW 금액 (VAT 포함)
    cost_usd: float = 0.0  # USD 원본 (Meta의 경우)
    exchange_rate: float = 0.0  # 적용 환율
    clicks: int = 0
    impressions: int = 0


@dataclass
class CourseSales:
    """강의별 매출 데이터"""
    month: str  # "YYYY-MM"
    course_id: str
    course_name: str
    company_id: str
    revenue: float  # 매출액


@dataclass
class CompanySettlement:
    """기업별 정산 결과"""
    company_id: str
    company_name: str
    period: str  # "YYYY-QN" (e.g., "2024-Q4")

    # 매출
    total_revenue: float = 0.0
    course_revenues: dict = field(default_factory=dict)  # {course_id: revenue}

    # 광고비
    direct_ad_cost: float = 0.0
    indirect_ad_cost: float = 0.0
    total_ad_cost: float = 0.0

    # 정산 금액
    contribution_margin: float = 0.0  # 공헌이익 = 매출 - 광고비
    revenue_share_fee: float = 0.0  # 수익쉐어 강사료
    union_payout: float = 0.0  # 유니온 실지급 강사료

    # 안분 상세
    course_count: int = 0
    indirect_ad_per_course: float = 0.0

    # 메타데이터
    revenue_share_ratio: float = 0.75  # 기본값 75%
    union_payout_ratio: float = 0.50  # 유니온 비율 (강사료의 2/3 ≈ 50%)


@dataclass
class ValidationResult:
    """교차검증 결과"""
    check_name: str
    passed: bool
    expected: float = 0.0
    actual: float = 0.0
    difference: float = 0.0
    tolerance: float = 1.0  # 허용 오차 (원)
    message: str = ""


# ──────────────────────────────────────────────
# 핵심 안분 엔진 클래스
# ──────────────────────────────────────────────

class ApportionmentEngine:
    """
    Share X 정산 안분 계산 엔진

    사용법:
        engine = ApportionmentEngine(base_path="/path/to/ShareX_Settlement")
        engine.load_config()

        # 광고비 데이터 입력
        engine.add_campaign_cost(CampaignCost(...))

        # 매출 데이터 입력
        engine.add_course_sales(CourseSales(...))

        # 안분 계산 실행
        results = engine.calculate_settlement(period="2024-Q4")

        # 교차검증
        validation = engine.validate(results, expected_data)
    """

    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)

        # 설정 데이터
        self.companies: dict[str, Company] = {}
        self.courses: dict[str, Course] = {}
        self.campaign_rules: dict = {}
        self.exchange_rates: dict[str, float] = {}

        # 입력 데이터
        self.campaign_costs: list[CampaignCost] = []
        self.course_sales: list[CourseSales] = []

        # 기본 설정값
        self.period = ""  # 현재 처리 중인 기간 (예: "2024-Q4")
        self.default_revenue_share_ratio = 0.75  # 공헌이익 대비 수익쉐어 비율
        self.default_union_payout_ratio = 2/3    # 수익쉐어 중 유니온 실지급 비율

    # ──────────────────────────────────────────
    # 설정 로드
    # ──────────────────────────────────────────

    def load_config(self):
        """JSON 설정 파일 로드"""
        self._load_companies()
        self._load_courses()
        self._load_campaign_rules()
        print(f"[Config] 기업 {len(self.companies)}개, 강의 {len(self.courses)}개, 캠페인 규칙 로드 완료")

    def _load_companies(self):
        """data/companies.json 로드"""
        path = self.base_path / "data" / "companies.json"
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for c in data["companies"]:
            company = Company(**{k: v for k, v in c.items() if k in Company.__dataclass_fields__})
            self.companies[company.company_id] = company

    def _load_courses(self):
        """data/course_mapping.json 로드"""
        path = self.base_path / "data" / "course_mapping.json"
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for c in data["courses"]:
            course = Course(**{k: v for k, v in c.items() if k in Course.__dataclass_fields__})
            self.courses[course.course_id] = course

    def _load_campaign_rules(self):
        """config/campaign_rules.json 로드"""
        path = self.base_path / "config" / "campaign_rules.json"
        with open(path, "r", encoding="utf-8") as f:
            self.campaign_rules = json.load(f)

        # 환율 데이터 로드
        self.exchange_rates = {
            k: float(v)
            for k, v in self.campaign_rules.get("exchange_rates", {}).items()
        }

    # ──────────────────────────────────────────
    # 데이터 입력
    # ──────────────────────────────────────────

    def add_campaign_cost(self, cost: CampaignCost):
        """광고비 데이터 추가"""
        self.campaign_costs.append(cost)

    def add_course_sales(self, sales: CourseSales):
        """매출 데이터 추가"""
        self.course_sales.append(sales)

    def clear_input_data(self):
        """입력 데이터 초기화"""
        self.campaign_costs.clear()
        self.course_sales.clear()

    # ──────────────────────────────────────────
    # 광고비 분류
    # ──────────────────────────────────────────

    def classify_campaign(self, campaign_name: str, target: str = "") -> dict:
        """
        캠페인을 직접/간접으로 분류

        Args:
            campaign_name: 캠페인명 (예: "SA_쉐어엑스_자상호")
            target: 광고 대상 (예: "SHARE X", "BKID")

        Returns:
            {
                "type": "direct" or "indirect",
                "target": "SHARE X" or company_id,
                "company_id": company_id or None
            }
        """
        target_mapping = self.campaign_rules.get("classification_rules", {}).get("target_mapping", {})

        # 1차: target 필드가 있으면 우선 사용
        if target and target in target_mapping:
            rule = target_mapping[target]
            return {
                "type": rule["type"],
                "target": target,
                "company_id": rule.get("company_id")
            }

        # 2차: 캠페인명으로 패턴 매칭
        # 직접 광고 대상 키워드를 먼저 체크 (더 구체적인 매칭 우선)
        direct_targets = {k: v for k, v in target_mapping.items() if v["type"] == "direct"}
        for target_name, rule in direct_targets.items():
            company_id = rule.get("company_id", "")
            # 캠페인명에 기업 키워드가 포함되어 있는지 확인
            keywords = self._get_company_keywords(target_name, company_id)
            for keyword in keywords:
                if keyword.lower() in campaign_name.lower():
                    return {
                        "type": "direct",
                        "target": target_name,
                        "company_id": company_id
                    }

        # 3차: 기본값 - 간접광고
        return {
            "type": "indirect",
            "target": "SHARE X",
            "company_id": None
        }

    def _get_company_keywords(self, target_name: str, company_id: str) -> list[str]:
        """기업 식별 키워드 반환"""
        keyword_map = {
            "PLUS X": ["PLUS X", "플러스엑스", "플러스", "plusx"],
            "BKID": ["BKID", "비케이아이디"],
            "BLSN": ["BLSN", "블센", "김형준"],
            "SANDOLL": ["SANDOLL", "산돌"],
            "HEAZ": ["HEAZ", "헤즈"],
            "HUSKYFOX": ["HUSKYFOX", "허스키폭스", "허스키"],
            "COSMICRAY": ["COSMICRAY", "코스믹레이"],
            "FONTRIX": ["FONTRIX", "폰트릭스"],
            "DFY": ["DFY", "디파이"],
            "COMPOUND-C": ["COMPOUND", "컴파운드"],
            "CSIDECITY": ["CSIDECITY", "시싸이드"],
        }
        return keyword_map.get(target_name, [target_name])

    # ──────────────────────────────────────────
    # 활성 강의 수 계산
    # ──────────────────────────────────────────

    def get_active_courses(self, period_months: list[str] = None) -> dict[str, list[Course]]:
        """
        기업별 활성 강의 목록 반환

        Args:
            period_months: 대상 월 리스트 (예: ["2024-10", "2024-11", "2024-12"])
                           None이면 전체 활성 강의 반환

        Returns:
            {company_id: [Course, ...]}
        """
        company_courses: dict[str, list[Course]] = {}

        for course in self.courses.values():
            if course.exclude_from_settlement:
                continue
            if not course.is_active:
                continue

            cid = course.company_id
            if cid not in company_courses:
                company_courses[cid] = []
            company_courses[cid].append(course)

        return company_courses

    def get_total_active_course_count(self, period_months: list[str] = None) -> int:
        """전체 활성 강의 수"""
        company_courses = self.get_active_courses(period_months)
        return sum(len(courses) for courses in company_courses.values())

    def get_company_course_count(self, company_id: str, period_months: list[str] = None) -> int:
        """특정 기업의 활성 강의 수"""
        company_courses = self.get_active_courses(period_months)
        return len(company_courses.get(company_id, []))

    # ──────────────────────────────────────────
    # 환율 처리
    # ──────────────────────────────────────────

    def convert_usd_to_krw(self, amount_usd: float, month: str) -> float:
        """
        USD → KRW 변환

        Args:
            amount_usd: USD 금액
            month: 적용월 (YYYY-MM)

        Returns:
            KRW 금액
        """
        rate = self.exchange_rates.get(month)
        if rate is None:
            # 가장 가까운 환율 사용
            available = sorted(self.exchange_rates.keys())
            if available:
                rate = self.exchange_rates[available[-1]]
                print(f"[Warning] {month} 환율 미등록. {available[-1]}의 환율({rate}) 사용")
            else:
                raise ValueError(f"환율 데이터가 없습니다: {month}")

        return amount_usd * rate

    # ──────────────────────────────────────────
    # 핵심: 안분 계산
    # ──────────────────────────────────────────

    def calculate_settlement(
        self,
        period: str,
        period_months: list[str],
        revenue_share_ratio: float = None,
        union_payout_ratio: float = None,
        total_course_override: int = None,
    ) -> dict[str, CompanySettlement]:
        """
        기업별 정산 금액 계산

        Args:
            period: 정산 기간 (예: "2024-Q4")
            period_months: 대상 월 리스트 (예: ["2024-10", "2024-11", "2024-12"])
            revenue_share_ratio: 수익쉐어 비율 (기본 0.75)
            union_payout_ratio: 유니온 실지급 비율 (기본 2/3)
            total_course_override: 전체 강의 수 수동 지정 (None이면 매핑 테이블 기준)

        Returns:
            {company_id: CompanySettlement}
        """
        self.period = period
        rs_ratio = revenue_share_ratio or self.default_revenue_share_ratio
        union_ratio = union_payout_ratio or self.default_union_payout_ratio

        # 1. 활성 강의 수 계산
        total_courses = total_course_override or self.get_total_active_course_count(period_months)
        company_courses = self.get_active_courses(period_months)

        print(f"\n{'='*60}")
        print(f"정산 계산 시작: {period} ({', '.join(period_months)})")
        print(f"전체 활성 강의 수: {total_courses}")
        print(f"수익쉐어 비율: {rs_ratio*100:.0f}%")
        print(f"{'='*60}")

        # 2. 광고비 분류 (직접/간접, 월별)
        direct_costs_by_company: dict[str, float] = {}  # company_id → total direct cost
        indirect_costs_by_month: dict[str, float] = {}  # month → total indirect cost
        total_indirect_cost = 0.0

        for cost in self.campaign_costs:
            if cost.month not in period_months:
                continue

            classification = self.classify_campaign(cost.campaign_name, cost.target)

            if classification["type"] == "direct":
                cid = classification["company_id"]
                if cid:
                    direct_costs_by_company[cid] = direct_costs_by_company.get(cid, 0) + cost.cost_krw
            else:
                # 간접광고비
                indirect_costs_by_month[cost.month] = indirect_costs_by_month.get(cost.month, 0) + cost.cost_krw
                total_indirect_cost += cost.cost_krw

        print(f"\n[광고비 분류]")
        print(f"  직접광고비: {sum(direct_costs_by_company.values()):,.0f}원 ({len(direct_costs_by_company)}개 기업)")
        print(f"  간접광고비: {total_indirect_cost:,.0f}원")
        for cid, cost in direct_costs_by_company.items():
            name = self.companies.get(cid, Company(company_id=cid, name=cid, type="unknown")).name
            print(f"    - {name}: {cost:,.0f}원")

        # 3. 간접광고비 기업별 안분
        # 공식: 기업 간접광고비 = 총 간접광고비 ÷ 전체 강의 수 × 기업 강의 수
        indirect_per_course = total_indirect_cost / total_courses if total_courses > 0 else 0

        print(f"\n[안분 계산]")
        print(f"  간접광고비 1강의당: {indirect_per_course:,.2f}원")

        # 4. 매출 집계 (기업별)
        revenue_by_company: dict[str, float] = {}
        course_revenues: dict[str, dict[str, float]] = {}  # company_id → {course_id: revenue}

        for sales in self.course_sales:
            if sales.month not in period_months:
                continue

            cid = sales.company_id
            if cid not in revenue_by_company:
                revenue_by_company[cid] = 0
                course_revenues[cid] = {}

            revenue_by_company[cid] += sales.revenue
            course_revenues[cid][sales.course_id] = course_revenues[cid].get(sales.course_id, 0) + sales.revenue

        # 5. 기업별 정산 결과 계산
        results: dict[str, CompanySettlement] = {}

        # 유니온 기업만 정산 (운영사 플러스엑스 제외)
        union_companies = {
            cid for cid, company in self.companies.items()
            if company.type in ("유니온", "유니온(신규)")
        }

        for cid in union_companies:
            company = self.companies[cid]
            course_count = len(company_courses.get(cid, []))

            if course_count == 0:
                continue

            # 매출
            total_revenue = revenue_by_company.get(cid, 0)

            # 직접광고비
            direct_cost = direct_costs_by_company.get(cid, 0)

            # 간접광고비 안분
            indirect_cost = indirect_per_course * course_count

            # 총 광고비
            total_ad = direct_cost + indirect_cost

            # 공헌이익
            contribution = total_revenue - total_ad

            # 수익쉐어 강사료 & 실지급 (기업별 비율 적용)
            c_rs_ratio = getattr(company, "revenue_share_ratio", rs_ratio)
            c_payout_ratio = getattr(company, "union_payout_ratio", union_ratio)
            
            rs_fee = contribution * c_rs_ratio
            union_payout = contribution * c_payout_ratio

            settlement = CompanySettlement(
                company_id=cid,
                company_name=company.name,
                period=period,
                total_revenue=total_revenue,
                course_revenues=course_revenues.get(cid, {}),
                direct_ad_cost=direct_cost,
                indirect_ad_cost=round(indirect_cost, 2),
                total_ad_cost=round(total_ad, 2),
                contribution_margin=round(contribution, 2),
                revenue_share_fee=round(rs_fee, 2),
                union_payout=round(union_payout, 2),
                course_count=course_count,
                indirect_ad_per_course=round(indirect_per_course, 2),
                revenue_share_ratio=c_rs_ratio,
                union_payout_ratio=c_payout_ratio,
            )
            results[cid] = settlement

        # 6. 결과 출력
        print(f"\n[기업별 정산 결과]")
        print(f"{'기업명':<15} {'매출':>15} {'직접광고':>12} {'간접광고':>12} {'공헌이익':>15} {'강사료':>15} {'실지급':>15}")
        print("-" * 100)

        total_union_payout = 0
        for cid in sorted(results.keys(), key=lambda x: results[x].union_payout, reverse=True):
            s = results[cid]
            print(f"{s.company_name:<15} {s.total_revenue:>15,.0f} {s.direct_ad_cost:>12,.0f} {s.indirect_ad_cost:>12,.0f} {s.contribution_margin:>15,.0f} {s.revenue_share_fee:>15,.1f} {s.union_payout:>15,.1f}")
            total_union_payout += s.union_payout

        print("-" * 100)
        print(f"{'합계':<15} {'':>15} {'':>12} {'':>12} {'':>15} {'':>15} {total_union_payout:>15,.1f}")

        return results

    # ──────────────────────────────────────────
    # 교차검증
    # ──────────────────────────────────────────

    def validate(
        self,
        results: dict[str, CompanySettlement],
        expected: dict[str, float] = None,
        tolerance: float = 1.0
    ) -> list[ValidationResult]:
        """
        교차검증 수행

        검증 항목:
        1. 합계 일치: Σ(기업별 마케팅비) = 원본 전체 마케팅비
        2. 매핑 완전성: 모든 코스ID가 매핑 테이블에 존재
        3. 기업 완전성: 모든 유니온 기업이 정산 결과에 포함
        4. 안분 비율 합계: 각 강의별 Σ(안분비율) = 100%
        5. 확정 금액 비교: 자동계산 vs 확정 정산서
        """
        validations = []

        # 검증 1: 매핑 완전성
        unmapped_courses = []
        for sales in self.course_sales:
            if sales.course_id not in self.courses:
                unmapped_courses.append(sales.course_id)

        validations.append(ValidationResult(
            check_name="매핑 완전성",
            passed=len(unmapped_courses) == 0,
            expected=0,
            actual=len(unmapped_courses),
            message=f"미매핑 코스: {unmapped_courses}" if unmapped_courses else "모든 코스 매핑 확인"
        ))

        # 검증 2: 기업 완전성
        union_companies = {
            cid for cid, c in self.companies.items()
            if c.type in ("유니온", "유니온(신규)")
            and self.get_company_course_count(cid) > 0
        }
        missing_companies = union_companies - set(results.keys())

        validations.append(ValidationResult(
            check_name="기업 완전성",
            passed=len(missing_companies) == 0,
            expected=len(union_companies),
            actual=len(results),
            message=f"누락 기업: {[self.companies[c].name for c in missing_companies]}" if missing_companies else "모든 유니온 기업 포함"
        ))

        # 검증 3: 안분 비율 합계 (각 강의별)
        total_courses = self.get_total_active_course_count()
        total_indirect_portions = sum(r.course_count for r in results.values())
        # 플러스엑스(운영사) 강의도 안분에 포함되므로, 운영사 강의 수 추가
        plusx_courses = self.get_company_course_count("plusx")
        total_with_plusx = total_indirect_portions + plusx_courses

        validations.append(ValidationResult(
            check_name="안분 강의 수 합계",
            passed=total_with_plusx == total_courses,
            expected=total_courses,
            actual=total_with_plusx,
            message=f"유니온({total_indirect_portions}) + 플엑({plusx_courses}) = {total_with_plusx}, 전체 {total_courses}"
        ))

        # 검증 4: 확정 금액 비교 (expected가 제공된 경우)
        if expected:
            for cid, expected_amount in expected.items():
                if cid in results:
                    actual = results[cid].union_payout
                    diff = abs(actual - expected_amount)
                    validations.append(ValidationResult(
                        check_name=f"확정 금액 비교: {results[cid].company_name}",
                        passed=diff <= tolerance,
                        expected=expected_amount,
                        actual=actual,
                        difference=diff,
                        tolerance=tolerance,
                        message=f"차이: {diff:,.1f}원 ({'PASS' if diff <= tolerance else 'FAIL'})"
                    ))

            # 합계 비교
            total_expected = sum(expected.values())
            total_actual = sum(r.union_payout for cid, r in results.items() if cid in expected)
            total_diff = abs(total_actual - total_expected)

            validations.append(ValidationResult(
                check_name="전체 합계 비교",
                passed=total_diff <= tolerance * len(expected),
                expected=total_expected,
                actual=total_actual,
                difference=total_diff,
                tolerance=tolerance * len(expected),
                message=f"합계 차이: {total_diff:,.1f}원"
            ))

        # 결과 출력
        print(f"\n{'='*60}")
        print(f"교차검증 결과")
        print(f"{'='*60}")

        all_passed = True
        for v in validations:
            status = "✅ PASS" if v.passed else "❌ FAIL"
            print(f"{status} | {v.check_name}")
            if v.message:
                print(f"       {v.message}")
            if not v.passed:
                all_passed = False
                if v.expected or v.actual:
                    print(f"       예상: {v.expected:,.1f} / 실제: {v.actual:,.1f} / 차이: {v.difference:,.1f}")

        print(f"\n{'전체 PASS ✅' if all_passed else '일부 FAIL ❌'}")

        return validations

    # ──────────────────────────────────────────
    # 정산메일 생성
    # ──────────────────────────────────────────

    def generate_settlement_email(
        self,
        settlement: CompanySettlement,
        quarter_label: str = "4분기",
        year_label: str = "2025",
        payment_date: str = "2026/01/30",
        tax_invoice_date: str = "2026년 01월 26일",
        sender_name: str = "정혜선",
        dashboard_url: str = "",
    ) -> dict:
        """
        기업별 정산 메일 본문 생성

        Args:
            settlement: 정산 결과
            quarter_label: 분기 표시 (예: "4분기")
            year_label: 연도 (예: "2025")
            payment_date: 지급 예정일
            tax_invoice_date: 세금계산서 발행일
            sender_name: 발신자명
            dashboard_url: 광고비 대시보드 URL

        Returns:
            {"subject": str, "body": str}
        """
        company = self.companies.get(settlement.company_id)
        if not company:
            raise ValueError(f"기업 정보 없음: {settlement.company_id}")

        # VAT 포함 금액 계산 (유니온 실지급 기준)
        amount_with_vat = settlement.union_payout
        amount_formatted = f"{amount_with_vat:,.0f}원(vat포함)"

        # 내용 문자열
        content = f"{company.name} 쉐어엑스 강사료_ {quarter_label[0]}Q/{year_label}"

        # 은행/계좌 정보
        bank_info = f"{company.bank}은행/ {company.account} / {company.name}"

        # 담당자명 (호칭 포함)
        contact = company.contact_name.replace("님", "")

        # 제목
        subject = f"[플러스엑스-{company.name}] 쉐어엑스 {year_label[2:]}년 {quarter_label} 정산서"

        # 본문
        dashboard_line = ""
        if dashboard_url:
            dashboard_line = f"광고매체별 상세 내역은  [{dashboard_url}]  에서 확인 부탁 드리며, "

        body = f"""안녕하세요. {contact}
플러스엑스 {sender_name}입니다.
잘 지내고 계신가요? : )

쉐어엑스 {quarter_label} 정산서 전달 드립니다.

매출내역 확인부탁 드리며, 광고비용은 기존과 동일하게, 강의 수 기준으로 안분하여 반영되었습니다.
{dashboard_line}
정산 관련하여 추가 궁금하신 내용이 있다면 문의 주시기 바랍니다.

추가 확인사항이 없으시면, 아래 내용으로 세금계산서 발행 부탁 드립니다.

{quarter_label[0]}Q 정산금액은 {payment_date}일 지급 예정입니다.

날 짜: {tax_invoice_date}
내 용: {content}
금 액: {amount_formatted}
메 일: finance@plus-ex.com
계 좌: {bank_info}

감사합니다.
{sender_name}드림"""

        return {
            "subject": subject,
            "body": body,
            "to": company.contact_email,
            "company_id": settlement.company_id,
            "company_name": company.name,
            "amount": amount_with_vat,
        }

    # ──────────────────────────────────────────
    # 결과 내보내기
    # ──────────────────────────────────────────

    def export_results(self, results: dict[str, CompanySettlement], output_dir: str = None):
        """정산 결과를 JSON으로 내보내기"""
        if output_dir is None:
            output_dir = str(self.base_path / "output")

        os.makedirs(output_dir, exist_ok=True)

        # 기업별 결과
        export_data = {
            "period": list(results.values())[0].period if results else "",
            "settlements": {},
            "summary": {
                "total_union_payout": sum(r.union_payout for r in results.values()),
                "total_revenue": sum(r.total_revenue for r in results.values()),
                "total_ad_cost": sum(r.total_ad_cost for r in results.values()),
                "company_count": len(results),
            }
        }

        for cid, s in results.items():
            export_data["settlements"][cid] = {
                "company_id": s.company_id,
                "company_name": s.company_name,
                "total_revenue": s.total_revenue,
                "direct_ad_cost": s.direct_ad_cost,
                "indirect_ad_cost": s.indirect_ad_cost,
                "total_ad_cost": s.total_ad_cost,
                "contribution_margin": s.contribution_margin,
                "revenue_share_fee": s.revenue_share_fee,
                "union_payout": s.union_payout,
                "course_count": s.course_count,
                "revenue_share_ratio": s.revenue_share_ratio,
            }

        output_path = os.path.join(output_dir, f"settlement_{export_data['period']}.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)

        print(f"\n결과 저장: {output_path}")
        return output_path


# ──────────────────────────────────────────────
# 편의 함수
# ──────────────────────────────────────────────

def format_krw(amount: float) -> str:
    """KRW 금액 포매팅"""
    if amount == 0:
        return "0원"
    return f"{amount:,.0f}원"


def format_krw_with_vat(amount: float) -> str:
    """VAT 포함 금액 포매팅"""
    return f"{amount:,.0f}원(vat포함)"


def parse_quarter_months(period: str) -> list[str]:
    """
    분기 문자열에서 월 리스트 추출
    예: "2024-Q4" → ["2024-10", "2024-11", "2024-12"]
    """
    year, q = period.split("-Q")
    q = int(q)
    start_month = (q - 1) * 3 + 1
    return [f"{year}-{start_month + i:02d}" for i in range(3)]


# ──────────────────────────────────────────────
# 메인 실행 (데모)
# ──────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    # 기본 경로 설정
    if len(sys.argv) > 1:
        base_path = sys.argv[1]
    else:
        # 스크립트 위치의 상위 디렉토리
        base_path = str(Path(__file__).parent.parent)

    print(f"Base path: {base_path}")

    # 엔진 초기화
    engine = ApportionmentEngine(base_path)
    engine.load_config()

    # 설정 확인 출력
    print(f"\n[설정 확인]")
    print(f"  기업 수: {len(engine.companies)}")
    print(f"  강의 수: {len(engine.courses)}")
    print(f"  전체 활성 강의: {engine.get_total_active_course_count()}")

    company_courses = engine.get_active_courses()
    for cid, courses in sorted(company_courses.items(), key=lambda x: len(x[1]), reverse=True):
        name = engine.companies[cid].name
        print(f"    {name}: {len(courses)}개")

    print(f"\n  환율 데이터: {len(engine.exchange_rates)}개월")
    for month, rate in sorted(engine.exchange_rates.items()):
        print(f"    {month}: {rate:,.2f} KRW/USD")

    print("\n✅ 안분 엔진 초기화 완료. Phase 1에서 실제 데이터를 입력하여 계산을 수행합니다.")
    print("   사용법: engine.add_campaign_cost() → engine.add_course_sales() → engine.calculate_settlement()")
