'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { LoadingScreen } from '@/components/ui/LoadingScreen';

interface GuestGuardProps {
    children: React.ReactNode;
    redirectTo?: string;
    fallback?: React.ReactNode;
}

export function GuestGuard({ children, redirectTo = '/dashboard', fallback }: GuestGuardProps) {
    const { isAuthenticated, isLoading } = useAuth();
    const router = useRouter();

    useEffect(() => {
        if (isLoading) return;

        if (isAuthenticated) {
            const returnUrl = localStorage.getItem('smithy_return_url');
            if (returnUrl) {
                localStorage.removeItem('smithy_return_url');
                router.push(returnUrl);
            } else {
                router.push(redirectTo);
            }
        }
    }, [isAuthenticated, isLoading, redirectTo, router]);

    if (isLoading) {
        return <>{children}</>;
    }

    if (isAuthenticated) {
        return fallback || <LoadingScreen message="Redirecting to dashboard..." />;
    }

    return <>{children}</>;
}
