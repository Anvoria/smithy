'use client';

import Image from 'next/image';
import { usePathname } from 'next/navigation';
import { Home, FolderOpen, CheckSquare, Settings } from 'lucide-react';
import { NavLink } from './NavLink';
import { UserDropdown } from './UserDropdown';

const navItems = [
    { icon: Home, label: 'Dashboard', href: '/dashboard' },
    { icon: FolderOpen, label: 'Projects', href: '/dashboard/projects' },
    { icon: CheckSquare, label: 'Tasks', href: '/dashboard/tasks' },
    { icon: Settings, label: 'Settings', href: '/dashboard/settings' },
];

export function Sidebar() {
    const pathname = usePathname();

    return (
        <div className="h-full flex flex-col">
            {/* Logo */}
            <div className="p-5">
                <div className="flex items-center space-x-3">
                    <Image
                        src="/images/logo-64.svg"
                        alt="Smithy"
                        width={24}
                        height={24}
                        className="w-6 h-6"
                    />
                    <span className="font-machina text-lg font-bold text-white">Smithy</span>
                </div>
            </div>

            {/* Navigation */}
            <nav className="flex-1 px-3">
                <ul className="space-y-0.5">
                    {navItems.map((item) => (
                        <li key={item.href}>
                            <NavLink
                                href={item.href}
                                icon={item.icon}
                                label={item.label}
                                isActive={pathname === item.href}
                            />
                        </li>
                    ))}
                </ul>
            </nav>

            {/* User Section */}
            <div className="p-3 border-t border-gray-700/30">
                <UserDropdown />
            </div>
        </div>
    );
}
