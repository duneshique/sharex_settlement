import { useState } from "react";

const phases = [
  {
    id: "diagnosis",
    title: "현황 진단",
    icon: "🔍",
    sections: [
      {
        title: "워크플로우 병목 분석",
        items: [
          {
            label: "수동 안분 계산",
            severity: "critical",
            detail:
              "강의 수 × 기업 수 조합이 늘수록 O(n²) 수준의 작업량 증가. 현재 26개+ 강의, 6개+ 기업 → 매월 150건 이상의 안분 계산을 수동으로 수행 중",
          },
          {
            label: "광고비 역산 구조",
            severity: "critical",
            detail:
              "Adriel 데이터 → 강의별 직접광고비 추출 → 나머지를 간접광고비로 역산 → 강의 수 기준 안분. 이 과정에서 데이터 소스 3개(정산서, 인보이스, Adriel CSV)를 수동 교차 참조",
          },
          {
            label: "스키마 변동",
            severity: "high",
            detail:
              '정산서 구조가 8가지 변형 존재. 수익쉐어 비율 70%→65%→60% 변경, 컬럼명 변경(마케팅비용→직접광고비+간접광고비), 헤더 행 위치 불일치(20행 vs 50행)',
          },
          {
            label: "크로스 플랫폼 호환",
            severity: "medium",
            detail:
              "EX팀(Windows) ↔ 나머지(macOS) 간 폰트 유실, UTF-8 인코딩 충돌. 특히 한글 파일명과 셀 내 특수문자(₩, %) 처리 이슈",
          },
          {
            label: "검증 부재",
            severity: "high",
            detail:
              "합계 검증, 매핑 누락 체크, 이전 월 대비 이상치 탐지 등의 교차검증이 체계화되지 않아 오류 발견이 지연됨",
          },
        ],
      },
    ],
  },
  {
    id: "data-needs",
    title: "필요 데이터",
    icon: "📋",
    sections: [
      {
        title: "즉시 필요 (MVP 구현용)",
        priority: "P0",
        items: [
          {
            label: "유니온 기업 마스터 리스트",
            detail:
              "기업명, 기업코드, 담당자명, 이메일, 전화번호, 은행/계좌정보, 수익쉐어 비율(%), 정산 시작월",
            format: "Google Sheets 또는 CSV",
            example: "PLUSX, 플러스엑스, 김OO, finance@plus-ex.com, 70%, 2023-04",
          },
          {
            label: "강의-기업 매핑 테이블",
            detail:
              "코스ID, 강의명, 담당기업(복수 가능), 안분비율, 정산제외 여부, 적용 시작월, 특이사항",
            format: "Google Sheets 또는 CSV",
            example:
              "236657, ComfyUI 브랜드 광고, PLUSX:100%, N, 2024-01, 단독제공",
          },
          {
            label: "최근 1개월 실제 정산 완성본",
            detail:
              "가장 최근에 완성한 정산서 원본(수치가 확정된 것). MVP 검증 시 이 데이터로 자동계산 결과와 수동계산 결과를 비교할 기준선(baseline)으로 사용",
            format: "PDF 또는 Excel",
            example: "26.1_정산(실비) 시트의 확정본",
          },
          {
            label: "Adriel 원본 데이터 샘플",
            detail:
              "실제로 다운로드받는 Adriel CSV/Excel 파일 1개월치. 현재 분석된 광고 시트는 가공 후 데이터이므로, 원본 구조를 파악해야 역산 로직을 정확히 구현 가능",
            format: "CSV 또는 Excel (Adriel에서 export한 그대로)",
            example:
              "채널별, 캠페인별, 일자별 breakdown이 포함된 원본",
          },
        ],
      },
      {
        title: "추가 확인 필요 (로직 정밀화용)",
        priority: "P1",
        items: [
          {
            label: "광고 인보이스 샘플",
            detail:
              "패스트캠퍼스에서 받는 광고비 사용 인보이스의 실제 양식. 정산서 내 광고비와 인보이스 금액 간의 매칭 로직을 파악하기 위함",
            format: "PDF 또는 Excel",
            example: "",
          },
          {
            label: "수익쉐어 비율 변경 이력",
            detail:
              "기업별 · 시기별 수익쉐어 비율 변경 내역. 분석 결과 70%→65%→60%로 변화가 확인되었으나, 정확한 적용 시점과 기업별 차이를 확인 필요",
            format: "텍스트 또는 표",
            example:
              "PLUSX: ~2025.04 70%, 2025.05~ 65%, HUSKYFOX: 전기간 50%",
          },
          {
            label: "안분 예외 케이스 목록",
            detail:
              "균등분할이 아닌 특수 안분이 적용되는 경우의 리스트. 예: 특정 강의에 대해 기업A 60%, 기업B 40% 같은 비대칭 분할",
            format: "텍스트 또는 표",
            example: "",
          },
          {
            label: "정산서 최종 산출물 양식",
            detail:
              "유니온 기업에 실제로 전달하는 정산서의 디자인/양식. 웹 기반 정산서 생성 시 이 양식을 재현하기 위한 참조자료",
            format: "PDF 또는 이미지",
            example: "",
          },
        ],
      },
      {
        title: "선택 사항 (고도화용)",
        priority: "P2",
        items: [
          {
            label: "과거 정산서 아카이브",
            detail:
              "2023~2025년 기간 중 주요 정산서 3~5개월치. 시계열 비교 검증 및 이상치 탐지 기준선 구축에 활용",
            format: "Excel 또는 PDF",
            example: "",
          },
          {
            label: "B2B 판매 실적 데이터",
            detail:
              "B2B 채널 매출이 정산에 포함되는 경우, 해당 매출의 구분 및 처리 방식",
            format: "기존 B2B 판매리스트 시트 참조",
            example: "",
          },
        ],
      },
    ],
  },
  {
    id: "architecture",
    title: "자동화 설계",
    icon: "⚙️",
    sections: [
      {
        title: "시스템 아키텍처",
        diagram: true,
      },
      {
        title: "MVP 단계별 로드맵",
        phases: [
          {
            phase: "Phase 1",
            name: "데이터 파이프라인",
            duration: "1~2주",
            goal: "입력 데이터 자동 파싱 및 정규화",
            tasks: [
              "정산서 PDF/Excel 파서 (스키마 8가지 변형 대응)",
              "Adriel CSV 파서 (채널별·캠페인별·일자별 구조 대응)",
              "광고 인보이스 파서",
              "데이터 매핑 테이블 스키마 확정 및 Google Sheets 연동",
              "UTF-8 정규화 및 크로스플랫폼 호환 처리",
            ],
            output: "정규화된 JSON/DataFrame 출력",
          },
          {
            phase: "Phase 2",
            name: "안분 계산 엔진",
            duration: "1~2주",
            goal: "광고비 안분 및 정산 금액 자동 계산",
            tasks: [
              "직접광고비 매칭 (캠페인명↔강의ID 매핑)",
              "간접광고비 안분 로직 (강의 수 기반 균등분할 + 예외처리)",
              "기업별 수익쉐어 비율 적용",
              "교차검증 모듈 (합계 일치, 매핑 누락, 이상치 탐지)",
              "검증 리포트 자동 생성",
            ],
            output: "기업별 정산 데이터 + 검증 리포트",
          },
          {
            phase: "Phase 3",
            name: "정산서 생성기",
            duration: "2~3주",
            goal: "웹 기반 시각적 정산서 생성 및 PDF 출력",
            tasks: [
              "기업별 정산서 웹 템플릿 (React/HTML)",
              "PDF 다운로드 기능 (puppeteer 또는 react-pdf)",
              "대시보드: 월별 추이, 기업별 비교, 이상치 하이라이트",
              "이전 월 대비 변동 요약 자동 생성",
            ],
            output: "웹 URL 기반 정산서 + PDF export",
          },
        ],
      },
    ],
  },
  {
    id: "logic",
    title: "안분 로직",
    icon: "🧮",
    sections: [
      {
        title: "안분 계산 플로우",
        rules: [
          {
            case: "Case 1: 단독 제공",
            condition: "강의 L을 기업 A만 제공",
            formula: "A의 마케팅비 = 직접광고비(L) + 간접광고비 안분액",
            example:
              "강의 L의 직접광고비 100만원, 간접광고비 총 300만원, 전체 강의 수 30개 → A에게 100만 + (300만/30) = 110만원",
          },
          {
            case: "Case 2: 공동 제공 (균등)",
            condition: "강의 L을 기업 A, B가 공동 제공",
            formula:
              "A의 마케팅비 = 직접광고비(L) × 50% + 간접광고비 안분액 × 50%",
            example:
              "강의 L의 직접광고비 100만원 → A: 50만, B: 50만. 간접광고비 안분액 10만원 → A: 5만, B: 5만",
          },
          {
            case: "Case 3: 공동 제공 (비대칭)",
            condition: "매핑 테이블에 커스텀 비율이 지정된 경우",
            formula:
              "A의 마케팅비 = 직접광고비(L) × ratio_A + 간접광고비 안분액 × ratio_A",
            example:
              "기업A 60%, 기업B 40% → 직접광고비 100만원 → A: 60만, B: 40만",
          },
          {
            case: "Case 4: 정산 제외 강의",
            condition: "매핑 테이블에서 excluded=true",
            formula:
              "해당 강의의 직접광고비는 0 처리, 간접광고비 안분 시 분모에서도 제외",
            example:
              "30개 강의 중 2개 제외 → 간접광고비 안분 분모 = 28개",
          },
        ],
      },
      {
        title: "검증 체크리스트",
        checks: [
          {
            check: "합계 일치 검증",
            formula: "Σ(기업별 마케팅비) = 원본 전체 마케팅비",
            tolerance: "±1원 (반올림 오차 허용)",
          },
          {
            check: "매핑 완전성 검증",
            formula: "정산서 내 모든 코스ID ⊆ 매핑 테이블 코스ID",
            tolerance: "0건 누락",
          },
          {
            check: "기업 완전성 검증",
            formula: "매핑 테이블 내 모든 기업 ⊆ 기업 마스터",
            tolerance: "0건 누락",
          },
          {
            check: "이상치 탐지",
            formula: "|당월 - 전월| / 전월 > threshold",
            tolerance: "±30% 초과 시 경고 플래그",
          },
          {
            check: "안분 비율 합계 검증",
            formula: "각 강의별 Σ(기업 안분비율) = 100%",
            tolerance: "정확히 100%",
          },
        ],
      },
    ],
  },
];

const severityColors = {
  critical: { bg: "#FEE2E2", text: "#991B1B", border: "#FECACA" },
  high: { bg: "#FEF3C7", text: "#92400E", border: "#FDE68A" },
  medium: { bg: "#DBEAFE", text: "#1E40AF", border: "#BFDBFE" },
};

const priorityColors = {
  P0: { bg: "#DC2626", text: "#fff" },
  P1: { bg: "#F59E0B", text: "#fff" },
  P2: { bg: "#6B7280", text: "#fff" },
};

function SeverityBadge({ severity }) {
  const c = severityColors[severity];
  return (
    <span
      style={{
        display: "inline-block",
        padding: "2px 10px",
        borderRadius: "999px",
        fontSize: "11px",
        fontWeight: 700,
        letterSpacing: "0.5px",
        background: c.bg,
        color: c.text,
        border: `1px solid ${c.border}`,
        textTransform: "uppercase",
      }}
    >
      {severity}
    </span>
  );
}

function PriorityBadge({ priority }) {
  const c = priorityColors[priority];
  return (
    <span
      style={{
        display: "inline-block",
        padding: "2px 10px",
        borderRadius: "4px",
        fontSize: "11px",
        fontWeight: 700,
        background: c.bg,
        color: c.text,
      }}
    >
      {priority}
    </span>
  );
}

function ArchitectureDiagram() {
  const boxStyle = (color) => ({
    background: color,
    borderRadius: "8px",
    padding: "12px 16px",
    fontSize: "13px",
    textAlign: "center",
    fontWeight: 600,
    color: "#fff",
    minWidth: "140px",
  });
  const arrowStyle = {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    color: "#94A3B8",
    fontSize: "20px",
    fontWeight: 700,
  };
  const labelStyle = {
    fontSize: "10px",
    color: "#64748B",
    textAlign: "center",
    marginTop: "4px",
  };

  return (
    <div style={{ overflowX: "auto", padding: "16px 0" }}>
      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          gap: "8px",
          minWidth: "900px",
        }}
      >
        {/* Input Layer */}
        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          <div style={{ fontSize: "11px", fontWeight: 700, color: "#64748B", marginBottom: "4px" }}>
            INPUT
          </div>
          <div style={boxStyle("#3B82F6")}>📄 정산서<br/><span style={{fontSize:"10px",fontWeight:400}}>PDF / Excel</span></div>
          <div style={boxStyle("#3B82F6")}>📊 광고 인보이스<br/><span style={{fontSize:"10px",fontWeight:400}}>PDF / Excel</span></div>
          <div style={boxStyle("#3B82F6")}>📈 Adriel 데이터<br/><span style={{fontSize:"10px",fontWeight:400}}>CSV / Excel</span></div>
        </div>

        <div style={{ ...arrowStyle, alignSelf: "center" }}>→</div>

        {/* Parser Layer */}
        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          <div style={{ fontSize: "11px", fontWeight: 700, color: "#64748B", marginBottom: "4px" }}>
            PARSE & NORMALIZE
          </div>
          <div style={boxStyle("#8B5CF6")}>🔧 파서 엔진<br/><span style={{fontSize:"10px",fontWeight:400}}>스키마 자동 감지</span></div>
          <div style={boxStyle("#8B5CF6")}>🔄 UTF-8 정규화<br/><span style={{fontSize:"10px",fontWeight:400}}>Win/Mac 호환</span></div>
          <div style={boxStyle("#8B5CF6")}>📋 매핑 테이블<br/><span style={{fontSize:"10px",fontWeight:400}}>Google Sheets</span></div>
        </div>

        <div style={{ ...arrowStyle, alignSelf: "center" }}>→</div>

        {/* Compute Layer */}
        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          <div style={{ fontSize: "11px", fontWeight: 700, color: "#64748B", marginBottom: "4px" }}>
            COMPUTE
          </div>
          <div style={boxStyle("#059669")}>🧮 안분 계산<br/><span style={{fontSize:"10px",fontWeight:400}}>직접 + 간접 광고비</span></div>
          <div style={boxStyle("#059669")}>✅ 교차 검증<br/><span style={{fontSize:"10px",fontWeight:400}}>5종 자동 체크</span></div>
          <div style={boxStyle("#059669")}>📊 이상치 탐지<br/><span style={{fontSize:"10px",fontWeight:400}}>전월 대비 비교</span></div>
        </div>

        <div style={{ ...arrowStyle, alignSelf: "center" }}>→</div>

        {/* Output Layer */}
        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          <div style={{ fontSize: "11px", fontWeight: 700, color: "#64748B", marginBottom: "4px" }}>
            OUTPUT
          </div>
          <div style={boxStyle("#DC2626")}>📑 기업별 정산서<br/><span style={{fontSize:"10px",fontWeight:400}}>웹 + PDF</span></div>
          <div style={boxStyle("#DC2626")}>📋 검증 리포트<br/><span style={{fontSize:"10px",fontWeight:400}}>자동 생성</span></div>
          <div style={boxStyle("#DC2626")}>📈 대시보드<br/><span style={{fontSize:"10px",fontWeight:400}}>월별 추이</span></div>
        </div>
      </div>
    </div>
  );
}

export default function App() {
  const [activeTab, setActiveTab] = useState("diagnosis");

  const activePhase = phases.find((p) => p.id === activeTab);

  return (
    <div
      style={{
        fontFamily:
          "'Pretendard', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        background: "#0F172A",
        color: "#E2E8F0",
        minHeight: "100vh",
        padding: "0",
      }}
    >
      {/* Header */}
      <div
        style={{
          background: "linear-gradient(135deg, #1E293B 0%, #0F172A 100%)",
          borderBottom: "1px solid #1E293B",
          padding: "32px 32px 0",
        }}
      >
        <div style={{ maxWidth: "960px", margin: "0 auto" }}>
          <div style={{ fontSize: "11px", fontWeight: 700, letterSpacing: "3px", color: "#F59E0B", marginBottom: "8px" }}>
            SHARE X SETTLEMENT AUTOMATION
          </div>
          <h1
            style={{
              fontSize: "28px",
              fontWeight: 800,
              color: "#F8FAFC",
              margin: "0 0 4px",
              lineHeight: 1.3,
            }}
          >
            정산 자동화 워크플로우 진단 및 제안
          </h1>
          <p style={{ color: "#94A3B8", fontSize: "14px", margin: "0 0 24px" }}>
            현재 워크플로우 병목 분석 → 필요 데이터 정의 → MVP 단계별 자동화 설계
          </p>

          {/* Tabs */}
          <div style={{ display: "flex", gap: "0" }}>
            {phases.map((p) => (
              <button
                key={p.id}
                onClick={() => setActiveTab(p.id)}
                style={{
                  padding: "12px 24px",
                  border: "none",
                  borderBottom:
                    activeTab === p.id
                      ? "3px solid #F59E0B"
                      : "3px solid transparent",
                  background:
                    activeTab === p.id ? "#1E293B" : "transparent",
                  color: activeTab === p.id ? "#F8FAFC" : "#64748B",
                  fontSize: "14px",
                  fontWeight: activeTab === p.id ? 700 : 500,
                  cursor: "pointer",
                  borderRadius: "8px 8px 0 0",
                  transition: "all 0.2s",
                }}
              >
                {p.icon} {p.title}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Content */}
      <div style={{ maxWidth: "960px", margin: "0 auto", padding: "32px" }}>
        {/* Diagnosis Tab */}
        {activeTab === "diagnosis" &&
          activePhase.sections.map((section, si) => (
            <div key={si}>
              <h2
                style={{
                  fontSize: "20px",
                  fontWeight: 700,
                  color: "#F8FAFC",
                  marginBottom: "20px",
                }}
              >
                {section.title}
              </h2>
              <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                {section.items.map((item, ii) => (
                  <div
                    key={ii}
                    style={{
                      background: "#1E293B",
                      borderRadius: "12px",
                      padding: "20px 24px",
                      border: "1px solid #334155",
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "12px",
                        marginBottom: "8px",
                      }}
                    >
                      <SeverityBadge severity={item.severity} />
                      <span
                        style={{
                          fontSize: "16px",
                          fontWeight: 700,
                          color: "#F8FAFC",
                        }}
                      >
                        {item.label}
                      </span>
                    </div>
                    <p
                      style={{
                        color: "#94A3B8",
                        fontSize: "14px",
                        lineHeight: 1.7,
                        margin: 0,
                      }}
                    >
                      {item.detail}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          ))}

        {/* Data Needs Tab */}
        {activeTab === "data-needs" &&
          activePhase.sections.map((section, si) => (
            <div key={si} style={{ marginBottom: "32px" }}>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "12px",
                  marginBottom: "16px",
                }}
              >
                <PriorityBadge priority={section.priority} />
                <h2
                  style={{
                    fontSize: "18px",
                    fontWeight: 700,
                    color: "#F8FAFC",
                    margin: 0,
                  }}
                >
                  {section.title}
                </h2>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                {section.items.map((item, ii) => (
                  <div
                    key={ii}
                    style={{
                      background: "#1E293B",
                      borderRadius: "12px",
                      padding: "20px 24px",
                      border: "1px solid #334155",
                    }}
                  >
                    <h3
                      style={{
                        fontSize: "15px",
                        fontWeight: 700,
                        color: "#F8FAFC",
                        margin: "0 0 8px",
                      }}
                    >
                      {item.label}
                    </h3>
                    <p
                      style={{
                        color: "#94A3B8",
                        fontSize: "13px",
                        lineHeight: 1.7,
                        margin: "0 0 12px",
                      }}
                    >
                      {item.detail}
                    </p>
                    <div
                      style={{
                        display: "flex",
                        gap: "16px",
                        flexWrap: "wrap",
                      }}
                    >
                      <div>
                        <span
                          style={{
                            fontSize: "10px",
                            fontWeight: 700,
                            color: "#64748B",
                            letterSpacing: "1px",
                          }}
                        >
                          FORMAT
                        </span>
                        <div
                          style={{
                            fontSize: "12px",
                            color: "#CBD5E1",
                            marginTop: "2px",
                          }}
                        >
                          {item.format}
                        </div>
                      </div>
                      {item.example && (
                        <div style={{ flex: 1, minWidth: "200px" }}>
                          <span
                            style={{
                              fontSize: "10px",
                              fontWeight: 700,
                              color: "#64748B",
                              letterSpacing: "1px",
                            }}
                          >
                            EXAMPLE
                          </span>
                          <div
                            style={{
                              fontSize: "12px",
                              color: "#CBD5E1",
                              marginTop: "2px",
                              fontFamily: "monospace",
                              background: "#0F172A",
                              padding: "6px 10px",
                              borderRadius: "4px",
                            }}
                          >
                            {item.example}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}

        {/* Architecture Tab */}
        {activeTab === "architecture" &&
          activePhase.sections.map((section, si) => (
            <div key={si} style={{ marginBottom: "40px" }}>
              <h2
                style={{
                  fontSize: "20px",
                  fontWeight: 700,
                  color: "#F8FAFC",
                  marginBottom: "16px",
                }}
              >
                {section.title}
              </h2>

              {section.diagram && (
                <div
                  style={{
                    background: "#1E293B",
                    borderRadius: "12px",
                    padding: "24px",
                    border: "1px solid #334155",
                    marginBottom: "24px",
                  }}
                >
                  <ArchitectureDiagram />
                </div>
              )}

              {section.phases &&
                section.phases.map((ph, pi) => (
                  <div
                    key={pi}
                    style={{
                      background: "#1E293B",
                      borderRadius: "12px",
                      padding: "24px",
                      border: "1px solid #334155",
                      marginBottom: "12px",
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "12px",
                        marginBottom: "12px",
                      }}
                    >
                      <span
                        style={{
                          background:
                            pi === 0
                              ? "#3B82F6"
                              : pi === 1
                              ? "#059669"
                              : "#DC2626",
                          color: "#fff",
                          padding: "4px 12px",
                          borderRadius: "6px",
                          fontSize: "12px",
                          fontWeight: 700,
                        }}
                      >
                        {ph.phase}
                      </span>
                      <span
                        style={{
                          fontSize: "18px",
                          fontWeight: 700,
                          color: "#F8FAFC",
                        }}
                      >
                        {ph.name}
                      </span>
                      <span
                        style={{
                          fontSize: "12px",
                          color: "#64748B",
                          marginLeft: "auto",
                        }}
                      >
                        ⏱ {ph.duration}
                      </span>
                    </div>
                    <p
                      style={{
                        color: "#F59E0B",
                        fontSize: "13px",
                        fontWeight: 600,
                        margin: "0 0 12px",
                      }}
                    >
                      목표: {ph.goal}
                    </p>
                    <div
                      style={{
                        display: "flex",
                        flexDirection: "column",
                        gap: "6px",
                        marginBottom: "12px",
                      }}
                    >
                      {ph.tasks.map((t, ti) => (
                        <div
                          key={ti}
                          style={{
                            color: "#CBD5E1",
                            fontSize: "13px",
                            paddingLeft: "16px",
                            position: "relative",
                          }}
                        >
                          <span
                            style={{
                              position: "absolute",
                              left: 0,
                              color: "#475569",
                            }}
                          >
                            ▸
                          </span>
                          {t}
                        </div>
                      ))}
                    </div>
                    <div
                      style={{
                        background: "#0F172A",
                        padding: "8px 12px",
                        borderRadius: "6px",
                        fontSize: "12px",
                        color: "#94A3B8",
                      }}
                    >
                      <strong style={{ color: "#F59E0B" }}>OUTPUT:</strong>{" "}
                      {ph.output}
                    </div>
                  </div>
                ))}
            </div>
          ))}

        {/* Logic Tab */}
        {activeTab === "logic" &&
          activePhase.sections.map((section, si) => (
            <div key={si} style={{ marginBottom: "40px" }}>
              <h2
                style={{
                  fontSize: "20px",
                  fontWeight: 700,
                  color: "#F8FAFC",
                  marginBottom: "16px",
                }}
              >
                {section.title}
              </h2>

              {section.rules &&
                section.rules.map((rule, ri) => (
                  <div
                    key={ri}
                    style={{
                      background: "#1E293B",
                      borderRadius: "12px",
                      padding: "20px 24px",
                      border: "1px solid #334155",
                      marginBottom: "12px",
                    }}
                  >
                    <h3
                      style={{
                        fontSize: "15px",
                        fontWeight: 700,
                        color: "#F59E0B",
                        margin: "0 0 4px",
                      }}
                    >
                      {rule.case}
                    </h3>
                    <p
                      style={{
                        color: "#94A3B8",
                        fontSize: "13px",
                        margin: "0 0 8px",
                      }}
                    >
                      조건: {rule.condition}
                    </p>
                    <div
                      style={{
                        background: "#0F172A",
                        padding: "10px 14px",
                        borderRadius: "6px",
                        fontFamily: "monospace",
                        fontSize: "13px",
                        color: "#67E8F9",
                        marginBottom: "8px",
                      }}
                    >
                      {rule.formula}
                    </div>
                    <p
                      style={{
                        color: "#CBD5E1",
                        fontSize: "12px",
                        margin: 0,
                        fontStyle: "italic",
                      }}
                    >
                      예시: {rule.example}
                    </p>
                  </div>
                ))}

              {section.checks &&
                section.checks.map((chk, ci) => (
                  <div
                    key={ci}
                    style={{
                      background: "#1E293B",
                      borderRadius: "12px",
                      padding: "16px 20px",
                      border: "1px solid #334155",
                      marginBottom: "8px",
                      display: "flex",
                      alignItems: "center",
                      gap: "16px",
                    }}
                  >
                    <div
                      style={{
                        width: "28px",
                        height: "28px",
                        borderRadius: "50%",
                        background: "#059669",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontSize: "14px",
                        flexShrink: 0,
                      }}
                    >
                      ✓
                    </div>
                    <div style={{ flex: 1 }}>
                      <div
                        style={{
                          fontSize: "14px",
                          fontWeight: 700,
                          color: "#F8FAFC",
                          marginBottom: "2px",
                        }}
                      >
                        {chk.check}
                      </div>
                      <div
                        style={{
                          fontSize: "12px",
                          color: "#94A3B8",
                          fontFamily: "monospace",
                        }}
                      >
                        {chk.formula}
                      </div>
                    </div>
                    <div
                      style={{
                        fontSize: "11px",
                        color: "#F59E0B",
                        fontWeight: 600,
                        whiteSpace: "nowrap",
                      }}
                    >
                      허용: {chk.tolerance}
                    </div>
                  </div>
                ))}
            </div>
          ))}
      </div>
    </div>
  );
}
