"use client";

import { useCallback, useState, useRef } from "react";

interface UploadZoneProps {
  onFileSelect: (file: File) => void;
  isLoading: boolean;
}

export default function UploadZone({ onFileSelect, isLoading }: UploadZoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);

      const file = e.dataTransfer.files[0];
      if (file?.type === "application/pdf") {
        onFileSelect(file);
      }
    },
    [onFileSelect]
  );

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) onFileSelect(file);
    },
    [onFileSelect]
  );

  if (isLoading) {
    return (
      <div className="border-2 border-dashed border-gray-200 rounded-lg p-16 text-center">
        <div className="animate-spin w-10 h-10 border-3 border-gray-300 border-t-black rounded-full mx-auto mb-4" />
        <p className="text-sm text-gray-500">PDF 분석 중...</p>
      </div>
    );
  }

  return (
    <div
      className={`border-2 border-dashed rounded-lg p-16 text-center cursor-pointer transition-colors ${
        isDragging
          ? "border-[var(--color-accent-orange)] bg-orange-50"
          : "border-gray-300 hover:border-gray-400"
      }`}
      onDragOver={(e) => {
        e.preventDefault();
        setIsDragging(true);
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={handleDrop}
      onClick={() => inputRef.current?.click()}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".pdf"
        className="hidden"
        onChange={handleChange}
      />
      <div className="text-4xl mb-4">&#128196;</div>
      <p className="text-sm font-medium mb-1">
        쉐어엑스 정산서 PDF를 드래그하거나 클릭하여 업로드
      </p>
      <p className="text-xs text-gray-400">
        분기별 정산서 PDF 파일 (예: [패스트캠퍼스] Share X 정산서 - 2024년 4Q.pdf)
      </p>
    </div>
  );
}
