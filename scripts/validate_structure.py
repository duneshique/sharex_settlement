#!/usr/bin/env python3
"""
프로젝트 구조 검증 스크립트
==========================
파일 재정리 후 구조가 올바른지 검증
"""

import sys
from pathlib import Path
from typing import List, Tuple

# 프로젝트 루트
BASE_PATH = Path(__file__).parent.parent

def check_file_exists(path: Path, description: str) -> Tuple[bool, str]:
    """파일 존재 여부 확인"""
    if path.exists():
        return True, f"✅ {description}: {path.name}"
    else:
        return False, f"❌ {description}: {path.name} (없음)"

def check_directory_exists(path: Path, description: str) -> Tuple[bool, str]:
    """디렉토리 존재 여부 확인"""
    if path.is_dir():
        file_count = len(list(path.iterdir()))
        return True, f"✅ {description}: {path.name}/ ({file_count}개 항목)"
    else:
        return False, f"❌ {description}: {path.name}/ (없음)"

def validate_structure() -> bool:
    """프로젝트 구조 검증"""
    
    print("=" * 60)
    print("ShareX Settlement - 프로젝트 구조 검증")
    print("=" * 60)
    
    all_passed = True
    
    # 1. 필수 디렉토리 확인
    print("\n📁 디렉토리 구조 확인")
    print("-" * 60)
    
    required_dirs = [
        (BASE_PATH / "src" / "models", "데이터 모델"),
        (BASE_PATH / "src" / "core", "핵심 로직"),
        (BASE_PATH / "src" / "parsers", "데이터 파서"),
        (BASE_PATH / "src" / "utils", "유틸리티"),
        (BASE_PATH / "scripts", "실행 스크립트"),
        (BASE_PATH / "tests", "테스트"),
        (BASE_PATH / "docs", "문서"),
        (BASE_PATH / "config", "설정"),
        (BASE_PATH / "data", "마스터 데이터"),
        (BASE_PATH / "output", "출력"),
        (BASE_PATH / "archive", "원본 데이터"),
        (BASE_PATH / "analysis", "분석 결과"),
    ]
    
    for path, desc in required_dirs:
        passed, msg = check_directory_exists(path, desc)
        print(msg)
        all_passed = all_passed and passed
    
    # 2. 모델 파일 확인
    print("\n🏗️  데이터 모델 파일 확인")
    print("-" * 60)
    
    model_files = [
        (BASE_PATH / "src" / "models" / "__init__.py", "모델 패키지"),
        (BASE_PATH / "src" / "models" / "company.py", "Company 모델"),
        (BASE_PATH / "src" / "models" / "course.py", "Course 모델"),
        (BASE_PATH / "src" / "models" / "campaign.py", "Campaign 모델"),
        (BASE_PATH / "src" / "models" / "validation.py", "Validation 모델"),
    ]
    
    for path, desc in model_files:
        passed, msg = check_file_exists(path, desc)
        print(msg)
        all_passed = all_passed and passed
    
    # 3. 핵심 파일 확인
    print("\n⚙️  핵심 파일 확인")
    print("-" * 60)
    
    core_files = [
        (BASE_PATH / "src" / "core" / "__init__.py", "Core 패키지"),
        (BASE_PATH / "src" / "core" / "apportionment.py", "안분 엔진"),
        (BASE_PATH / "data" / "companies.json", "기업 마스터"),
        (BASE_PATH / "data" / "course_mapping.json", "강의 매핑"),
        (BASE_PATH / "config" / "campaign_rules.json", "캠페인 규칙"),
    ]
    
    for path, desc in core_files:
        passed, msg = check_file_exists(path, desc)
        print(msg)
        all_passed = all_passed and passed
    
    # 4. 스크립트 파일 확인
    print("\n🔧 스크립트 파일 확인")
    print("-" * 60)
    
    script_files = [
        (BASE_PATH / "scripts" / "run_settlement.py", "정산 실행"),
        (BASE_PATH / "scripts" / "validation_phase0.py", "Phase 0 검증"),
        (BASE_PATH / "scripts" / "update_companies_ratios.py", "수익쉐어 비율 업데이트"),
    ]
    
    for path, desc in script_files:
        passed, msg = check_file_exists(path, desc)
        print(msg)
        all_passed = all_passed and passed
    
    # 5. 문서 파일 확인
    print("\n📝 문서 파일 확인")
    print("-" * 60)
    
    doc_files = [
        (BASE_PATH / "README.md", "프로젝트 README"),
        (BASE_PATH / ".gitignore", "Git 제외 설정"),
        (BASE_PATH / "docs" / "CLAUDE.md", "프로젝트 지침"),
    ]
    
    for path, desc in doc_files:
        passed, msg = check_file_exists(path, desc)
        print(msg)
        all_passed = all_passed and passed
    
    # 최종 결과
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ 모든 구조 검증 통과!")
        print("=" * 60)
        return True
    else:
        print("❌ 일부 검증 실패 - 위 내용을 확인하세요")
        print("=" * 60)
        return False

if __name__ == "__main__":
    success = validate_structure()
    sys.exit(0 if success else 1)
