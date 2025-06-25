import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

export const forgeTheme = {
    colors: {
        orange: '#F18424',
        charcoal: '#0D0D0D',
        iron: '#2E2E2E',
        ash: '#A2A2A2',
        shadow: '#1A1A1A',
        spark: '#FFCE5B',
        molten: '#D9481F',
    },
} as const;
