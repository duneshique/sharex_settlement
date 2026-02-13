import pandas as pd
from pathlib import Path
from typing import Dict
from datetime import datetime
from ..models.company import CompanySettlement

def generate_excel_report(
    results: Dict[str, CompanySettlement],
    period: str,
    output_dir: str = "output"
) -> str:
    """
    정산 결과를 엑셀 리포트로 생성합니다.
    """
    output_path = Path(output_dir) / period
    output_path.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"ShareX_Settlement_Report_{period}_{timestamp}.xlsx"
    file_path = output_path / file_name
    
    # 1. Summary DataFrame 생성
    summary_data = []
    for cid, s in results.items():
        summary_data.append({
            "기업ID": cid,
            "기업명": s.company_name,
            "매출액": s.total_revenue,
            "직접광고비": s.direct_ad_cost,
            "간접광고비": s.indirect_ad_cost,
            "총광고비": s.total_ad_cost,
            "공헌이익": s.contribution_margin,
            "수익쉐어비율": f"{s.revenue_share_ratio * 100:.1f}%",
            "강사료(RS)": s.revenue_share_fee,
            "지급비율": f"{s.union_payout_ratio * 100:.1f}%",
            "실지급액": s.union_payout,
            "강의수": s.course_count
        })
    
    df_summary = pd.DataFrame(summary_data)
    
    # 2. 엑셀 파일 작성
    with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
        # 요약 시트
        df_summary.to_excel(writer, sheet_name="Summary", index=False)
        
        # 기업별 상세 시트
        for cid, s in results.items():
            if s.course_revenues:
                # 강의별 상세 데이터 구성
                detail_data = []
                for course_id, revenue in s.course_revenues.items():
                    # 간접광고비는 강의수대로 균등 안분된 값 사용
                    detail_data.append({
                        "강의ID": course_id,
                        "매출액": revenue,
                        "간접광고비(안분)": s.indirect_ad_per_course
                    })
                
                df_detail = pd.DataFrame(detail_data)
                # 시트 이름은 기업명으로 (최대 31자 제한)
                sheet_name = s.company_name[:31]
                df_detail.to_excel(writer, sheet_name=sheet_name, index=False)
                
    return str(file_path)
