#!/usr/bin/env python3
"""
정산 PDF 파서 진단 스크립트
- 실제 PDF에서 추출된 강의 목록
- mapping.json에서 찾을 수 있는 강의 목록
- 차이 분석
"""

import sys
import json
from pathlib import Path
import pdfplumber

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.parsers.base import load_course_mapping
from src.parsers.unified_pdf_parser import parse_settlement_pdf_unified

def extract_course_names_from_pdf(pdf_path: str) -> set:
    """PDF에서 강의명 추출 (임시ID 제외, 실제 이름만)"""
    courses = set()
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            lines = text.split("\n")
            for line in lines:
                # 패턴: 2510_[쉐어엑스]강의명 ...
                if "_[쉐어엑스]" in line or "_[Shared" in line:
                    # 강의명 부분 추출 (대략적)
                    parts = line.split()
                    if len(parts) > 1:
                        # 첫 번째 파트는 코스ID_강의명의 일부
                        course_part = parts[0]
                        if "_" in course_part:
                            # 2510_강의명 형식
                            _, name_start = course_part.split("_", 1)
                            # 전체 강의명 재구성 (다음 파트들을 보며 숫자가 나올때까지)
                            full_name = course_part
                            for i, part in enumerate(parts[1:], 1):
                                # 숫자가 나오면 멈추기
                                if any(c.isdigit() for c in part) and "," in part:
                                    break
                                full_name += " " + part
                            courses.add(full_name)
    return courses

def get_courses_from_mapping(base_path: str) -> dict:
    """mapping.json에서 강의 정보 조회"""
    mapping = load_course_mapping(base_path)
    courses = {}
    for course_id, course_info in mapping.items():
        course_name = course_info.get("course_name", "")
        company_id = course_info.get("company_id", "")
        courses[course_name] = {
            "course_id": course_id,
            "company_id": company_id
        }
    return courses

def main():
    base_path = "/Users/plusx-junsikhwang/Documents/GitHub/ShareX_Settlement"
    pdf_path = f"{base_path}/archive/FastCampus_Settlement/[패스트캠퍼스] Share X 정산서 - 2024년 4Q.pdf"

    print("=" * 80)
    print("📊 정산 PDF 파서 진단")
    print("=" * 80)

    # Step 1: 통합 파서로 추출된 결과
    print("\n[Step 1] 통합 파서 실행...")
    try:
        result = parse_settlement_pdf_unified(pdf_path, "2024-Q4", base_path)
        parsed_courses = result.settlement_rows
        print(f"✅ 추출된 강의: {len(parsed_courses)}개")

        # 코스별 분포
        course_ids = set(row.course_id for row in parsed_courses)
        print(f"   고유 코스ID: {len(course_ids)}개")
        print(f"   임시ID (XX00 형식): {len([c for c in course_ids if c.endswith('0')])}")

        # 샘플 출력
        print("\n   첫 10개 강의:")
        for i, row in enumerate(parsed_courses[:10], 1):
            print(f"     {i}. {row.course_id}: {row.course_name}")

    except Exception as e:
        print(f"❌ 파서 실행 실패: {e}")
        parsed_courses = []

    # Step 2: PDF에서 직접 추출한 강의명
    print("\n[Step 2] PDF 텍스트에서 강의명 직접 추출...")
    pdf_course_names = extract_course_names_from_pdf(pdf_path)
    print(f"✅ 추출된 강의명 (원본): {len(pdf_course_names)}개")

    # 샘플 출력
    print("\n   첫 10개:")
    for i, name in enumerate(sorted(pdf_course_names)[:10], 1):
        print(f"     {i}. {name}")

    # Step 3: mapping에서 조회 가능한 강의
    print("\n[Step 3] course_mapping.json 조회...")
    mapping_courses = get_courses_from_mapping(base_path)
    print(f"✅ Mapping에 있는 강의: {len(mapping_courses)}개")

    # 샘플 출력
    print("\n   첫 10개:")
    for i, (name, info) in enumerate(sorted(mapping_courses.items())[:10], 1):
        print(f"     {i}. {name[:50]}... (ID: {info['course_id']})")

    # Step 4: 분석
    print("\n[Step 4] 분석 결과")
    print("-" * 80)

    parsed_course_names = set(row.course_name for row in parsed_courses)

    # 파서가 찾은 것 중 매핑에 없는 것
    not_in_mapping = parsed_course_names - set(mapping_courses.keys())
    if not_in_mapping:
        print(f"\n⚠️  파서가 찾았으나 매핑에 없는 강의: {len(not_in_mapping)}개")
        for name in sorted(not_in_mapping)[:5]:
            print(f"   - {name[:60]}")
        if len(not_in_mapping) > 5:
            print(f"   ... 외 {len(not_in_mapping) - 5}개")

    # PDF에는 있으나 파서가 못 찾은 것
    not_parsed = pdf_course_names - parsed_course_names
    if not_parsed:
        print(f"\n⚠️  PDF에는 있으나 파서가 못 찾은 강의명: {len(not_parsed)}개")
        for name in sorted(not_parsed)[:5]:
            print(f"   - {name[:60]}")
        if len(not_parsed) > 5:
            print(f"   ... 외 {len(not_parsed) - 5}개")

    # 파서의 임시ID 문제
    temp_ids = [row.course_id for row in parsed_courses if row.course_id.endswith('0')]
    if temp_ids:
        print(f"\n⚠️  임시ID로 처리된 강의: {len(set(temp_ids))}개")
        print(f"   이들은 course_name 매칭 실패로 YYYYMM0 형식으로 처리됨")

        # 임시ID별 강의명 샘플
        for temp_id in sorted(set(temp_ids))[:3]:
            names = [row.course_name for row in parsed_courses if row.course_id == temp_id]
            print(f"   - {temp_id}: {len(names)}개 강의")
            for name in names[:2]:
                print(f"     · {name[:50]}")

    print("\n" + "=" * 80)
    print("📋 권장 조치:")
    print("-" * 80)
    print("1. course_name 매칭 방식 개선 (부분 일치, 정규화 등)")
    print("2. PDF에서 코스ID 직접 추출 메커니즘 확인")
    print("3. 월별 강의가 분기 매핑에 없는지 확인")

if __name__ == "__main__":
    main()
