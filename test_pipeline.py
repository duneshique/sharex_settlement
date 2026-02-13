#!/usr/bin/env python3
"""
Test the end-to-end settlement processing pipeline.

Tests:
1. Monthly PDF processing (October, November, December 2025)
2. Monthly settlement JSON generation
3. Quarterly consolidation from 3 monthly files
4. Validation of quarterly output
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.monthly_processor import MonthlyProcessor
from core.quarterly_consolidator import QuarterlyConsolidator


def test_monthly_processing():
    """Test processing of monthly FastCampus PDFs."""
    print("\n" + "="*80)
    print("PHASE 1: MONTHLY PDF PROCESSING TEST")
    print("="*80)

    base_path = Path(__file__).parent
    processor = MonthlyProcessor(str(base_path))

    # Q4 2025 monthly PDFs
    monthly_pdfs = [
        ("2025-10", "archive/FastCampus_Settlement/[패스트캠퍼스] Share X 정산서 - 2025년 10월.pdf"),
        ("2025-11", "archive/FastCampus_Settlement/[패스트캠퍼스] Share X 정산서 - 2025년 11월.pdf"),
        ("2025-12", "archive/FastCampus_Settlement/[패스트캠퍼스] Share X 정산서 - 2025년 12월.pdf"),
    ]

    monthly_files = {}
    for month, pdf_rel_path in monthly_pdfs:
        pdf_path = base_path / pdf_rel_path

        if not pdf_path.exists():
            print(f"[Warning] PDF not found: {pdf_path}")
            continue

        print(f"\n→ Processing {month}: {pdf_path.name}")
        try:
            settlement_data = processor.process_monthly_pdf(str(pdf_path), month)
            if settlement_data:
                output_file = processor.save_monthly_settlement(settlement_data)
                monthly_files[month] = output_file
                print(f"  ✓ Successfully saved monthly settlement")
            else:
                print(f"  ✗ Failed to process PDF")
        except Exception as e:
            print(f"  ✗ Error processing PDF: {e}")
            import traceback
            traceback.print_exc()

    return monthly_files


def test_quarterly_consolidation(monthly_files):
    """Test consolidation of 3 monthly files into quarterly report."""
    print("\n" + "="*80)
    print("PHASE 2: QUARTERLY CONSOLIDATION TEST")
    print("="*80)

    if len(monthly_files) < 3:
        print(f"[Error] Need 3 monthly files for quarterly consolidation, got {len(monthly_files)}")
        return None

    base_path = Path(__file__).parent
    consolidator = QuarterlyConsolidator(str(base_path))

    quarterly_pdf = "archive/FastCampus_Settlement/[패스트캠퍼스] Share X 정산서 - 2025년 4분기.pdf"
    quarterly_pdf_path = str(base_path / quarterly_pdf) if (base_path / quarterly_pdf).exists() else None

    print(f"\n→ Consolidating 2025-Q4 from {len(monthly_files)} monthly files")

    try:
        consolidated_data = consolidator.consolidate_quarter(
            "2025-Q4",
            validation_pdf_path=quarterly_pdf_path
        )

        if consolidated_data:
            output_file = consolidator.save_consolidated_quarterly(consolidated_data)
            print(f"  ✓ Successfully saved quarterly consolidation")
            return consolidated_data
        else:
            print(f"  ✗ Failed to consolidate")
            return None
    except Exception as e:
        print(f"  ✗ Error consolidating: {e}")
        import traceback
        traceback.print_exc()
        return None


def print_summary(consolidated_data):
    """Print summary of consolidated quarterly data."""
    if not consolidated_data:
        return

    print("\n" + "="*80)
    print("QUARTERLY CONSOLIDATION SUMMARY")
    print("="*80)

    print(f"\nPeriod: {consolidated_data['period']}")
    print(f"Consolidation Date: {consolidated_data['consolidation_date']}")
    print(f"Monthly Files: {', '.join(consolidated_data['monthly_files'])}")

    companies = consolidated_data.get('companies', {})
    print(f"\nCompanies ({len(companies)}):")
    print(f"{'Company ID':<20} {'Company Name':<20} {'Q4 Settlement':>15}")
    print("-" * 57)

    total_settlement = 0
    for company_id in sorted(companies.keys()):
        company_data = companies[company_id]
        settlement = company_data.get('q4_totals', {}).get('q4_settlement', 0)
        company_name = company_data.get('company_name', 'Unknown')[:18]
        print(f"{company_id:<20} {company_name:<20} {settlement:>15,.0f}")
        total_settlement += settlement

    print("-" * 57)
    print(f"{'TOTAL':<20} {'':<20} {total_settlement:>15,.0f}")

    print(f"\nValidation Status: {consolidated_data.get('validation', {}).get('status', 'unknown')}")


def main():
    """Run the full test pipeline."""
    print("\n" + "="*80)
    print("SHAREX SETTLEMENT PROCESSING PIPELINE TEST")
    print("="*80)
    print("\nTesting the end-to-end process:")
    print("1. Load 3 monthly FastCampus PDFs (Oct, Nov, Dec 2025)")
    print("2. Generate monthly settlement JSON files")
    print("3. Consolidate 3 monthly files into quarterly report")
    print("4. Validate quarterly output")

    # Phase 1: Monthly PDF processing
    monthly_files = test_monthly_processing()

    if not monthly_files:
        print("\n[Error] No monthly files processed. Cannot proceed to consolidation.")
        return 1

    # Phase 2: Quarterly consolidation
    consolidated_data = test_quarterly_consolidation(monthly_files)

    # Print summary
    if consolidated_data:
        print_summary(consolidated_data)
        print("\n" + "="*80)
        print("✓ PIPELINE TEST COMPLETED SUCCESSFULLY")
        print("="*80)
        return 0
    else:
        print("\n" + "="*80)
        print("✗ PIPELINE TEST FAILED")
        print("="*80)
        return 1


if __name__ == "__main__":
    sys.exit(main())
