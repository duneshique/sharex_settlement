"use client";

interface ActionBarProps {
  companyCount: number;
  reviewedCount: number;
  pdfStatus: "idle" | "generating" | "completed" | "failed";
  pdfProgress: number;
  onGenerate: () => void;
  onDownloadAll: () => void;
  onSaveArchive?: () => void;
  isSaving?: boolean;
}

export default function ActionBar({
  companyCount,
  reviewedCount,
  pdfStatus,
  pdfProgress,
  onGenerate,
  onDownloadAll,
  onSaveArchive,
  isSaving = false,
}: ActionBarProps) {
  return (
    <div className="fixed bottom-8 left-1/2 -translate-x-1/2 bg-white/80 backdrop-blur-md border shadow-2xl px-6 py-4 rounded-full flex items-center gap-6 z-50">
      <div className="text-sm font-medium">
        전체 {companyCount}개 중{" "}
        <span className="text-[var(--color-accent-orange)]">
          {reviewedCount}개
        </span>{" "}
        검토 완료
      </div>
      <div className="h-4 w-[1px] bg-gray-300" />

      {/* 데이터 저장하기 */}
      {onSaveArchive && (
        <button
          onClick={onSaveArchive}
          disabled={isSaving}
          className="px-4 py-2 border border-gray-300 text-sm font-medium hover:bg-gray-50 transition-colors rounded disabled:opacity-50"
        >
          {isSaving ? "저장 중..." : "데이터 저장하기"}
        </button>
      )}

      <div className="h-4 w-[1px] bg-gray-300" />

      {pdfStatus === "idle" && (
        <button
          onClick={onGenerate}
          className="px-6 py-2 bg-black text-white text-sm font-bold hover:bg-black/90 transition-colors rounded"
        >
          최종 승인 및 PDF 생성
        </button>
      )}

      {pdfStatus === "generating" && (
        <div className="flex items-center gap-3">
          <div className="w-32 h-2 bg-gray-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-[var(--color-accent-orange)] transition-all duration-300"
              style={{ width: `${pdfProgress}%` }}
            />
          </div>
          <span className="text-xs text-gray-500">
            PDF 생성 중... {pdfProgress}%
          </span>
        </div>
      )}

      {pdfStatus === "completed" && (
        <button
          onClick={onDownloadAll}
          className="px-6 py-2 bg-[var(--color-accent-orange)] text-white text-sm font-bold hover:opacity-90 transition-colors rounded"
        >
          PDF 다운로드
        </button>
      )}

      {pdfStatus === "failed" && (
        <button
          onClick={onGenerate}
          className="px-6 py-2 border border-red-400 text-red-600 text-sm font-bold hover:bg-red-50 transition-colors rounded"
        >
          다시 시도
        </button>
      )}
    </div>
  );
}
