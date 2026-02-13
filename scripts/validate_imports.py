#!/usr/bin/env python3
"""
Import 검증 스크립트
===================
새로운 모듈 구조에서 import가 정상 작동하는지 검증
"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
BASE_PATH = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_PATH))

def test_model_imports():
    """모델 import 테스트"""
    print("📦 모델 import 테스트...")
    
    try:
        from src.models.company import Company, CompanySettlement
        print("  ✅ Company, CompanySettlement")
    except ImportError as e:
        print(f"  ❌ Company 모델 import 실패: {e}")
        return False
    
    try:
        from src.models.course import Course, CourseSales
        print("  ✅ Course, CourseSales")
    except ImportError as e:
        print(f"  ❌ Course 모델 import 실패: {e}")
        return False
    
    try:
        from src.models.campaign import CampaignCost
        print("  ✅ CampaignCost")
    except ImportError as e:
        print(f"  ❌ Campaign 모델 import 실패: {e}")
        return False
    
    try:
        from src.models.validation import ValidationResult
        print("  ✅ ValidationResult")
    except ImportError as e:
        print(f"  ❌ Validation 모델 import 실패: {e}")
        return False
    
    return True

def test_core_imports():
    """핵심 엔진 import 테스트"""
    print("\n⚙️  핵심 엔진 import 테스트...")
    
    try:
        from src.core.apportionment import ApportionmentEngine
        print("  ✅ ApportionmentEngine")
    except ImportError as e:
        print(f"  ❌ ApportionmentEngine import 실패: {e}")
        return False
    
    return True

def test_model_instantiation():
    """모델 인스턴스 생성 테스트"""
    print("\n🏗️  모델 인스턴스 생성 테스트...")
    
    try:
        from src.models.company import Company, CompanySettlement
        
        # Company 인스턴스 생성
        company = Company(
            company_id="test",
            name="테스트 기업",
            type="유니온",
            revenue_share_ratio=0.75,
            union_payout_ratio=0.50,
            payout_calculation="shared_50_25"
        )
        print(f"  ✅ Company 인스턴스: {company.name}")
        
        # CompanySettlement 인스턴스 생성
        settlement = CompanySettlement(
            company_id="test",
            company_name="테스트 기업",
            period="2024-Q4"
        )
        print(f"  ✅ CompanySettlement 인스턴스: {settlement.period}")
        
    except Exception as e:
        print(f"  ❌ 모델 인스턴스 생성 실패: {e}")
        return False
    
    return True

def test_data_loading():
    """데이터 파일 로딩 테스트"""
    print("\n📊 데이터 파일 로딩 테스트...")
    
    import json
    
    # companies.json 로딩
    try:
        companies_path = BASE_PATH / "data" / "companies.json"
        with open(companies_path, "r", encoding="utf-8") as f:
            companies_data = json.load(f)
        
        company_count = len(companies_data.get("companies", []))
        print(f"  ✅ companies.json: {company_count}개 기업")
        
        # revenue_share_ratio 필드 확인
        first_company = companies_data["companies"][0]
        if "revenue_share_ratio" in first_company:
            print(f"  ✅ revenue_share_ratio 필드 존재")
        else:
            print(f"  ❌ revenue_share_ratio 필드 없음")
            return False
            
    except Exception as e:
        print(f"  ❌ companies.json 로딩 실패: {e}")
        return False
    
    # course_mapping.json 로딩
    try:
        courses_path = BASE_PATH / "data" / "course_mapping.json"
        with open(courses_path, "r", encoding="utf-8") as f:
            courses_data = json.load(f)
        
        course_count = len(courses_data.get("courses", []))
        print(f"  ✅ course_mapping.json: {course_count}개 강의")
        
    except Exception as e:
        print(f"  ❌ course_mapping.json 로딩 실패: {e}")
        return False
    
    return True

def main():
    """메인 검증 함수"""
    print("=" * 60)
    print("ShareX Settlement - Import 검증")
    print("=" * 60)
    
    all_passed = True
    
    # 각 테스트 실행
    all_passed = test_model_imports() and all_passed
    all_passed = test_core_imports() and all_passed
    all_passed = test_model_instantiation() and all_passed
    all_passed = test_data_loading() and all_passed
    
    # 최종 결과
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ 모든 import 검증 통과!")
        print("=" * 60)
        return True
    else:
        print("❌ 일부 검증 실패 - 위 내용을 확인하세요")
        print("=" * 60)
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
