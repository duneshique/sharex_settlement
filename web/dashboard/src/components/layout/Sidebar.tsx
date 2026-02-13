import React from 'react';
import Link from 'next/link';

export default function Sidebar() {
    const menuItems = [
        { label: '내 프로젝트', href: '/projects' },
        { label: '전체 프로젝트', href: '/projects/all' },
    ];

    const actionButtons = [
        { label: '고객사 관리', href: '/projects/clients' },
        { label: '프로젝트 생성', href: '/projects/new' },
        { label: '투입 리소스 수정', href: '/projects/resources' },
        { label: '프로젝트 정산', href: '/projects/settlement', highlight: true },
    ];

    return (
        <aside className="sidebar flex flex-col h-full">
            <div className="p-6">
                <div className="w-8 h-8 bg-black rounded flex items-center justify-center text-white font-bold text-xl">G</div>
            </div>

            <div className="flex-1 px-4 py-2">
                <h2 className="text-[18px] font-bold px-4 mb-6">프로젝트</h2>

                <nav className="space-y-1">
                    {menuItems.map((item) => (
                        <Link
                            key={item.label}
                            href={item.href}
                            className="block px-4 py-2 text-[14px] text-gray-900 hover:bg-[#F3F3F3] rounded transition-colors"
                        >
                            {item.label}
                        </Link>
                    ))}
                </nav>

                <div className="mt-12 space-y-2">
                    {actionButtons.map((btn) => (
                        <Link
                            key={btn.label}
                            href={btn.href}
                            className={`block w-full px-4 py-2 text-center text-[13px] font-medium border border-black rounded-[2px] hover:bg-gray-50 transition-colors ${btn.highlight ? 'bg-black !text-white hover:bg-black/90' : 'text-black'
                                }`}
                        >
                            {btn.label}
                        </Link>
                    ))}
                </div>
            </div>

            <div className="p-6 mt-auto">
                <div className="w-8 h-8 rounded-full bg-gray-900 flex items-center justify-center text-white text-xs font-bold">N</div>
            </div>
        </aside>
    );
}
