
import sys
from pathlib import Path

# 프로젝트 루트를 모듈 검색 경로에 추가
BASE_PATH = str(Path(__file__).parent.parent)
sys.path.insert(0, BASE_PATH)

from src.parsers.union_pdf import parse_union_settlement_pdf

def test_parser():
    file_path = "archive/Union_Profit Share_Settlement/쉐어엑스_ BKID 4Q 정산서.pdf"
    print(f"Testing parser on: {file_path}")
    try:
        result = parse_union_settlement_pdf(file_path)
        print("\n[Result]")
        for k, v in result.items():
            print(f"  {k}: {v}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_parser()
