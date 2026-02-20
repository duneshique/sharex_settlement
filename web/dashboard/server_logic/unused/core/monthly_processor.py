"""
Monthly PDF Settlement Processor
================================
Processes monthly FastCampus PDFs and generates company-level settlement data.

Process:
1. Parse monthly PDF → Extract course-level data
2. Classify courses by company → Using course_mapping.json
3. Apply settlement ratios → Using companies.json
4. Save monthly settlement JSON
"""

import json
from pathlib import Path
from typing import Dict, List
from datetime import datetime

from parsers.fastcampus_pdf import parse_monthly_pdf
from parsers.base import load_course_mapping
from models.company import Company


class MonthlyProcessor:
    """Process monthly PDF and generate settlement data per company."""

    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        self.course_mapping = load_course_mapping(base_path)
        self.companies = self._load_companies()
        self.campaign_rules = self._load_campaign_rules()

    def _load_companies(self) -> Dict[str, Company]:
        """Load companies configuration."""
        companies_path = self.base_path / "data" / "companies.json"
        with open(companies_path) as f:
            data = json.load(f)

        companies = {}
        for c in data["companies"]:
            company = Company(**{k: v for k, v in c.items() if k in Company.__dataclass_fields__})
            companies[company.company_id] = company
        return companies

    def _load_campaign_rules(self) -> Dict:
        """Load campaign classification rules."""
        rules_path = self.base_path / "config" / "campaign_rules.json"
        if not rules_path.exists():
            return {"classification_rules": {"target_mapping": {}}}

        with open(rules_path) as f:
            return json.load(f)

    def classify_campaign(self, campaign_name: str, target: str = "") -> Dict:
        """
        Classify campaign as direct or indirect cost.

        Args:
            campaign_name: Campaign name
            target: Campaign target (e.g., "SHARE X", "BKID")

        Returns:
            {
                "type": "direct" or "indirect",
                "target": target name,
                "company_id": company_id or None
            }
        """
        target_mapping = self.campaign_rules.get("classification_rules", {}).get("target_mapping", {})

        # 1. Check target field first
        if target and target in target_mapping:
            rule = target_mapping[target]
            return {
                "type": rule["type"],
                "target": target,
                "company_id": rule.get("company_id")
            }

        # 2. Pattern matching on campaign name
        direct_targets = {k: v for k, v in target_mapping.items() if v["type"] == "direct"}
        for target_name, rule in direct_targets.items():
            company_id = rule.get("company_id", "")
            # Simple keyword matching
            if company_id and company_id.upper() in campaign_name.upper():
                return {
                    "type": "direct",
                    "target": target_name,
                    "company_id": company_id
                }

        # 3. Default to indirect
        return {
            "type": "indirect",
            "target": "SHARE X",
            "company_id": None
        }

    def process_monthly_pdf(self, pdf_path: str, month: str) -> Dict:
        """
        Process a single monthly PDF and generate settlement data.

        Args:
            pdf_path: Path to FastCampus monthly PDF
            month: Month identifier (e.g., "2025-10")

        Returns:
            Settlement data dict with company-level aggregation
        """
        print(f"\n{'='*80}")
        print(f"Processing Monthly PDF: {month}")
        print(f"{'='*80}")

        # Parse PDF
        print(f"\n[1/3] Parsing PDF: {Path(pdf_path).name}")
        parsed_data = parse_monthly_pdf(pdf_path, month, str(self.base_path))

        if not parsed_data.course_sales:
            print("[Warning] No course sales data found in PDF")
            return self._create_empty_settlement(month)

        print(f"  ✓ Extracted {len(parsed_data.course_sales)} course sales records")
        print(f"  ✓ Extracted {len(parsed_data.campaign_costs)} campaign cost records")

        # Classify and aggregate by company
        print(f"\n[2/3] Classifying courses and aggregating by company")
        company_data = self._aggregate_by_company(parsed_data.course_sales, parsed_data.campaign_costs)

        print(f"  ✓ Classified {len(company_data)} companies")
        for company_id in sorted(company_data.keys()):
            print(f"    - {company_id:<20} Revenue: {company_data[company_id]['total_revenue']:>12,}")

        # Apply settlement ratios
        print(f"\n[3/3] Applying settlement ratios")
        settlement_result = self._apply_settlement_ratios(company_data)

        print(f"  ✓ Settlement amounts calculated")
        for company_id in sorted(settlement_result.keys()):
            print(f"    - {company_id:<20} Settlement: {settlement_result[company_id]['settlement_amount']:>12,.0f}")

        return {
            "period": month,
            "extraction_date": datetime.now().isoformat(),
            "source_file": Path(pdf_path).name,
            "companies": settlement_result,
        }

    def _aggregate_by_company(self, course_sales: List, campaign_costs: List) -> Dict:
        """Aggregate course sales and costs by company."""
        company_data = {}

        # Initialize all companies
        for company_id in self.companies.keys():
            company_data[company_id] = {
                "company_name": self.companies[company_id].name,
                "total_revenue": 0,
                "total_cost": 0,
                "courses": []
            }

        # Aggregate course sales by company
        for sale in course_sales:
            course_info = self.course_mapping.get(sale.course_id, {})
            company_id = course_info.get("company_id", "plusx")

            if company_id in company_data:
                company_data[company_id]["total_revenue"] += sale.revenue
                company_data[company_id]["courses"].append({
                    "course_id": sale.course_id,
                    "course_name": sale.course_name,
                    "revenue": sale.revenue,
                })

        # Classify and aggregate campaign costs
        direct_costs_by_company = {}
        total_indirect_cost = 0

        for cost in campaign_costs:
            classification = self.classify_campaign(cost.campaign_name, cost.target)

            if classification["type"] == "direct":
                company_id = classification["company_id"]
                if company_id:
                    direct_costs_by_company[company_id] = direct_costs_by_company.get(company_id, 0) + cost.cost_krw
            else:
                # Indirect cost
                total_indirect_cost += cost.cost_krw

        # Calculate total active courses
        total_courses = sum(len(company_data[c]["courses"]) for c in company_data if company_data[c]["total_revenue"] > 0)

        # Distribute indirect costs evenly across all active courses
        indirect_per_course = total_indirect_cost / total_courses if total_courses > 0 else 0

        # Assign costs to each company
        for company_id in company_data:
            # Direct cost for this company
            direct_cost = direct_costs_by_company.get(company_id, 0)

            # Indirect cost based on course count
            course_count = len(company_data[company_id]["courses"])
            indirect_cost = indirect_per_course * course_count

            # Total cost
            company_data[company_id]["total_cost"] = direct_cost + indirect_cost

        return company_data

    def _apply_settlement_ratios(self, company_data: Dict) -> Dict:
        """Apply settlement ratios from companies.json."""
        result = {}

        for company_id, data in company_data.items():
            company = self.companies[company_id]

            contribution = data["total_revenue"] - data["total_cost"]

            # Apply settlement ratio
            settlement_amount = contribution * company.union_payout_ratio

            result[company_id] = {
                "company_name": data["company_name"],
                "total_revenue": round(data["total_revenue"], 2),
                "total_cost": round(data["total_cost"], 2),
                "contribution_margin": round(contribution, 2),
                "revenue_share_ratio": company.revenue_share_ratio,
                "union_payout_ratio": company.union_payout_ratio,
                "settlement_amount": round(settlement_amount, 2),
                "course_count": len(data["courses"]),
            }

        return result

    def _create_empty_settlement(self, month: str) -> Dict:
        """Create empty settlement structure for month with no data."""
        return {
            "period": month,
            "extraction_date": datetime.now().isoformat(),
            "companies": {},
        }

    def save_monthly_settlement(self, settlement_data: Dict, output_dir: str = None) -> Path:
        """Save monthly settlement to JSON file."""
        if output_dir is None:
            period = settlement_data["period"]
            year = period[:4]
            month = int(period[5:7])
            quarter_num = (month - 1) // 3 + 1
            quarter = f"{year}-Q{quarter_num}"
            output_dir = str(self.base_path / "output" / quarter)

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        filename = f"{settlement_data['period']}_settlement.json"
        filepath = output_path / filename

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(settlement_data, f, ensure_ascii=False, indent=2)

        print(f"\n✓ Settlement data saved: {filepath}")
        return filepath
