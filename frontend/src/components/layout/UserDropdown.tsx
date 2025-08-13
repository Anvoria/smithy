'use client';

import { User, Settings, LogOut, UserCircle } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { Dropdown } from '@/components/ui/Dropdown';

export function UserDropdown() {
    const { user, logout } = useAuth();
    const router = useRouter();

    const dropdownItems = [
        {
            label: 'Profile Settings',
            onClick: () => router.push('/dashboard/settings'),
            icon: Settings,
        },
        {
            label: 'Account',
            onClick: () => router.push('/dashboard/settings/account'),
            icon: UserCircle,
        },
        {
            label: 'Sign Out',
            onClick: logout,
            icon: LogOut,
            variant: 'danger' as const,
        },
    ];

    if (!user) {
        return (
            <div className="flex items-center space-x-3">
                <div className="w-8 h-8 bg-gray-700 rounded-full flex items-center justify-center">
                    <User size={16} className="text-gray-300" />
                </div>
                <div className="flex-1 min-w-0">
                    <p className="font-machina text-sm font-medium text-white truncate">User</p>
                    <p className="font-machina text-xs text-gray-400 truncate">Not loaded</p>
                </div>
            </div>
        );
    }

    const trigger = (
        <div className="flex items-center space-x-3 hover:bg-white/5 rounded-lg p-2 -m-2 transition-colors">
            <div className="w-8 h-8 bg-gray-700 rounded-full flex items-center justify-center overflow-hidden">
                <img
                    src={user.avatar_url || '/images/default-avatar.png'}
                    alt={user.username || 'User Avatar'}
                    width={32}
                    height={32}
                    className="w-8 h-8 rounded-full object-cover"
                />
            </div>
            <div className="flex-1 min-w-0">
                <p className="font-machina text-sm font-medium text-white truncate">
                    {user.username}
                </p>
                <p className="font-machina text-xs text-gray-400 truncate">{user.email}</p>
            </div>
        </div>
    );

    return <Dropdown trigger={trigger} items={dropdownItems} align="right" className="w-full" />;
}
