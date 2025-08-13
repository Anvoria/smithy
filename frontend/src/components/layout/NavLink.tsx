'use client';

import Link from 'next/link';
import { LucideIcon } from 'lucide-react';

interface NavLinkProps {
    href: string;
    icon: LucideIcon;
    label: string;
    isActive: boolean;
}

export function NavLink({ href, icon: Icon, label, isActive }: NavLinkProps) {
    return (
        <Link
            href={href}
            className={`
                flex items-center space-x-2.5 px-3 py-2 rounded-lg
                text-sm font-medium transition-colors duration-150
                ${
                    isActive
                        ? 'bg-white/10 text-white'
                        : 'text-gray-400 hover:text-gray-200 hover:bg-white/5'
                }
            `}
        >
            <Icon size={16} />
            <span>{label}</span>
        </Link>
    );
}
