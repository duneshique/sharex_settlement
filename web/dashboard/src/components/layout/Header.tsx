import React from 'react';

export default function Header() {
    return (
        <header className="header flex justify-between items-center px-6">
            <div className="flex gap-8 text-[14px] font-medium text-gray-400">
                <span className="cursor-pointer hover:text-black">데스크</span>
                <span className="cursor-pointer hover:text-black">페이퍼빈</span>
                <span className="cursor-pointer hover:text-black">전자결제</span>
                <span className="cursor-pointer hover:text-black text-black">프로젝트</span>
            </div>

            <div className="flex gap-4 items-center">
                <div className="flex gap-2">
                    {/* Mock icons for Lock, Notification, Profile */}
                    <div className="w-10 h-10 flex items-center justify-center hover:bg-gray-100 rounded-full cursor-pointer">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" /></svg>
                    </div>
                    <div className="w-10 h-10 flex items-center justify-center hover:bg-gray-100 rounded-full cursor-pointer relative">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" /><path d="M13.73 21a2 2 0 0 1-3.46 0" /></svg>
                        <span className="absolute top-2 right-2 w-2 h-2 bg-[#ff5c35] rounded-full border-2 border-white"></span>
                    </div>
                    <div className="w-10 h-10 flex items-center justify-center hover:bg-gray-100 rounded-full cursor-pointer">
                        <div className="w-6 h-6 rounded-full bg-gray-200 border border-gray-300"></div>
                    </div>
                </div>
            </div>
        </header>
    );
}
