'use client';

import { useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { LoadingScreen } from '@/components/ui/LoadingScreen';

interface AuthGuardProps {
    children: React.ReactNode;
    requireAuth?: boolean;
    redirectTo?: string;
    fallback?: React.ReactNode;
}

export function AuthGuard({
    children,
    requireAuth = true,
    redirectTo = '/login',
    fallback,
}: AuthGuardProps) {
    const { isAuthenticated, isLoading } = useAuth();
    const router = useRouter();
    const pathname = usePathname();

    useEffect(() => {
        if (isLoading) return;

        if (requireAuth && !isAuthenticated) {
            if (pathname !== '/login' && pathname !== '/register') {
                localStorage.setItem('smithy_return_url', pathname);
            }
            router.push(redirectTo);
        }
    }, [isAuthenticated, isLoading, requireAuth, redirectTo, router, pathname]);

    if (isLoading) {
        return fallback || <LoadingScreen message="Checking authentication..." />;
    }

    if (requireAuth && !isAuthenticated) {
        return fallback || <LoadingScreen message="Redirecting to login..." />;
    }

    return <>{children}</>;
}
