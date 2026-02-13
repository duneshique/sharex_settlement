"""
Quarterly Settlement Consolidator
==================================
Consolidates 3 monthly settlement files into quarterly report.

Process:
1. Load 3 monthly settlement JSON files
2. Aggregate company-level data
3. Validate against quarterly PDF if available
4. Generate consolidated quarterly report
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime


class QuarterlyConsolidator:
    """Consolidate monthly settlements into quarterly report."""

    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)

    def consolidate_quarter(self, period: str, validation_pdf_path: str = None) -> Dict:
        """
        Consolidate quarterly settlement from monthly data.

        Args:
            period: Quarter identifier (e.g., "2025-Q4")
            validation_pdf_path: Optional path to quarterly PDF for validation

        Returns:
            Consolidated quarterly settlement data
        """
        print(f"\n{'='*80}")
        print(f"Consolidating Quarterly Settlement: {period}")
        print(f"{'='*80}")

        # Extract year and quarter
        year, quarter = period.split("-Q")
        months = self._get_quarter_months(int(quarter), int(year))

        print(f"\n[1/4] Loading monthly settlement files")
        print(f"  Expected months: {months}")

        monthly_files = self._find_monthly_files(period, months)
        if not monthly_files:
            print("[Error] Could not find all 3 monthly settlement files")
            return None

        print(f"  ✓ Found {len(monthly_files)} monthly files")
        for month, filepath in sorted(monthly_files.items()):
            print(f"    - {month}: {filepath.name}")

        # Load monthly data
        print(f"\n[2/4] Loading and aggregating monthly data")
        all_monthly_data = {}
        for month, filepath in sorted(monthly_files.items()):
            with open(filepath) as f:
                all_monthly_data[month] = json.load(f)

        # Aggregate by company
        print(f"\n[3/4] Aggregating company-level data across 3 months")
        consolidated = self._aggregate_companies(all_monthly_data)

        print(f"  ✓ Aggregated {len(consolidated)} companies")
        for company_id in sorted(consolidated.keys()):
            settlement = consolidated[company_id]['q4_totals']['q4_settlement']
            print(f"    - {company_id:<20} Q4 Settlement: {settlement:>12,.0f}")

        # Validation
        print(f"\n[4/4] Validation")
        if validation_pdf_path:
            validation_result = self._validate_against_pdf(consolidated, validation_pdf_path, period)
        else:
            print("  ⚠ No PDF provided for validation")
            validation_result = {}

        result = {
            "period": period,
            "consolidation_date": datetime.now().isoformat(),
            "monthly_files": list(sorted(all_monthly_data.keys())),
            "source_files": {month: str(filepath) for month, filepath in sorted(monthly_files.items())},
            "companies": consolidated,
            "validation": validation_result,
        }

        return result

    def _get_quarter_months(self, quarter: int, year: int) -> List[str]:
        """Get month identifiers for a quarter."""
        start_month = (quarter - 1) * 3 + 1
        return [f"{year:04d}-{m:02d}" for m in range(start_month, start_month + 3)]

    def _find_monthly_files(self, period: str, months: List[str]) -> Dict[str, Path]:
        """Find monthly settlement files."""
        quarter = period.split("-Q")[1]
        year = period.split("-")[0]
        output_dir = self.base_path / "output" / f"{year}-Q{quarter}"

        files = {}
        for month in months:
            filepath = output_dir / f"{month}_settlement.json"
            if filepath.exists():
                files[month] = filepath

        return files

    def _aggregate_companies(self, all_monthly_data: Dict) -> Dict:
        """Aggregate company data from all months."""
        # Collect all company IDs
        all_companies = set()
        for month_data in all_monthly_data.values():
            all_companies.update(month_data.get("companies", {}).keys())

        # Aggregate by company
        consolidated = {}
        for company_id in sorted(all_companies):
            monthly_records = []
            total_revenue = 0
            total_cost = 0
            total_contribution = 0
            total_settlement = 0

            for month in sorted(all_monthly_data.keys()):
                company_record = all_monthly_data[month].get("companies", {}).get(company_id)
                if company_record:
                    monthly_records.append({
                        "month": month,
                        "revenue": company_record.get("total_revenue", 0),
                        "cost": company_record.get("total_cost", 0),
                        "contribution": company_record.get("contribution_margin", 0),
                        "settlement": company_record.get("settlement_amount", 0),
                    })

                    total_revenue += company_record.get("total_revenue", 0)
                    total_cost += company_record.get("total_cost", 0)
                    total_contribution += company_record.get("contribution_margin", 0)
                    total_settlement += company_record.get("settlement_amount", 0)

            if monthly_records:
                consolidated[company_id] = {
                    "company_name": monthly_records[0] if isinstance(monthly_records[0], str)
                                    else all_monthly_data[list(all_monthly_data.keys())[0]]
                                        .get("companies", {}).get(company_id, {}).get("company_name", ""),
                    "monthly": monthly_records,
                    "q4_totals": {
                        "total_revenue": round(total_revenue, 2),
                        "total_cost": round(total_cost, 2),
                        "total_contribution": round(total_contribution, 2),
                        "q4_settlement": round(total_settlement, 2),
                    }
                }

        return consolidated

    def _validate_against_pdf(self, consolidated: Dict, pdf_path: str, period: str) -> Dict:
        """Validate consolidated data against PDF values."""
        from parsers.fastcampus_pdf import parse_quarterly_pdf
        from parsers.base import load_course_mapping

        try:
            # Parse quarterly PDF
            print(f"  → Parsing quarterly PDF for validation")
            parsed_data = parse_quarterly_pdf(pdf_path, period, str(self.base_path))

            if not parsed_data.settlement_rows:
                return {
                    "status": "error",
                    "note": "No settlement data found in quarterly PDF",
                    "expected_file": pdf_path,
                }

            # Load course mapping
            mapping = load_course_mapping(str(self.base_path))

            # Aggregate PDF data by company
            pdf_by_company = {}
            for row in parsed_data.settlement_rows:
                course = mapping.get(row.course_id, {})
                company_id = course.get("company_id", "plusx")

                if company_id not in pdf_by_company:
                    pdf_by_company[company_id] = 0

                pdf_by_company[company_id] += row.instructor_fee

            # Compare aggregated values
            validation_results = []
            mismatches = []

            for company_id in consolidated.keys():
                calculated_settlement = consolidated[company_id]['q4_totals']['q4_settlement']
                pdf_settlement = pdf_by_company.get(company_id, 0)

                diff = abs(calculated_settlement - pdf_settlement)
                diff_pct = (diff / pdf_settlement * 100) if pdf_settlement != 0 else 0

                validation_results.append({
                    "company_id": company_id,
                    "calculated": calculated_settlement,
                    "pdf_value": pdf_settlement,
                    "difference": diff,
                    "difference_pct": diff_pct,
                    "match": diff < 100  # Allow 100 KRW rounding difference
                })

                if diff >= 100:
                    mismatches.append({
                        "company_id": company_id,
                        "calculated": calculated_settlement,
                        "pdf_value": pdf_settlement,
                        "difference": diff
                    })

            # Summary
            total_validated = len(validation_results)
            total_matched = sum(1 for v in validation_results if v["match"])

            status = "passed" if len(mismatches) == 0 else "failed"

            print(f"  → Validated {total_validated} companies")
            print(f"  → Matched: {total_matched}/{total_validated}")

            if mismatches:
                print(f"  ⚠ Found {len(mismatches)} mismatches:")
                for m in mismatches[:5]:  # Show first 5
                    print(f"    - {m['company_id']}: calc={m['calculated']:,.0f}, pdf={m['pdf_value']:,.0f}, diff={m['difference']:,.0f}")

            return {
                "status": status,
                "validated_file": pdf_path,
                "total_companies": total_validated,
                "matched": total_matched,
                "mismatches": mismatches,
                "details": validation_results
            }

        except Exception as e:
            print(f"  ⚠ Validation error: {e}")
            import traceback
            traceback.print_exc()
            return {
                "status": "error",
                "note": str(e),
                "expected_file": pdf_path,
            }

    def save_consolidated_quarterly(self, consolidated_data: Dict, output_dir: str = None) -> Path:
        """Save consolidated quarterly settlement to JSON file."""
        if output_dir is None:
            period = consolidated_data["period"]
            output_dir = str(self.base_path / "output" / period)

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        filename = f"{consolidated_data['period']}_consolidated.json"
        filepath = output_path / filename

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(consolidated_data, f, ensure_ascii=False, indent=2)

        print(f"\n✓ Consolidated quarterly settlement saved: {filepath}")
        return filepath
