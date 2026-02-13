#!/usr/bin/env python3
"""
Share X 정산 자동화 CLI
==============================

사용법:
    # 분기 정산서 PDF에서 직접 유니온 지급액 계산 (가장 정확)
    python3 run_settlement.py --period 2024-Q4 --source quarterly_pdf

    # 월별 PDF에서 매출+광고비 추출 → 안분 계산
    python3 run_settlement.py --period 2024-Q4 --source pdf

    # Excel Master/Info에서 데이터 추출 → 안분 계산
    python3 run_settlement.py --period 2024-Q4 --source excel

    # 검증만 수행
    python3 run_settlement.py --period 2024-Q4 --validate

    # 모든 소스로 계산 후 교차 비교
    python3 run_settlement.py --period 2024-Q4 --compare-all
"""

import argparse
import sys
from pathlib import Path

# 프로젝트 루트를 모듈 검색 경로에 추가
BASE_PATH = str(Path(__file__).parent.parent)
sys.path.insert(0, BASE_PATH)

from src.pipeline import (
    run_quarterly_pdf_pipeline,
    run_monthly_pipeline,
    validate_results,
    load_ground_truth_from_union_pdfs,
)
from src.reports.excel_report import generate_excel_report


def main():
    parser = argparse.ArgumentParser(
        description="Share X 정산 자동화 CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--period", "-p",
        default="2024-Q4",
        help="정산 기간 (예: 2024-Q4, 2025-Q1)",
    )
    parser.add_argument(
        "--source", "-s",
        choices=["quarterly_pdf", "pdf", "excel"],
        default="quarterly_pdf",
        help="데이터 소스 (기본: quarterly_pdf)",
    )
    parser.add_argument(
        "--validate", "-v",
        action="store_true",
        help="결과를 확정 금액과 비교 검증",
    )
    parser.add_argument(
        "--compare-all",
        action="store_true",
        help="모든 소스로 계산 후 교차 비교",
    )
    parser.add_argument(
        "--base-path",
        default=BASE_PATH,
        help="프로젝트 루트 경로",
    )
    parser.add_argument(
        "--output", "-o",
        default="output",
        help="리포트 출력 디렉토리 (기본: output)",
    )

    args = parser.parse_args()

    print(f"Share X 정산 자동화")
    print(f"기간: {args.period}")
    print(f"소스: {args.source}")
    print(f"경로: {args.base_path}")

    # Ground Truth 로드 (검색 조건에 맞는 경우 항상 로드 시도)
    expected = None
    if args.validate or args.compare_all:
        try:
            expected = load_ground_truth_from_union_pdfs(args.base_path, args.period)
        except Exception as e:
            print(f"[Warning] Ground Truth 로드 실패: {e}")

    if args.compare_all:
        _compare_all_sources(args.base_path, args.period, expected)
        return

    if args.source == "quarterly_pdf":
        results = run_quarterly_pdf_pipeline(args.base_path, args.period)
        if expected:
            validate_results(results, expected)
        
        # 리포트 생성
        report_path = generate_excel_report(results, args.period, args.output)
        print(f"\n[리포트 생성 완료] {report_path}")

    elif args.source in ("pdf", "excel"):
        settlements = run_monthly_pipeline(args.base_path, args.period, args.source)
        if expected:
            validate_results(settlements, expected)
            
        # 리포트 생성
        report_path = generate_excel_report(settlements, args.period, args.output)
        print(f"\n[리포트 생성 완료] {report_path}")


def _compare_all_sources(base_path: str, period: str, expected: dict = None):
    """모든 소스로 계산하고 교차 비교"""
    print(f"\n{'='*70}")
    print(f"교차 비교: {period}")
    print(f"{'='*70}")

    results = {}

    # 1. Quarterly PDF
    try:
        r = run_quarterly_pdf_pipeline(base_path, period)
        results["quarterly_pdf"] = r
    except Exception as e:
        print(f"\n[quarterly_pdf] Error: {e}")

    # 2. Monthly PDF
    try:
        settlements = run_monthly_pipeline(base_path, period, "pdf")
        results["pdf"] = {cid: s.union_payout for cid, s in settlements.items()}
    except Exception as e:
        print(f"\n[pdf] Error: {e}")

    # 3. Excel
    try:
        settlements = run_monthly_pipeline(base_path, period, "excel")
        results["excel"] = {cid: s.union_payout for cid, s in settlements.items()}
    except Exception as e:
        print(f"\n[excel] Error: {e}")

    # 비교
    if len(results) > 1:
        print(f"\n{'='*70}")
        print(f"소스별 비교")
        print(f"{'='*70}")

        all_companies = set()
        for r in results.values():
            all_companies.update(r.keys())

        header = f"{'기업ID':<20}"
        for src in results:
            header += f" {src:>18}"
        print(header)
        print("-" * (20 + 19 * len(results)))

        for cid in sorted(all_companies):
            line = f"{cid:<20}"
            for src in results:
                val = results[src].get(cid, 0.0)
                line += f" {val:>18,.1f}"
            print(line)

    # 각 소스별 검증
    if expected:
        for src, r in results.items():
            print(f"\n--- {src} 검증 ---")
            validate_results(r, expected)


if __name__ == "__main__":
    main()
