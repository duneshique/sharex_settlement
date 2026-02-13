#!/usr/bin/env python3
"""
Share X MVP 정산 파이프라인 CLI

사용법:
    # 전체 파이프라인 실행 (PDF 추출 → 정산 계산 → 정산서 PDF 생성)
    python3 scripts/run_mvp.py --period 2024-Q4

    # 월별 breakdown 포함 (월별 PDF 3개 자동 탐색)
    python3 scripts/run_mvp.py --period 2024-Q4 --monthly

    # 특정 단계만 실행
    python3 scripts/run_mvp.py --period 2024-Q4 --step extract
    python3 scripts/run_mvp.py --period 2024-Q4 --step calculate
    python3 scripts/run_mvp.py --period 2024-Q4 --step generate

    # 검증 포함
    python3 scripts/run_mvp.py --period 2024-Q4 --validate

    # 2025 Q4 실행
    python3 scripts/run_mvp.py --period 2025-Q4
"""

import argparse
import sys
import json
from pathlib import Path
from datetime import datetime

# 프로젝트 루트를 모듈 검색 경로에 추가
BASE_PATH = str(Path(__file__).parent.parent)
sys.path.insert(0, BASE_PATH)

from src.mvp.pdf_extractor import (
    extract_pdf_data,
    extract_quarterly_with_monthly,
    save_extracted_data,
    load_extracted_data,
)
from src.parsers.base import parse_quarter_months
from src.mvp.settlement_calculator import (
    calculate_settlements,
    save_settlement_result,
    load_settlement_result,
    validate_settlement,
)
from src.mvp.pdf_generator import generate_all_settlement_pdfs


# 2024 Q4 확정 데이터 (검증 기준)
EXPECTED_2024_Q4 = {
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


def main():
    parser = argparse.ArgumentParser(
        description="Share X MVP 정산 파이프라인",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--period",
        "-p",
        default="2024-Q4",
        help="정산 기간 (예: 2024-Q4, 2025-Q4)",
    )

    parser.add_argument(
        "--step",
        "-s",
        choices=["extract", "calculate", "generate", "all"],
        default="all",
        help="실행할 단계 (기본: all)",
    )

    parser.add_argument(
        "--monthly",
        "-m",
        action="store_true",
        help="월별 PDF를 탐색하여 월별 breakdown 포함",
    )

    parser.add_argument(
        "--validate",
        "-v",
        action="store_true",
        help="계산 결과를 확정 금액과 검증",
    )

    parser.add_argument(
        "--base-path",
        default=BASE_PATH,
        help="프로젝트 루트 경로",
    )

    parser.add_argument(
        "--output-dir",
        "-o",
        default=None,
        help="출력 디렉토리 (기본: output/YYYY-QN/)",
    )

    args = parser.parse_args()

    # 기본값 설정
    if args.output_dir is None:
        args.output_dir = f"output/{args.period}"

    print(f"\n{'='*70}")
    print(f"Share X MVP 정산 파이프라인")
    print(f"{'='*70}")
    print(f"기간: {args.period}")
    print(f"단계: {args.step}")
    print(f"월별: {'Yes' if args.monthly else 'No'}")
    print(f"경로: {args.base_path}")
    print(f"출력: {args.output_dir}")
    print(f"{'='*70}\n")

    try:
        # Step 1: PDF 추출
        if args.step in ("extract", "all"):
            print("📄 Step 1: PDF 데이터 추출")
            print("-" * 70)
            extracted_data = run_extract_step(args.period, args.base_path, args.output_dir, args.monthly)
            if extracted_data is None:
                print("❌ Step 1 실패")
                return False
            print()
        else:
            print("⏭️  Step 1 스킵 (기존 데이터 사용)")
            extracted_data = load_extracted_data(f"{args.output_dir}/intermediate_data.json")
            print(f"   로드: {extracted_data['course_count']}개 강의\n")

        # Step 2: 정산 계산
        if args.step in ("calculate", "all"):
            print("📊 Step 2: 정산 계산")
            print("-" * 70)
            settlement_result = run_calculate_step(
                extracted_data, args.period, args.base_path, args.output_dir
            )
            if settlement_result is None:
                print("❌ Step 2 실패")
                return False

            # 검증
            if args.validate:
                print("\n📋 검증")
                print("-" * 70)
                run_validation_step(settlement_result, args.period)

            print()
        else:
            print("⏭️  Step 2 스킵 (기존 데이터 사용)")
            settlement_result = load_settlement_result(f"{args.output_dir}/settlement_result.json")
            print(f"   로드: {len(settlement_result['companies'])}개 기업\n")

        # Step 3: PDF 생성
        if args.step in ("generate", "all"):
            print("📋 Step 3: 정산서 PDF 생성")
            print("-" * 70)
            run_generate_step(settlement_result, args.base_path, args.output_dir)
            print()

        # 완료
        print(f"{'='*70}")
        print("✅ MVP 파이프라인 완료!")
        print(f"{'='*70}")
        print(f"\n📁 출력 파일: {args.output_dir}/")
        print(f"   - intermediate_data.json (추출 데이터)")
        print(f"   - settlement_result.json (정산 결과)")
        print(f"   - 쉐어엑스_*.pdf (정산서 12개)")
        print()

        return True

    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False


def find_quarterly_pdf(archive_dir: Path, year: str, q: str) -> Path:
    """분기 PDF 파일 탐색"""
    import unicodedata

    q_text = f"{q}Q"
    q_korean = {"1": "1분기", "2": "2분기", "3": "3분기", "4": "4분기"}.get(q, f"{q}분기")

    for f in archive_dir.iterdir():
        if f.suffix.lower() != ".pdf":
            continue
        name_nfc = unicodedata.normalize("NFC", f.name)
        if year in name_nfc and (q_text in name_nfc or q_korean in name_nfc):
            return f

    return None


def find_monthly_pdfs(archive_dir: Path, period: str) -> dict:
    """월별 PDF 파일 탐색. {month: pdf_path} 반환"""
    import unicodedata

    months = parse_quarter_months(period)  # ["2024-10", "2024-11", "2024-12"]
    found = {}

    # macOS는 NFD 유니코드 파일명 사용 → NFC 정규화 후 매칭
    all_files = list(archive_dir.iterdir())

    for month in months:
        year, mm = month.split("-")
        month_num = int(mm)
        pattern = f"{year}년 {month_num}월"

        for f in all_files:
            if f.suffix.lower() != ".pdf":
                continue
            name_nfc = unicodedata.normalize("NFC", f.name)
            if pattern in name_nfc and "분기" not in name_nfc and "Q" not in name_nfc:
                found[month] = str(f)
                break

    return found


def run_extract_step(period: str, base_path: str, output_dir: str, monthly: bool = False) -> dict:
    """Step 1: PDF 추출"""
    try:
        archive_dir = Path(base_path) / "archive" / "FastCampus_Settlement"
        year, q = period.split("-Q")

        # 분기 PDF 찾기
        quarterly_pdf = find_quarterly_pdf(archive_dir, year, q)
        if quarterly_pdf is None:
            print(f"❌ {period} 분기 PDF 파일을 찾을 수 없습니다")
            print(f"   검색 위치: {archive_dir}")
            return None

        print(f"📥 분기 PDF: {quarterly_pdf.name}")

        # 월별 모드
        if monthly:
            monthly_pdfs = find_monthly_pdfs(archive_dir, period)
            months = parse_quarter_months(period)

            if len(monthly_pdfs) == len(months):
                print(f"📥 월별 PDF: {len(monthly_pdfs)}개 발견")
                for m, p in sorted(monthly_pdfs.items()):
                    print(f"   - {m}: {Path(p).name}")

                extracted_data = extract_quarterly_with_monthly(
                    str(quarterly_pdf), monthly_pdfs, period, base_path
                )
            else:
                found_months = sorted(monthly_pdfs.keys())
                missing = [m for m in months if m not in monthly_pdfs]
                print(f"⚠️  월별 PDF 일부 미발견 ({len(monthly_pdfs)}/{len(months)}개)")
                print(f"   미발견: {', '.join(missing)}")
                print(f"   → 분기 전용 모드로 fallback")
                extracted_data = extract_pdf_data(str(quarterly_pdf), base_path)
        else:
            extracted_data = extract_pdf_data(str(quarterly_pdf), base_path)

        # 저장
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        output_file = Path(output_dir) / "intermediate_data.json"
        save_extracted_data(extracted_data, str(output_file))

        print(f"✅ 추출 완료: {extracted_data['course_count']}개 강의")
        print(f"   매출: {extracted_data['total_revenue']:,.0f}원")
        if extracted_data.get("has_monthly_breakdown"):
            print(f"   월별 breakdown: 포함")

        return extracted_data

    except Exception as e:
        print(f"❌ 추출 실패: {e}")
        return None


def run_calculate_step(
    extracted_data: dict,
    period: str,
    base_path: str,
    output_dir: str,
) -> dict:
    """Step 2: 정산 계산"""
    try:
        # 계산
        settlement_result = calculate_settlements(extracted_data, base_path)

        # 저장
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        output_file = Path(output_dir) / "settlement_result.json"
        save_settlement_result(settlement_result, str(output_file))

        print(f"✅ 정산 계산 완료: {len(settlement_result['companies'])}개 기업")
        print(f"   총 정산: {settlement_result['total_settlement']:,.0f}원")

        return settlement_result

    except Exception as e:
        print(f"❌ 정산 계산 실패: {e}")
        return None


def run_validation_step(settlement_result: dict, period: str) -> bool:
    """검증"""
    try:
        if period == "2024-Q4":
            # sabum 제외
            filtered_result = {
                "period": settlement_result["period"],
                "companies": {
                    k: v
                    for k, v in settlement_result["companies"].items()
                    if k in EXPECTED_2024_Q4
                },
                "total_settlement": sum(
                    v["settlement_amount"]
                    for k, v in settlement_result["companies"].items()
                    if k in EXPECTED_2024_Q4
                ),
            }

            validation = validate_settlement(filtered_result, EXPECTED_2024_Q4)

            if validation["valid"]:
                print(f"✅ 검증 성공!")
                print(f"   기업 수: {len(EXPECTED_2024_Q4)}개")
                print(f"   총 정산: {filtered_result['total_settlement']:,.1f}원")
                print(f"   모든 금액이 ±1원 이내로 일치합니다")
                return True
            else:
                print(f"❌ 검증 실패")
                for error in validation["errors"]:
                    print(f"   - {error}")
                return False
        else:
            print(f"ℹ️  {period}은 기준 데이터가 없어 검증을 스킵합니다")
            return True

    except Exception as e:
        print(f"❌ 검증 실패: {e}")
        return False


def run_generate_step(settlement_result: dict, base_path: str, output_dir: str) -> bool:
    """Step 3: PDF 생성"""
    try:
        # 기업 정보 로드
        companies_data = {}
        companies_path = Path(base_path) / "data" / "companies.json"
        if companies_path.exists():
            with open(companies_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for company in data.get("companies", []):
                    companies_data[company["company_id"]] = company

        # PDF 생성
        results = generate_all_settlement_pdfs(settlement_result, output_dir, companies_data)

        print(f"✅ PDF 생성 완료: {len(results)}개 파일")

        return len(results) > 0

    except Exception as e:
        print(f"❌ PDF 생성 실패: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
