'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useAuth } from '@/contexts/AuthContext';
import { AuthService } from '@/services/auth';
import { LoginRequest, MFARequiredResponse } from '@/types/auth';
import { AuthLayout } from '@/components/layout/AuthLayout';
import { EmailPasswordStep } from '@/components/auth/login/EmailPasswordStep';
import { MFAStep } from '@/components/auth/login/MFAStep';

interface LoginFormState {
    email: string;
    password: string;
    mfa_code: string;
    remember_me: boolean;
}

interface LoginErrors {
    email?: string;
    password?: string;
    mfa_code?: string;
    general?: string;
}

export default function LoginForm() {
    const { login, completeMFALogin } = useAuth();

    const [formData, setFormData] = useState<LoginFormState>({
        email: '',
        password: '',
        mfa_code: '',
        remember_me: false,
    });

    const [showPassword, setShowPassword] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const [errors, setErrors] = useState<LoginErrors>({});
    const [requiresMFA, setRequiresMFA] = useState(false);
    const [partialAuthToken, setPartialAuthToken] = useState<string | null>(null);

    // Load remembered email on mount
    useEffect(() => {
        const savedEmail = AuthService.getRememberedEmail();
        if (savedEmail) {
            setFormData((prev) => ({
                ...prev,
                email: savedEmail,
                remember_me: true,
            }));
        }
    }, []);

    const validateForm = (includeMFA = false): boolean => {
        const newErrors: LoginErrors = {};

        if (!formData.email) {
            newErrors.email = 'Email is required';
        } else if (!/\S+@\S+\.\S+/.test(formData.email)) {
            newErrors.email = 'Please enter a valid email';
        }

        if (!formData.password) {
            newErrors.password = 'Password is required';
        } else if (formData.password.length < 6) {
            newErrors.password = 'Password must be at least 6 characters';
        }

        if (includeMFA && requiresMFA && !formData.mfa_code) {
            newErrors.mfa_code = 'MFA code is required';
        }

        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    const handleInitialLogin = async (e?: React.FormEvent) => {
        e?.preventDefault();
        if (!validateForm()) return;

        setIsLoading(true);
        setErrors({});

        try {
            const loginData: LoginRequest = {
                email: formData.email,
                password: formData.password,
                remember_me: formData.remember_me,
            };

            const response = await login(loginData);

            if ('requires_mfa' in response && response.requires_mfa) {
                const mfaResponse = response as MFARequiredResponse;
                setRequiresMFA(true);
                setPartialAuthToken(mfaResponse.partial_auth_token || null);
                return;
            }

            // Handle remember email
            if (formData.remember_me) {
                AuthService.setRememberedEmail(formData.email);
            } else {
                AuthService.clearRememberedEmail();
            }
        } catch (error) {
            setErrors({
                general: error instanceof Error ? error.message : 'Login failed. Please try again.',
            });
        } finally {
            setIsLoading(false);
        }
    };

    const handleMFALogin = async (e?: React.FormEvent) => {
        e?.preventDefault();
        if (!validateForm(true) || !partialAuthToken) return;

        setIsLoading(true);
        setErrors({});

        try {
            await completeMFALogin({
                partial_auth_token: partialAuthToken,
                mfa_code: formData.mfa_code,
            });

            // Handle remember email
            if (formData.remember_me) {
                AuthService.setRememberedEmail(formData.email);
            } else {
                AuthService.clearRememberedEmail();
            }
        } catch (error) {
            setErrors({
                general:
                    error instanceof Error
                        ? error.message
                        : 'MFA verification failed. Please try again.',
            });
        } finally {
            setIsLoading(false);
        }
    };

    const handleFieldChange = (field: keyof LoginFormState, value: string | boolean) => {
        setFormData((prev) => ({
            ...prev,
            [field]: value,
        }));

        // Clear field-specific errors
        if (errors[field as keyof LoginErrors]) {
            setErrors((prev) => {
                const newErrors = { ...prev };
                delete newErrors[field as keyof LoginErrors];
                return newErrors;
            });
        }
    };

    const handleBackToLogin = () => {
        setRequiresMFA(false);
        setPartialAuthToken(null);
        setFormData((prev) => ({ ...prev, mfa_code: '' }));
        setErrors({});
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !isLoading) {
            e.preventDefault();
            if (requiresMFA) {
                handleMFALogin();
            } else {
                handleInitialLogin();
            }
        }
    };

    return (
        <AuthLayout>
            <div>
                {!requiresMFA ? (
                    <>
                        <EmailPasswordStep
                            email={formData.email}
                            password={formData.password}
                            rememberMe={formData.remember_me}
                            errors={errors}
                            isLoading={isLoading}
                            showPassword={showPassword}
                            onEmailChange={(email: string) => handleFieldChange('email', email)}
                            onPasswordChange={(password: string) =>
                                handleFieldChange('password', password)
                            }
                            onRememberMeChange={(checked: boolean) =>
                                handleFieldChange('remember_me', checked)
                            }
                            onPasswordToggle={() => setShowPassword(!showPassword)}
                            onSubmit={handleInitialLogin}
                            onKeyDown={handleKeyDown}
                        />

                        {/* Sign up link */}
                        <div className="text-center mt-8">
                            <div className="text-[var(--ash-gray)] text-sm">
                                Need an account?{' '}
                                <Link
                                    href="/register"
                                    className="text-[var(--forge-orange)] hover:text-[var(--spark-yellow)] transition-colors py-2 px-1 cursor-pointer"
                                >
                                    Sign up
                                </Link>
                            </div>
                        </div>
                    </>
                ) : (
                    <MFAStep
                        mfaCode={formData.mfa_code}
                        error={errors.mfa_code}
                        generalError={errors.general}
                        isLoading={isLoading}
                        onMfaCodeChange={(code: string) => handleFieldChange('mfa_code', code)}
                        onSubmit={handleMFALogin}
                        onBack={handleBackToLogin}
                        onKeyDown={handleKeyDown}
                    />
                )}
            </div>
        </AuthLayout>
    );
}
