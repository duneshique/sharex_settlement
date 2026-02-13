"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    // Redirect to the professional settlement management page by default
    router.push("/projects/settlement");
  }, [router]);

  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <div className="text-gray-400 text-sm animate-pulse">정산 관리 시스템으로 이동 중...</div>
    </div>
  );
}
