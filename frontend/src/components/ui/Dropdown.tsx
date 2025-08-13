'use client';

import { Menu, MenuButton, MenuItem, MenuItems } from '@headlessui/react';
import { LucideIcon } from 'lucide-react';

interface DropdownItem {
    label: string;
    onClick: () => void;
    icon?: LucideIcon;
    variant?: 'default' | 'danger';
    disabled?: boolean;
}

interface DropdownProps {
    trigger: React.ReactNode;
    items: DropdownItem[];
    align?: 'left' | 'right';
    className?: string;
}

export function Dropdown({ trigger, items, align = 'right', className = '' }: DropdownProps) {
    const alignmentClasses = {
        left: 'origin-top-left',
        right: 'origin-top-right',
    };

    const anchorAlignment = {
        left: 'bottom start' as const,
        right: 'bottom end' as const,
    };

    return (
        <Menu as="div" className={`relative inline-block text-left ${className}`}>
            <MenuButton as="div" className="cursor-pointer">
                {trigger}
            </MenuButton>

            <MenuItems
                transition
                anchor={anchorAlignment[align]}
                className={`
                    ${alignmentClasses[align]} w-48
                    rounded-lg border border-gray-700/50 bg-[#2a2a2a] p-1
                    shadow-xl backdrop-blur-sm
                    text-sm text-white transition duration-100 ease-out
                    focus:outline-none data-closed:scale-95 data-closed:opacity-0
                    z-50 [--anchor-gap:8px]
                `}
            >
                {items.map((item, index) => (
                    <MenuItem key={index} disabled={item.disabled}>
                        <button
                            onClick={item.onClick}
                            disabled={item.disabled}
                            className={`
                                group flex w-full items-center space-x-2.5 rounded-md px-2.5 py-1.5
                                text-sm transition-colors hover:cursor-pointer
                                ${
                                    item.disabled
                                        ? 'text-gray-500 cursor-not-allowed'
                                        : item.variant === 'danger'
                                          ? 'text-red-400 data-focus:bg-red-500/10 data-focus:text-red-300'
                                          : 'text-gray-300 data-focus:bg-white/10 data-focus:text-white'
                                }
                            `}
                        >
                            {item.icon && (
                                <item.icon
                                    size={16}
                                    className={`
                                        ${
                                            item.disabled
                                                ? 'text-gray-500'
                                                : item.variant === 'danger'
                                                  ? 'text-red-400'
                                                  : 'text-gray-400'
                                        }
                                    `}
                                />
                            )}
                            <span>{item.label}</span>
                        </button>
                    </MenuItem>
                ))}
            </MenuItems>
        </Menu>
    );
}
