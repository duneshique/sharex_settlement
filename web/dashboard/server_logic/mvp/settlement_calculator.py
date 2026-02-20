"""
MVP Step 2: 정산 계산기

Step 1에서 추출한 PDF 데이터를 기반으로 각 기업별 정산 금액을 계산합니다.

분기별 PDF는 이미 FastCampus에서 계산한 수익쉐어 강사료가 포함되어 있으므로,
이를 기업별로 집계하여 유니온 실지급액을 계산합니다.
"""

import json
from pathlib import Path
from typing import Dict, List, Any
from decimal import Decimal, ROUND_HALF_UP


def calculate_settlements(
    extracted_data: Dict[str, Any],
    base_path: str = None
) -> Dict[str, Any]:
    """
    기업별 정산 금액 계산 (MVP 간소화 버전)

    Args:
        extracted_data: Step 1의 extract_pdf_data() 반환값
        base_path: 프로젝트 루트 경로 (course_mapping.json 로드용)

    Returns:
        {
            "period": "2024-Q4",
            "companies": {
                "heaz": {
                    "company_id": "heaz",
                    "company_name": "HEAZ",
                    "revenue": 10000000,
                    "ad_cost": 500000,
                    "contribution": 9500000,
                    "revenue_share": 7125000,
                    "union_payout": 4750000,
                    "settlement_amount": 3659120.0
                }
            },
            "total_settlement": 32708346.5,
            "validation": {...}
        }
    """
    if base_path is None:
        base_path = str(Path(__file__).parent.parent.parent)

    # 설정 로드
    course_mapping = _load_course_mapping(base_path)
    companies_data = _load_companies(base_path)

    period = extracted_data["period"]
    courses = extracted_data["courses"]

    # 매출액 자동 역산: revenue가 0이고 contribution이 있으면 보정
    for course in courses:
        if course.get("revenue", 0) == 0 and course.get("contribution", 0) > 0:
            course["revenue"] = course["contribution"] + course.get("ad_cost", 0)
            print(f"  ℹ️  매출액 자동 역산: {course['course_name'][:30]}... → {course['revenue']:,.0f}원")

    # 기업별 집계
    company_settlements = {}

    for course in courses:
        course_id = course["course_id"]

        # 강의 → 기업 매핑
        course_info = course_mapping.get(course_id)
        if not course_info:
            print(f"⚠️  강의 {course_id}가 course_mapping.json에 없습니다")
            continue

        # company_id와 비율 추출
        company_id = course_info.get("company_id")
        if not company_id:
            print(f"⚠️  강의 {course_id}의 company_id가 없습니다")
            continue

        # share_type에 따라 비율 결정
        share_type = course_info.get("share_type", "single")
        if share_type == "single":
            # 단독 제공: 100%
            companies_ratio = {company_id: 1.0}
        else:
            # 공동 제공: companies 필드 사용 (있으면)
            companies_ratio = course_info.get("companies", {company_id: 1.0})

        for company_id, ratio in companies_ratio.items():
            if company_id not in company_settlements:
                company_settlements[company_id] = {
                    "company_id": company_id,
                    "company_name": companies_data.get(company_id, {}).get("name", company_id),
                    "revenue": 0.0,
                    "ad_cost": 0.0,
                    "contribution": 0.0,
                    "revenue_share": 0.0,
                    "courses": [],
                }

            # 비율에 따라 안분
            company_settlements[company_id]["revenue"] += course["revenue"] * ratio
            company_settlements[company_id]["ad_cost"] += course["ad_cost"] * ratio
            company_settlements[company_id]["contribution"] += course["contribution"] * ratio
            company_settlements[company_id]["revenue_share"] += course["revenue_share"] * ratio

            company_settlements[company_id]["courses"].append({
                "course_id": course_id,
                "course_name": course["course_name"],
                "ratio": ratio,
                "revenue": course["revenue"] * ratio,
                "ad_cost": course["ad_cost"] * ratio,
                "contribution": course["contribution"] * ratio,
                "revenue_share": course["revenue_share"] * ratio,
            })

    # 유니온 실지급액 계산
    for company_id, settlement in company_settlements.items():
        contribution = settlement["contribution"]

        # companies.json에서 기업별 union_payout_ratio 조회 (기간별 변동 지원)
        company_info = companies_data.get(company_id, {})
        payout_ratio = _get_payout_ratio(company_info, period)

        union_payout = contribution * payout_ratio

        settlement["union_payout"] = round(union_payout, 2)
        settlement["settlement_amount"] = round(union_payout, 2)
        settlement["union_payout_ratio"] = payout_ratio

        # 각 강의별 revenue_share도 union_payout_ratio 적용
        # (화면 표시 시 contribution × payout_ratio와 일치하도록)
        for course in settlement["courses"]:
            course["revenue_share"] = round(course["contribution"] * payout_ratio, 2)

        # 반올림 처리
        settlement["revenue"] = round(settlement["revenue"], 2)
        settlement["ad_cost"] = round(settlement["ad_cost"], 2)
        settlement["contribution"] = round(settlement["contribution"], 2)
        settlement["revenue_share"] = round(settlement["revenue_share"], 2)

    # 총 정산 금액 (전체 기업 포함)
    total_settlement = sum(
        s["settlement_amount"]
        for cid, s in company_settlements.items()
    )

    result = {
        "period": period,
        "calculation_date": extracted_data.get("extraction_date", ""),
        "companies": company_settlements,
        "total_settlement": round(total_settlement, 2),
        "validation": {},
    }

    return result


def _load_course_mapping(base_path: str) -> Dict[str, dict]:
    """course_mapping.json 로드"""
    path = Path(base_path) / "data" / "course_mapping.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    mapping = {}
    for course in data["courses"]:
        mapping[course["course_id"]] = course

    return mapping


def _get_payout_ratio(company_info: dict, period: str) -> float:
    """
    기간별 수익쉐어 비율 조회

    companies.json에 payout_ratio_changes가 있으면 기간에 따라 비율을 동적 적용.
    예: plusx는 2024년까지 70%, 2025-Q3부터 65%.

    period 형식: "2024-Q4" (분기별) 또는 "2024-10" (월별)
    """
    base_ratio = company_info.get("union_payout_ratio", 0.5)
    changes = company_info.get("payout_ratio_changes", [])

    if not changes:
        return base_ratio

    # 비교를 위해 period를 정규화 (월별 → 분기로 변환)
    normalized = _normalize_period(period)
    for change in sorted(changes, key=lambda c: c["from_period"], reverse=True):
        change_normalized = _normalize_period(change["from_period"])
        if normalized >= change_normalized:
            return change["ratio"]

    return base_ratio


def _normalize_period(period: str) -> str:
    """
    기간 문자열을 비교 가능한 형식으로 변환
    "2024-Q4" → "2024-10", "2025-Q1" → "2025-01", "2024-10" → "2024-10"
    """
    import re
    q_match = re.match(r'^(\d{4})-Q(\d)$', period)
    if q_match:
        year = q_match.group(1)
        quarter = int(q_match.group(2))
        first_month = (quarter - 1) * 3 + 1
        return f"{year}-{first_month:02d}"
    return period


def _load_companies(base_path: str) -> Dict[str, dict]:
    """companies.json 로드"""
    path = Path(base_path) / "data" / "companies.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    companies = {}
    for company in data["companies"]:
        companies[company["company_id"]] = company

    return companies


def save_settlement_result(result: Dict[str, Any], output_path: str) -> None:
    """
    정산 결과를 JSON 파일로 저장

    Args:
        result: calculate_settlements()의 반환값
        output_path: 저장할 JSON 파일 경로
    """
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"✅ 정산 계산 완료: {output_file}")
    print(f"   - 기간: {result['period']}")
    print(f"   - 기업 수: {len(result['companies'])}")
    print(f"   - 총 정산 금액: {result['total_settlement']:,.0f}원 (플러스엑스 제외)")


def load_settlement_result(json_path: str) -> Dict[str, Any]:
    """저장된 정산 결과 로드"""
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ─────────────────────────────────────────────────────────
# 검증 함수
# ─────────────────────────────────────────────────────────

def validate_settlement(
    result: Dict[str, Any],
    expected: Dict[str, float] = None
) -> Dict[str, Any]:
    """
    정산 결과 검증

    Args:
        result: calculate_settlements()의 반환값
        expected: 기대값 {"heaz": 3659120.0, "bkid": 4509514.5, ...}

    Returns:
        {
            "valid": True/False,
            "total_diff": 0.0,
            "company_diffs": {...},
            "errors": [...],
            "warnings": [...]
        }
    """
    errors = []
    warnings = []
    company_diffs = {}

    if expected is None:
        # 확정 데이터가 없으면 기본 검증만 수행
        if result["total_settlement"] <= 0:
            errors.append("총 정산 금액이 0 이하입니다")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }

    # 기업별 비교
    for company_id, expected_amount in expected.items():
        if company_id not in result["companies"]:
            errors.append(f"기업 {company_id}가 정산 결과에 없습니다")
            continue

        actual_amount = result["companies"][company_id]["settlement_amount"]
        diff = actual_amount - expected_amount
        company_diffs[company_id] = {
            "expected": expected_amount,
            "actual": actual_amount,
            "diff": diff,
        }

        # ±1원 이내 허용
        if abs(diff) > 1.0:
            errors.append(
                f"{company_id}: 차이 {diff:,.2f}원 "
                f"(예상 {expected_amount:,.0f} != 실제 {actual_amount:,.0f})"
            )

    # 총합 검증
    total_expected = sum(expected.values())
    total_actual = result["total_settlement"]
    total_diff = total_actual - total_expected

    if abs(total_diff) > 1.0:
        errors.append(
            f"총 정산 금액 차이: {total_diff:,.2f}원 "
            f"(예상 {total_expected:,.0f} != 실제 {total_actual:,.0f})"
        )

    return {
        "valid": len(errors) == 0,
        "total_diff": total_diff,
        "company_diffs": company_diffs,
        "errors": errors,
        "warnings": warnings,
    }


# ─────────────────────────────────────────────────────────
# CLI 테스트용 메인
# ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("사용법: python settlement_calculator.py <intermediate_data.json>")
        sys.exit(1)

    json_path = sys.argv[1]
    base_path = str(Path(__file__).parent.parent.parent)

    print(f"📊 정산 계산 시작: {json_path}")
    print()

    try:
        # 추출 데이터 로드
        with open(json_path, "r", encoding="utf-8") as f:
            extracted_data = json.load(f)

        # 정산 계산
        result = calculate_settlements(extracted_data, base_path)

        # 결과 출력
        print("✅ 정산 계산 완료")
        print(f"   기간: {result['period']}")
        print(f"   기업 수: {len(result['companies'])}")
        print(f"   총 정산 금액: {result['total_settlement']:,.0f}원")
        print()

        # 기업별 정산 금액 (플러스엑스 제외)
        print("기업별 정산 금액:")
        for company_id, settlement in sorted(result["companies"].items()):
            if company_id == "plusx":
                continue
            print(f"  - {settlement['company_name']:20} "
                  f"{settlement['settlement_amount']:>12,.0f}원")
        print()

        # JSON 저장
        period = result["period"]
        output_path = f"output/{period}/settlement_result.json"
        save_settlement_result(result, output_path)

        # 2024-Q4 확정 데이터로 검증 (있으면)
        if period == "2024-Q4":
            expected_2024_q4 = {
                "huskyfox": 6432849.5,
                "cosmicray": 4083126.5,
                "bkid": 4509514.5,
                "heaz": 3659120.0,
                "atelier_dongga": 2392750.5,
                "fontrix": 949759.0,
                "dfy": 2994788.5,
                "compound_c": 2255400.0,
                "csidecity": 1930270.5,
                "blsn": 1031299.0,
                "sandoll": 2469468.5,
            }

            print("\n📋 2024-Q4 확정 데이터 검증:")

            # sabum 제외 (2024 Q4 당시 정산 대상 아님)
            filtered_result = {
                "period": result["period"],
                "companies": {k: v for k, v in result["companies"].items()
                              if k in expected_2024_q4},
                "total_settlement": sum(
                    v["settlement_amount"]
                    for k, v in result["companies"].items()
                    if k in expected_2024_q4
                ),
            }

            validation = validate_settlement(filtered_result, expected_2024_q4)

            if validation["valid"]:
                print("✅ 검증 성공! 모든 금액이 ±1원 이내로 일치합니다")
                print(f"   검증 대상: {len(expected_2024_q4)}개 기업")
                print(f"   총 정산 금액: {filtered_result['total_settlement']:,.1f}원")
            else:
                print("❌ 검증 실패:")
                for error in validation["errors"]:
                    print(f"  - {error}")

                print(f"\n총 차이: {validation['total_diff']:,.2f}원")

            # sabum 안내
            if "sabum" in result["companies"]:
                print(f"\nℹ️  sabum(변사범)은 2024 Q4 당시 정산 대상이 아니었으므로 검증에서 제외되었습니다.")
                print(f"   sabum 정산액: {result['companies']['sabum']['settlement_amount']:,.0f}원")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
