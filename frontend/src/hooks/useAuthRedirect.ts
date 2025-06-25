'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';

interface UseAuthRedirectOptions {
    requireAuth?: boolean;
    requiredRoles?: string[];
    redirectTo?: string;
    onUnauthorized?: () => void;
}

export function useAuthRedirect({
    requireAuth = true,
    requiredRoles = [],
    redirectTo = '/login',
    onUnauthorized,
}: UseAuthRedirectOptions = {}) {
    const { user, isAuthenticated, isLoading } = useAuth();
    const router = useRouter();

    useEffect(() => {
        if (isLoading) return;

        if (requireAuth && !isAuthenticated) {
            if (onUnauthorized) {
                onUnauthorized();
            } else {
                router.push(redirectTo);
            }
            return;
        }

        if (requiredRoles.length > 0 && user && !requiredRoles.includes(user.role)) {
            if (onUnauthorized) {
                onUnauthorized();
            } else {
                router.push('/unauthorized');
            }
            return;
        }
    }, [
        isAuthenticated,
        isLoading,
        user,
        requireAuth,
        requiredRoles,
        redirectTo,
        onUnauthorized,
        router,
    ]);

    return {
        isAuthorized:
            isAuthenticated &&
            (requiredRoles.length === 0 || (user && requiredRoles.includes(user.role))),
        isLoading,
        user,
    };
}
