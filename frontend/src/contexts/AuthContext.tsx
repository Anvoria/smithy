'use client';

import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { AuthService } from '@/services/auth';
import {
    AuthState,
    User,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    MFARequiredResponse,
    MFALoginRequest,
} from '@/types/auth';

interface AuthContextType extends AuthState {
    login: (data: LoginRequest) => Promise<TokenResponse | MFARequiredResponse>;
    register: (data: RegisterRequest) => Promise<TokenResponse>;
    logout: () => Promise<void>;
    completeMFALogin: (data: MFALoginRequest) => Promise<TokenResponse>;
    refreshAuth: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
    children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
    const [state, setState] = useState<AuthState>({
        user: null,
        isAuthenticated: false,
        isLoading: true,
    });

    // Initialize auth state on mount
    useEffect(() => {
        initializeAuth();
    }, []);

    const initializeAuth = async () => {
        try {
            const user = AuthService.getUser();
            const isAuthenticated = AuthService.isAuthenticated();

            if (isAuthenticated && user) {
                setState({
                    user,
                    isAuthenticated: true,
                    isLoading: false,
                });
            } else {
                setState({
                    user: null,
                    isAuthenticated: false,
                    isLoading: false,
                });
            }
        } catch (error) {
            console.error('Auth initialization failed:', error);
            setState({
                user: null,
                isAuthenticated: false,
                isLoading: false,
            });
        }
    };

    const login = async (data: LoginRequest): Promise<TokenResponse | MFARequiredResponse> => {
        setState((prev) => ({ ...prev, isLoading: true }));

        try {
            const response = await AuthService.login(data);

            console.log('Login response:', response);
            if ('requires_mfa' in response && response.requires_mfa) {
                setState((prev) => ({ ...prev, isLoading: false }));
                return response;
            }

            // Normal login success
            const tokenResponse = response as TokenResponse;
            setState({
                user: tokenResponse.user,
                isAuthenticated: true,
                isLoading: false,
            });

            return tokenResponse;
        } catch (error) {
            setState({
                user: null,
                isAuthenticated: false,
                isLoading: false,
            });
            throw error;
        }
    };

    const completeMFALogin = async (data: MFALoginRequest): Promise<TokenResponse> => {
        setState((prev) => ({ ...prev, isLoading: true }));

        try {
            const response = await AuthService.completeMFALogin(data);

            setState({
                user: response.user,
                isAuthenticated: true,
                isLoading: false,
            });

            return response;
        } catch (error) {
            setState({
                user: null,
                isAuthenticated: false,
                isLoading: false,
            });
            throw error;
        }
    };

    const register = async (data: RegisterRequest): Promise<TokenResponse> => {
        setState((prev) => ({ ...prev, isLoading: true }));

        try {
            const response = await AuthService.register(data);

            setState({
                user: response.user,
                isAuthenticated: true,
                isLoading: false,
            });

            return response;
        } catch (error) {
            setState({
                user: null,
                isAuthenticated: false,
                isLoading: false,
            });
            throw error;
        }
    };

    const logout = async () => {
        setState((prev) => ({ ...prev, isLoading: true }));

        try {
            await AuthService.logout();
        } catch (error) {
            console.error('Logout error:', error);
        } finally {
            setState({
                user: null,
                isAuthenticated: false,
                isLoading: false,
            });
        }
    };

    const refreshAuth = async () => {
        try {
            const success = await AuthService.refreshTokens();

            if (success) {
                const user = AuthService.getUser();
                setState({
                    user,
                    isAuthenticated: true,
                    isLoading: false,
                });
            } else {
                setState({
                    user: null,
                    isAuthenticated: false,
                    isLoading: false,
                });
            }
        } catch (error) {
            console.error('Auth refresh failed:', error);
            setState({
                user: null,
                isAuthenticated: false,
                isLoading: false,
            });
        }
    };

    return (
        <AuthContext.Provider
            value={{
                ...state,
                login,
                register,
                logout,
                completeMFALogin,
                refreshAuth,
            }}
        >
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const context = useContext(AuthContext);

    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider');
    }

    return context;
}
