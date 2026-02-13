"""
이메일 발송 서비스

Gmail Workspace SMTP를 통한 정산서 이메일 발송.
- 템플릿 렌더링 (str.format_map)
- PDF 첨부 발송
- 발송 로그 관리
"""

import json
import os
import smtplib
from collections import defaultdict
from datetime import datetime
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class SafeFormatDict(dict):
    """알 수 없는 키는 원본 플레이스홀더를 유지"""
    def __missing__(self, key):
        return f"{{{key}}}"


class EmailService:
    def __init__(self, config_dir: str):
        self.config_dir = Path(config_dir)
        self.smtp_config = self._load_smtp_config()
        self.template = self._load_template()

    # ──────────────────────────────────────────────
    # 설정 로드/저장
    # ──────────────────────────────────────────────

    def _load_smtp_config(self) -> Dict[str, Any]:
        """SMTP 설정 로드 (환경변수 > config 파일)"""
        # 환경변수 우선
        if os.environ.get("SMTP_HOST"):
            return {
                "host": os.environ.get("SMTP_HOST", "smtp.gmail.com"),
                "port": int(os.environ.get("SMTP_PORT", "587")),
                "username": os.environ.get("SMTP_USERNAME", ""),
                "password": os.environ.get("SMTP_PASSWORD", ""),
                "use_tls": True,
                "sender_name": os.environ.get("SMTP_SENDER_NAME", "플러스엑스 정산팀"),
                "sender_email": os.environ.get("SMTP_SENDER_EMAIL", "finance@plus-ex.com"),
            }

        # config 파일
        config_path = self.config_dir / "smtp_config.json"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)

        return {
            "host": "smtp.gmail.com",
            "port": 587,
            "username": "",
            "password": "",
            "use_tls": True,
            "sender_name": "플러스엑스 정산팀",
            "sender_email": "finance@plus-ex.com",
        }

    def save_smtp_config(self, config: Dict[str, Any]) -> None:
        """SMTP 설정 저장"""
        config_path = self.config_dir / "smtp_config.json"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        self.smtp_config = config

    def get_smtp_config_masked(self) -> Dict[str, Any]:
        """비밀번호 마스킹된 SMTP 설정 반환"""
        config = {**self.smtp_config}
        if config.get("password"):
            config["password"] = "****"
            config["configured"] = True
        else:
            config["configured"] = False
        return config

    def _load_template(self) -> Dict[str, str]:
        """이메일 템플릿 로드"""
        template_path = self.config_dir / "email_template.json"
        if template_path.exists():
            with open(template_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return self._default_template()

    def save_template(self, template: Dict[str, str]) -> None:
        """이메일 템플릿 저장"""
        template["updated_at"] = datetime.now().isoformat()
        template_path = self.config_dir / "email_template.json"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        with open(template_path, "w", encoding="utf-8") as f:
            json.dump(template, f, ensure_ascii=False, indent=2)
        self.template = template

    def get_template(self) -> Dict[str, str]:
        """현재 이메일 템플릿 반환"""
        return {**self.template}

    @staticmethod
    def _default_template() -> Dict[str, str]:
        return {
            "subject": "[플러스엑스-{company_name}] 쉐어엑스 {year_short}년 {quarter}분기 정산서",
            "body": (
                "안녕하세요. {contact_name}\n"
                "플러스엑스 {sender_name}입니다.\n"
                "잘 지내고 계신가요? : )\n\n"
                "쉐어엑스 {quarter}분기 정산서 전달 드립니다.\n\n"
                "매출내역 확인부탁 드리며, 광고비용은 기존과 동일하게, "
                "강의 수 기준으로 안분하여 반영되었습니다.\n\n"
                "정산 관련하여 추가 궁금하신 내용이 있다면 문의 주시기 바랍니다.\n\n"
                "추가 확인사항이 없으시면, 아래 내용으로 세금계산서 발행 부탁 드립니다.\n\n"
                "{quarter}Q 정산금액은 {payment_date}일 지급 예정입니다.\n\n"
                "날 짜: {tax_invoice_date}\n"
                "내 용: {content_line}\n"
                "금 액: {amount_formatted}\n"
                "메 일: finance@plus-ex.com\n"
                "계 좌: {bank_info}\n\n"
                "감사합니다.\n"
                "{sender_name}드림"
            ),
            "updated_at": "",
        }

    # ──────────────────────────────────────────────
    # 템플릿 렌더링
    # ──────────────────────────────────────────────

    def render_template(
        self,
        subject_tpl: str,
        body_tpl: str,
        variables: Dict[str, str],
    ) -> Tuple[str, str]:
        """템플릿 변수 치환"""
        safe_vars = SafeFormatDict(variables)
        subject = subject_tpl.format_map(safe_vars)
        body = body_tpl.format_map(safe_vars)
        return subject, body

    def build_template_variables(
        self,
        period: str,
        company_id: str,
        settlement_data: Dict[str, Any],
        company_info: Dict[str, Any],
        extra_vars: Dict[str, str] = None,
    ) -> Dict[str, str]:
        """정산 데이터에서 템플릿 변수 생성"""
        year = ""
        quarter = ""
        year_short = ""
        if "-Q" in period:
            parts = period.split("-Q")
            year = parts[0]
            quarter = parts[1]
            year_short = year[2:] if len(year) == 4 else year

        settlement_amount = settlement_data.get("settlement_amount", 0)
        company_name = company_info.get("name", settlement_data.get("company_name", company_id))

        variables = {
            "company_name": company_name,
            "company_id": company_id,
            "contact_name": company_info.get("contact_name", "담당자님"),
            "period": period,
            "year": year,
            "year_short": year_short,
            "quarter": quarter,
            "quarter_num": quarter,
            "settlement_amount": f"{settlement_amount:,.0f}",
            "amount_formatted": f"{settlement_amount:,.0f}원(vat포함)",
            "bank_info": f"{company_info.get('bank', '')}/ {company_info.get('account', '')} / {company_info.get('account_holder', company_name)}",
            "content_line": f"{company_name} 쉐어엑스 강사료_ {quarter}Q/{year}",
            "sender_name": self.smtp_config.get("sender_name", "정산팀"),
            "sender_email": self.smtp_config.get("sender_email", "finance@plus-ex.com"),
            "payment_date": "",
            "tax_invoice_date": "",
        }

        if extra_vars:
            variables.update(extra_vars)

        return variables

    # ──────────────────────────────────────────────
    # 이메일 발송
    # ──────────────────────────────────────────────

    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        attachment_path: Optional[str] = None,
        cc: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """단일 이메일 발송"""
        if not self.smtp_config.get("username") or not self.smtp_config.get("password"):
            raise ValueError("SMTP 설정이 완료되지 않았습니다. 설정 > SMTP에서 계정 정보를 입력하세요.")

        msg = MIMEMultipart()
        sender_name = self.smtp_config.get("sender_name", "")
        sender_email = self.smtp_config.get("sender_email", self.smtp_config["username"])
        msg["From"] = f"{sender_name} <{sender_email}>"
        msg["To"] = to
        msg["Subject"] = subject
        if cc:
            msg["Cc"] = ", ".join(cc)

        msg.attach(MIMEText(body, "plain", "utf-8"))

        # PDF 첨부
        if attachment_path and Path(attachment_path).exists():
            with open(attachment_path, "rb") as f:
                pdf_part = MIMEApplication(f.read(), _subtype="pdf")
                pdf_part.add_header(
                    "Content-Disposition", "attachment",
                    filename=Path(attachment_path).name,
                )
                msg.attach(pdf_part)

        # SMTP 발송
        host = self.smtp_config.get("host", "smtp.gmail.com")
        port = self.smtp_config.get("port", 587)

        with smtplib.SMTP(host, port, timeout=30) as server:
            if self.smtp_config.get("use_tls", True):
                server.starttls()
            server.login(self.smtp_config["username"], self.smtp_config["password"])
            recipients = [to] + (cc or [])
            server.sendmail(sender_email, recipients, msg.as_string())

        return {
            "status": "sent",
            "sent_at": datetime.now().isoformat(),
            "recipient": to,
            "subject": subject,
        }

    def send_settlement_email(
        self,
        period: str,
        company_id: str,
        settlement_data: Dict[str, Any],
        company_info: Dict[str, Any],
        pdf_path: str,
        subject_override: Optional[str] = None,
        body_override: Optional[str] = None,
        recipient_override: Optional[str] = None,
        extra_vars: Dict[str, str] = None,
    ) -> Dict[str, Any]:
        """정산서 이메일 발송 (high-level)"""
        # 수신자 결정
        recipient = recipient_override or company_info.get("contact_email", "")
        if not recipient:
            raise ValueError(f"기업 {company_id}의 이메일 주소가 등록되어 있지 않습니다.")

        # 템플릿 변수 생성
        variables = self.build_template_variables(
            period, company_id, settlement_data, company_info, extra_vars
        )

        # 템플릿 렌더링
        template = self.get_template()
        subject_tpl = subject_override or template["subject"]
        body_tpl = body_override or template["body"]
        subject, body = self.render_template(subject_tpl, body_tpl, variables)

        # 발송
        result = self.send_email(
            to=recipient,
            subject=subject,
            body=body,
            attachment_path=pdf_path,
        )

        result["pdf_filename"] = Path(pdf_path).name if pdf_path else ""
        return result

    def test_connection(self) -> Dict[str, Any]:
        """SMTP 연결 테스트"""
        if not self.smtp_config.get("username") or not self.smtp_config.get("password"):
            return {"status": "error", "message": "SMTP 설정이 완료되지 않았습니다."}

        try:
            host = self.smtp_config.get("host", "smtp.gmail.com")
            port = self.smtp_config.get("port", 587)

            with smtplib.SMTP(host, port, timeout=10) as server:
                if self.smtp_config.get("use_tls", True):
                    server.starttls()
                server.login(self.smtp_config["username"], self.smtp_config["password"])

            return {"status": "success", "message": "SMTP 연결 성공"}
        except smtplib.SMTPAuthenticationError:
            return {"status": "error", "message": "인증 실패: 사용자명 또는 비밀번호를 확인하세요. Google Workspace는 앱 비밀번호가 필요합니다."}
        except Exception as e:
            return {"status": "error", "message": f"연결 실패: {str(e)}"}


# ──────────────────────────────────────────────
# 아카이브 이메일 로그 관리
# ──────────────────────────────────────────────

def log_email_to_archive(archive_path: str, company_id: str, log_entry: Dict[str, Any]) -> None:
    """아카이브 JSON에 이메일 발송 로그 추가"""
    path = Path(archive_path)
    if not path.exists():
        return

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "email_log" not in data:
        data["email_log"] = {}
    if company_id not in data["email_log"]:
        data["email_log"][company_id] = []

    data["email_log"][company_id].append(log_entry)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
