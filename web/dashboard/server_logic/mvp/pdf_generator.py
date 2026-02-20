"""
MVP Step 3: 기업별 정산서 PDF 생성

레퍼런스 정산서 레이아웃 기반:
- 제목: [ 기업명 ] YYYY년 N분기 정산서
- 좌측 플러스엑스 / 우측 거래상대방 정보
- 요약: 총매출액 | 마케팅비+제작비 | 공헌이익 | 수익쉐어 강사료
- 월별 breakdown 상세 테이블 (정산월 | 강의명 | 매출액 | 마케팅비 | 제작비 | 공헌이익 | 강사료)
- 기업별 동적 강사료 비율 (companies.json의 union_payout_ratio)
"""

import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

try:
    from weasyprint import HTML, CSS
except ImportError:
    print("weasyprint가 설치되지 않았습니다: pip install weasyprint")
    HTML = None


ISSUER_INFO = {
    "name": "플러스엑스 주식회사",
    "biz_number": "211-88-46851",
    "representative": "유상원, 이재훈",
    "address": "서울시 강남구 언주로 149길 17, 4-5F",
    "bank": "우리은행",
    "account": "1005-980-100727",
    "contact": "finance@plus-ex.com"
}


def generate_settlement_pdf(
    company_id: str,
    settlement_data: Dict[str, Any],
    output_path: str,
    company_info: Dict[str, Any] = None,
) -> str:
    if HTML is None:
        raise RuntimeError("weasyprint를 설치하세요: pip install weasyprint")

    if company_info is None:
        company_info = {}

    html_content = _generate_html_template(
        company_id=company_id,
        settlement=settlement_data,
        company_info=company_info,
    )

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        HTML(string=html_content).write_pdf(str(output_file))
        return str(output_file)
    except Exception as e:
        print(f"PDF 생성 실패: {e}")
        raise


def _generate_html_template(
    company_id: str,
    settlement: Dict[str, Any],
    company_info: Dict[str, Any],
) -> str:
    # 기본 정보 추출
    company_name = settlement.get("company_name", company_id)
    period = settlement.get("period", "")
    receiver_name = company_info.get("name", company_name)

    # 기간 파싱
    year_num, q_num = _parse_period_parts(period)
    today = datetime.now().strftime("%Y.%m.%d")

    # 수신 회사 정보
    receiver_biz = company_info.get("biz_number", "")
    receiver_rep = company_info.get("representative", "")
    receiver_address = company_info.get("address", "")
    receiver_bank = company_info.get("bank", "")
    receiver_account = company_info.get("account", "")
    receiver_contact = company_info.get("contact_name", "")
    receiver_email = company_info.get("contact_email", "")

    # 정산 수치
    revenue = settlement.get("revenue", 0)
    ad_cost = settlement.get("ad_cost", 0)
    contribution = settlement.get("contribution", 0)
    settlement_amount = settlement.get("settlement_amount", 0)
    payout_ratio = settlement.get("union_payout_ratio", 0.5)
    ratio_percent = int(payout_ratio * 100)

    # 강의별 상세 내역 HTML
    courses_html = _build_courses_table_rows(
        settlement=settlement,
        company_id=company_id,
        period=period,
        payout_ratio=payout_ratio,
        total_revenue=revenue,
        total_ad_cost=ad_cost,
    )

    # 합계 행
    totals_html = f"""
    <tr style="background-color: #f5f5f5; font-weight: bold;">
        <td style="text-align: center;">합계</td>
        <td></td>
        <td style="text-align: right;">{revenue:,.0f}</td>
        <td style="text-align: right;">{ad_cost:,.0f}</td>
        <td style="text-align: right;"></td>
        <td style="text-align: right;">{contribution:,.0f}</td>
        <td style="text-align: right;">{settlement_amount:,.0f}</td>
    </tr>
    """

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
    @page {{
        size: A4;
        margin: 18mm 15mm 15mm 15mm;
    }}
    * {{
        font-family: 'Noto Sans CJK KR', 'Noto Sans', -apple-system, 'Apple SD Gothic Neo', sans-serif;
        box-sizing: border-box;
    }}
    body {{
        margin: 0; padding: 0;
        font-size: 9pt; line-height: 1.5; color: #1a1a1a;
    }}

    /* 제목 영역 */
    .title-area {{
        display: flex; justify-content: space-between; align-items: flex-start;
        margin-bottom: 16px; padding-bottom: 8px;
        border-bottom: 2px solid #000;
    }}
    .title-area h1 {{
        margin: 0; font-size: 15pt; font-weight: bold;
    }}
    .title-area .date {{
        font-size: 9pt; color: #333; white-space: nowrap;
    }}

    /* 회사 정보 */
    .company-row {{
        display: flex; gap: 16px; margin-bottom: 14px; font-size: 8.5pt;
    }}
    .company-col {{
        flex: 1; line-height: 1.6;
    }}
    .company-col .name {{
        font-weight: bold; font-size: 9.5pt; margin-bottom: 2px;
    }}
    .company-col p {{
        margin: 1px 0;
    }}

    /* 요약 테이블 */
    .summary {{
        width: 100%; border-collapse: collapse; margin-bottom: 12px;
    }}
    .summary td {{
        border: 1px solid #ccc; padding: 6px 8px; font-size: 9pt;
    }}
    .summary .lbl {{
        background: #f0f0f0; font-weight: bold; text-align: center; width: 18%;
    }}
    .summary .val {{
        text-align: right; width: 32%;
    }}

    /* 상세 테이블 */
    .detail {{
        width: 100%; border-collapse: collapse; font-size: 8pt; margin-bottom: 10px;
    }}
    .detail th {{
        background: #333; color: #fff; padding: 5px 4px;
        text-align: center; border: 1px solid #333; font-weight: bold; font-size: 7.5pt;
    }}
    .detail td {{
        padding: 4px; border: 1px solid #ddd; font-size: 8pt;
    }}
    .detail td.month-cell {{
        text-align: center; vertical-align: middle; font-weight: bold;
        background: #fafafa;
    }}
    .detail td.name-cell {{
        text-align: left; padding-left: 6px;
    }}
    .detail td.num {{
        text-align: right;
    }}

    /* 안내사항 */
    .note {{
        font-size: 7.5pt; color: #555; margin-top: 10px; line-height: 1.5;
    }}
    .note p {{ margin: 1px 0; }}
    .note strong {{ color: #333; }}
</style>
</head>
<body>
    <!-- 제목 -->
    <div class="title-area">
        <h1>[ {receiver_name} ] {year_num}년 {q_num}분기 정산서</h1>
        <span class="date">[{today}]</span>
    </div>

    <!-- 회사 정보 (라벨 없이 나란히) -->
    <div class="company-row">
        <div class="company-col">
            <p class="name">{ISSUER_INFO['name']}</p>
            <p>사업자번호 {ISSUER_INFO['biz_number']}</p>
            <p>주소 {ISSUER_INFO['address']}</p>
            <p>대표이사 {ISSUER_INFO['representative']}</p>
            <p>계좌번호 {ISSUER_INFO['bank']}/{ISSUER_INFO['account']}</p>
            <p>담당자 {ISSUER_INFO['contact']}</p>
        </div>
        <div class="company-col">
            <p class="name">{receiver_name}</p>
            <p>사업자번호 {receiver_biz}</p>
            <p>주소 {receiver_address}</p>
            <p>대표이사 {receiver_rep}</p>
            <p>계좌번호 {receiver_bank}/{receiver_account}</p>
            <p>담당자 {receiver_contact or receiver_email}</p>
        </div>
    </div>

    <!-- 요약 -->
    <table class="summary">
        <tr>
            <td class="lbl">총 매출액</td>
            <td class="val">{revenue:,.0f}</td>
            <td class="lbl">마케팅비+제작비</td>
            <td class="val">{ad_cost:,.0f}</td>
        </tr>
        <tr>
            <td class="lbl">공헌이익</td>
            <td class="val">{contribution:,.0f}</td>
            <td class="lbl">수익쉐어 강사료</td>
            <td class="val" style="font-weight:bold; background:#fff8e1;">{settlement_amount:,.0f}</td>
        </tr>
    </table>

    <!-- 상세 테이블 -->
    <table class="detail">
        <thead>
            <tr>
                <th style="width:9%;">정산월</th>
                <th style="width:28%;">강의명</th>
                <th style="width:12%;">매출액</th>
                <th style="width:12%;">마케팅비</th>
                <th style="width:9%;">제작비</th>
                <th style="width:14%;">공헌이익</th>
                <th style="width:16%;">수익쉐어 강사료<br>(공헌이익x{ratio_percent}%)</th>
            </tr>
        </thead>
        <tbody>
            {courses_html}
            {totals_html}
        </tbody>
    </table>

    <!-- 안내사항 -->
    <div class="note">
        <p><strong>[참고사항]</strong></p>
        <p><strong>[B2C]</strong></p>
        <p style="margin-left:8px;">*매출액 = 결제금액 - 환불액</p>
        <p style="margin-left:8px;">*공헌이익 = 매출액 - 제작비 - 마케팅비용</p>
        <p style="margin-left:8px;">*수익쉐어 강사료 = 공헌이익 x {ratio_percent}%</p>
        <p style="margin-left:8px;">*마케팅비용의 세부내역은 별도 첨부파일에서 확인 가능합니다.</p>
        <p style="margin-top:4px;"><strong>[기타 참고사항]</strong></p>
        <p style="margin-left:8px;">*정산서상 모든금액은 부가세포함 금액입니다.</p>
        <p style="margin-left:8px;">*수익쉐어 강사료는 세금계산서 발행 후 15일이내 입금됩니다.</p>
        <p style="margin-left:8px;">*세금계산서 수신이메일: finance@plus-ex.com</p>
    </div>
</body>
</html>"""
    return html


def _parse_period_parts(period: str) -> tuple:
    """'2024-Q4' → ('2024', '4')"""
    if not period or "-Q" not in period:
        return ("N/A", "N/A")
    parts = period.split("-Q")
    return parts[0], parts[1]


def _build_courses_table_rows(
    settlement: Dict[str, Any],
    company_id: str,
    period: str,
    payout_ratio: float,
    total_revenue: float,
    total_ad_cost: float,
) -> str:
    """강의별 상세 테이블 HTML 행 생성 (월별 그룹핑 지원)"""
    courses = settlement.get("courses", [])
    if not courses:
        return ""

    # 월별 데이터 유무 확인
    has_monthly = any(c.get("monthly_revenue") for c in courses)

    html = ""

    if has_monthly:
        # 월별 그룹핑
        from server_logic.parsers.base import parse_quarter_months
        months = parse_quarter_months(period)

        for month in months:
            month_label = month.replace("-", ".")  # "2024-10" → "2024.10"
            month_courses = []

            for course in courses:
                mr = course.get("monthly_revenue", {})
                if month in mr:
                    month_courses.append((course, mr[month]))

            if not month_courses:
                continue

            for i, (course, month_rev) in enumerate(month_courses):
                course_name = _clean_course_name(course.get("course_name", ""))
                # 광고비를 월 매출 비율로 안분
                course_total_rev = course.get("revenue", 0)
                ratio_val = course.get("ratio", 1.0)
                course_ad_total = total_ad_cost * ratio_val if ratio_val > 0 else 0
                if course_total_rev > 0:
                    month_ad = course_ad_total * (month_rev / course_total_rev)
                else:
                    month_ad = 0
                month_cont = month_rev - month_ad
                month_settle = month_cont * payout_ratio

                html += "<tr>"
                if i == 0:
                    html += f'<td class="month-cell" rowspan="{len(month_courses)}">{month_label}</td>'
                html += f'<td class="name-cell">{course_name}</td>'
                html += f'<td class="num">{month_rev:,.0f}</td>'
                html += f'<td class="num">{month_ad:,.0f}</td>'
                html += f'<td class="num"></td>'
                html += f'<td class="num">{month_cont:,.0f}</td>'
                html += f'<td class="num">{month_settle:,.0f}</td>'
                html += "</tr>"
    else:
        # 분기 합산 (월별 데이터 없음)
        for i, course in enumerate(courses):
            course_name = _clean_course_name(course.get("course_name", ""))
            course_rev = course.get("revenue", 0)
            ratio_val = course.get("ratio", 1.0)
            course_ad = total_ad_cost * ratio_val if ratio_val > 0 else 0
            course_cont = course_rev - course_ad
            course_settle = course_cont * payout_ratio

            html += "<tr>"
            if i == 0:
                html += f'<td class="month-cell" rowspan="{len(courses)}">합계</td>'
            html += f'<td class="name-cell">{course_name}</td>'
            html += f'<td class="num">{course_rev:,.0f}</td>'
            html += f'<td class="num">{course_ad:,.0f}</td>'
            html += f'<td class="num"></td>'
            html += f'<td class="num">{course_cont:,.0f}</td>'
            html += f'<td class="num">{course_settle:,.0f}</td>'
            html += "</tr>"

    return html


def _clean_course_name(name: str) -> str:
    """강의명 정제: [쉐어엑스] 프리픽스 제거 + 40자 제한"""
    if name.startswith("[쉐어엑스]"):
        name = name[5:].strip()
    return name[:40]


def generate_single_company_pdf(
    period: str,
    company_id: str,
    settlement_data: Dict[str, Any],
    company_info: Dict[str, Any],
    output_dir: str,
) -> str:
    """단일 기업 정산서 PDF 생성

    Returns:
        생성된 PDF 파일 경로
    """
    year_num, q_num = _parse_period_parts(period)
    year_short = year_num[2:] if len(year_num) == 4 else year_num

    korean_name = company_info.get("name", settlement_data.get("company_name", company_id))
    pdf_filename = f"쉐어엑스_ {korean_name} {year_short}년 {q_num}Q 정산서.pdf"
    pdf_path = Path(output_dir) / pdf_filename

    settlement_data["period"] = period

    return generate_settlement_pdf(
        company_id=company_id,
        settlement_data=settlement_data,
        output_path=str(pdf_path),
        company_info=company_info,
    )


def get_pdf_filename(period: str, company_name: str) -> str:
    """기업 정산서 PDF 파일명 생성"""
    year_num, q_num = _parse_period_parts(period)
    year_short = year_num[2:] if len(year_num) == 4 else year_num
    return f"쉐어엑스_ {company_name} {year_short}년 {q_num}Q 정산서.pdf"


def generate_all_settlement_pdfs(
    settlement_result: Dict[str, Any],
    output_dir: str,
    companies_data: Dict[str, dict] = None,
) -> Dict[str, str]:
    """모든 기업의 정산서 PDF 일괄 생성"""
    if companies_data is None:
        companies_data = {}

    period = settlement_result["period"]
    companies = settlement_result["companies"]

    results = {}
    errors = []

    for company_id, settlement in companies.items():
        if company_id == "plusx":
            continue

        try:
            company_info = companies_data.get(company_id, {})
            pdf_file = generate_single_company_pdf(
                period=period,
                company_id=company_id,
                settlement_data=settlement,
                company_info=company_info,
                output_dir=output_dir,
            )
            results[company_id] = pdf_file
            print(f"  {company_id:20} -> {Path(pdf_file).name}")

        except Exception as e:
            errors.append(f"{company_id}: {str(e)}")
            print(f"  {company_id}: {str(e)}")

    if errors:
        print(f"\n  {len(errors)}개 PDF 생성 실패")

    return results


# CLI
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("사용법: python pdf_generator.py <settlement_result.json>")
        sys.exit(1)

    json_path = sys.argv[1]
    base_path = str(Path(__file__).parent.parent.parent)

    with open(json_path, "r", encoding="utf-8") as f:
        settlement_result = json.load(f)

    companies_data = {}
    companies_path = Path(base_path) / "data" / "companies.json"
    if companies_path.exists():
        with open(companies_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            for company in data.get("companies", []):
                companies_data[company["company_id"]] = company

    period = settlement_result["period"]
    output_dir = f"output/{period}"

    results = generate_all_settlement_pdfs(settlement_result, output_dir, companies_data)
    print(f"\n생성 완료: {len(results)}개 파일 -> {output_dir}/")
