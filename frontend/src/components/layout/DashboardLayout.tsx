'use client';

import { useState } from 'react';
import { Sidebar } from '@/components/layout/Sidebar';
import { Navbar } from '@/components/layout/Navbar';

interface DashboardLayoutProps {
    children: React.ReactNode;
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
    const [sidebarOpen, setSidebarOpen] = useState(false);

    return (
        <div className="min-h-screen bg-[#1a1a1a] text-white">
            {/* Mobile Overlay */}
            {sidebarOpen && (
                <div
                    className="fixed inset-0 bg-black/50 z-40 lg:hidden"
                    onClick={() => setSidebarOpen(false)}
                />
            )}

            <div className="flex h-screen">
                {/* Sidebar */}
                <div
                    className={`
                    fixed lg:static inset-y-0 left-0 z-50
                    w-64 bg-[#1a1a1a] border-r border-gray-800/50
                    transform transition-transform duration-300 ease-out
                    ${sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
                `}
                >
                    <Sidebar />
                </div>

                <div className="flex-1 flex flex-col min-w-0">
                    {/* Navbar */}
                    <Navbar />

                    <main className="flex-1 overflow-auto">{children}</main>
                </div>
            </div>
        </div>
    );
}
