#!/usr/bin/env python3
"""
companies.json 업데이트 스크립트
================================
모든 기업에 revenue_share_ratio, union_payout_ratio, payout_calculation 필드 추가
"""

import json
from pathlib import Path

# 프로젝트 루트 경로
BASE_PATH = Path(__file__).parent.parent

# companies.json 로드
companies_path = BASE_PATH / "data" / "companies.json"
with open(companies_path, "r", encoding="utf-8") as f:
    data = json.load(f)

# 기업별 수익쉐어 비율 설정
revenue_share_config = {
    "plusx": {
        "revenue_share_ratio": 0.65,
        "union_payout_ratio": 0.0,
        "payout_calculation": "full"  # 65% 전액 플엑 귀속
    },
    "designhouse": {
        "revenue_share_ratio": 0.60,
        "union_payout_ratio": 0.20,  # 공헌이익의 20% 지급
        "payout_calculation": "shared_20_40"  # 20% 지급, 40% 플엑
    },
    # 나머지 유니온 기업들
    "default_union": {
        "revenue_share_ratio": 0.75,
        "union_payout_ratio": 0.50,  # 공헌이익의 50% 지급
        "payout_calculation": "shared_50_25"  # 50% 지급, 25% 플엑
    }
}

# 각 기업에 필드 추가
for company in data["companies"]:
    company_id = company["company_id"]
    
    if company_id == "plusx":
        config = revenue_share_config["plusx"]
    elif company_id == "designhouse":
        config = revenue_share_config["designhouse"]
    else:
        # 유니온 기업
        config = revenue_share_config["default_union"]
    
    # 기존 필드가 없으면 추가
    if "revenue_share_ratio" not in company:
        company["revenue_share_ratio"] = config["revenue_share_ratio"]
    if "union_payout_ratio" not in company:
        company["union_payout_ratio"] = config["union_payout_ratio"]
    if "payout_calculation" not in company:
        company["payout_calculation"] = config["payout_calculation"]

# 저장
with open(companies_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"✅ companies.json 업데이트 완료")
print(f"   - 플러스엑스: 65% (전액 플엑)")
print(f"   - 디자인하우스: 60% (20% 지급, 40% 플엑)")
print(f"   - 유니온 기업: 75% (50% 지급, 25% 플엑)")
