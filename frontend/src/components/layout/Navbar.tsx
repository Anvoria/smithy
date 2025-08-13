'use client';

import { usePathname } from 'next/navigation';
import { ChevronRight } from 'lucide-react';

export function Navbar() {
    const pathname = usePathname();

    const segments = pathname.split('/').filter(Boolean);

    // Generate breadcrumb items
    const breadcrumbs = segments.map((segment, index) => {
        const href = '/' + segments.slice(0, index + 1).join('/');
        const label = segment.charAt(0).toUpperCase() + segment.slice(1);
        const isLast = index === segments.length - 1;

        return { href, label, isLast };
    });

    return (
        <nav className="h-14 bg-[#1a1a1a] border-b border-gray-700/30 flex items-center px-6">
            <div className="flex items-center space-x-2 text-sm">
                {breadcrumbs.map((crumb, index) => (
                    <div key={crumb.href} className="flex items-center space-x-2">
                        {index > 0 && <ChevronRight size={14} className="text-gray-500" />}
                        {crumb.isLast ? (
                            <span className="text-white font-medium">{crumb.label}</span>
                        ) : (
                            <a
                                href={crumb.href}
                                className="text-gray-400 hover:text-gray-200 transition-colors"
                            >
                                {crumb.label}
                            </a>
                        )}
                    </div>
                ))}
            </div>
        </nav>
    );
}
