'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useAuth } from '@/contexts/AuthContext';
import { RegisterRequest } from '@/types/auth';
import { AuthLayout } from '@/components/layout/AuthLayout';
import { FormField } from '@/components/forms/FormField';
import { Button } from '@/components/forms/Button';
import { ErrorMessage } from '@/components/ui/ErrorMessage';

interface RegisterFormState {
    email: string;
    password: string;
    confirmPassword: string;
    first_name: string;
    last_name: string;
}

interface RegisterErrors {
    email?: string;
    password?: string;
    confirmPassword?: string;
    first_name?: string;
    last_name?: string;
    general?: string;
}

export default function RegisterForm() {
    const { register } = useAuth();

    const [formData, setFormData] = useState<RegisterFormState>({
        email: '',
        password: '',
        confirmPassword: '',
        first_name: '',
        last_name: '',
    });

    const [showPassword, setShowPassword] = useState(false);
    const [showConfirmPassword, setShowConfirmPassword] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const [errors, setErrors] = useState<RegisterErrors>({});

    // Password strength validation
    const validatePasswordStrength = (password: string) => {
        return {
            length: password.length >= 8,
            uppercase: /[A-Z]/.test(password),
            lowercase: /[a-z]/.test(password),
            digit: /\d/.test(password),
            special: /[!@#$%^&*(),.?":{}|<>]/.test(password),
        };
    };

    const getPasswordStrength = (password: string) => {
        const checks = validatePasswordStrength(password);
        const score = Object.values(checks).filter(Boolean).length;

        if (score < 3) return { level: 'weak', color: 'bg-red-500', text: 'Weak' };
        if (score < 5) return { level: 'medium', color: 'bg-yellow-500', text: 'Medium' };
        return { level: 'strong', color: 'bg-green-500', text: 'Strong' };
    };

    const validateForm = (): boolean => {
        const newErrors: RegisterErrors = {};

        if (!formData.email) {
            newErrors.email = 'Email is required';
        } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
            newErrors.email = 'Please enter a valid email address';
        }

        if (!formData.password) {
            newErrors.password = 'Password is required';
        } else {
            const checks = validatePasswordStrength(formData.password);
            if (!checks.length) {
                newErrors.password = 'Password must be at least 8 characters long';
            } else if (!checks.uppercase || !checks.lowercase || !checks.digit || !checks.special) {
                newErrors.password =
                    'Password must contain uppercase, lowercase, digit, and special character';
            }
        }

        if (!formData.confirmPassword) {
            newErrors.confirmPassword = 'Please confirm your password';
        } else if (formData.password !== formData.confirmPassword) {
            newErrors.confirmPassword = 'Passwords do not match';
        }

        if (formData.first_name && formData.first_name.length > 100) {
            newErrors.first_name = 'First name must be less than 100 characters';
        }

        if (formData.last_name && formData.last_name.length > 100) {
            newErrors.last_name = 'Last name must be less than 100 characters';
        }

        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    const handleFieldChange = (field: keyof RegisterFormState, value: string) => {
        setFormData((prev) => ({
            ...prev,
            [field]: value,
        }));

        // Clear field-specific errors
        if (errors[field as keyof RegisterErrors]) {
            setErrors((prev) => {
                const newErrors = { ...prev };
                delete newErrors[field as keyof RegisterErrors];
                return newErrors;
            });
        }

        // Clear confirm password error if passwords now match
        if (
            field === 'password' &&
            formData.confirmPassword &&
            value === formData.confirmPassword
        ) {
            setErrors((prev) => {
                const newErrors = { ...prev };
                delete newErrors.confirmPassword;
                return newErrors;
            });
        }
        if (field === 'confirmPassword' && formData.password && value === formData.password) {
            setErrors((prev) => {
                const newErrors = { ...prev };
                delete newErrors.confirmPassword;
                return newErrors;
            });
        }
    };

    const handleSubmit = async () => {
        if (!validateForm()) return;

        setIsLoading(true);
        setErrors({});

        try {
            const registerData: RegisterRequest = {
                email: formData.email,
                password: formData.password,
                first_name: formData.first_name || undefined,
                last_name: formData.last_name || undefined,
            };

            await register(registerData);
        } catch (error) {
            setErrors({
                general:
                    error instanceof Error
                        ? error.message
                        : 'Registration failed. Please try again.',
            });
        } finally {
            setIsLoading(false);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !isLoading) {
            e.preventDefault();
            handleSubmit();
        }
    };

    const passwordStrength = formData.password ? getPasswordStrength(formData.password) : null;

    return (
        <AuthLayout>
            <div>
                <div className="mb-8">
                    <h2 className="font-machina text-3xl font-medium text-white mb-2">
                        Create Account
                    </h2>
                    <p className="text-[var(--ash-gray)] text-sm">Set up your workspace</p>
                </div>

                {/* General Error */}
                {errors.general && <ErrorMessage message={errors.general} className="mb-6" />}

                {/* Form */}
                <form onSubmit={handleSubmit} onKeyDown={handleKeyDown} className="space-y-5">
                    {/* Name Fields */}
                    <div className="grid grid-cols-2 gap-4">
                        <FormField
                            label="First Name"
                            type="text"
                            value={formData.first_name}
                            onChange={(value: string) => handleFieldChange('first_name', value)}
                            placeholder="Jacob"
                            error={errors.first_name}
                            disabled={isLoading}
                            autoComplete="given-name"
                        />

                        <FormField
                            label="Last Name"
                            type="text"
                            value={formData.last_name}
                            onChange={(value: string) => handleFieldChange('last_name', value)}
                            placeholder="Smith"
                            error={errors.last_name}
                            disabled={isLoading}
                            autoComplete="family-name"
                        />
                    </div>

                    {/* Email */}
                    <FormField
                        label="Email"
                        type="email"
                        value={formData.email}
                        onChange={(value: string) => handleFieldChange('email', value)}
                        placeholder="jacob@smithy.sh"
                        error={errors.email}
                        disabled={isLoading}
                        autoFocus
                        autoComplete="email"
                    />

                    {/* Password */}
                    <FormField
                        label="Password"
                        type="password"
                        value={formData.password}
                        onChange={(value: string) => handleFieldChange('password', value)}
                        placeholder="Create a strong password"
                        error={errors.password}
                        disabled={isLoading}
                        autoComplete="new-password"
                        showPasswordToggle
                        showPassword={showPassword}
                        onPasswordToggle={() => setShowPassword(!showPassword)}
                    />

                    {/* Password Strength Indicator */}
                    {formData.password && passwordStrength && (
                        <div className="space-y-2">
                            <div className="flex items-center justify-between text-xs">
                                <span className="text-[var(--ash-gray)]">Password strength:</span>
                                <span
                                    className={`font-medium ${
                                        passwordStrength.level === 'weak'
                                            ? 'text-red-400'
                                            : passwordStrength.level === 'medium'
                                              ? 'text-yellow-400'
                                              : 'text-green-400'
                                    }`}
                                >
                                    {passwordStrength.text}
                                </span>
                            </div>
                            <div className="w-full bg-[var(--charcoal)] rounded-full h-2">
                                <div
                                    className={`h-2 rounded-full transition-all duration-300 ${passwordStrength.color}`}
                                    style={{
                                        width: `${(Object.values(validatePasswordStrength(formData.password)).filter(Boolean).length / 5) * 100}%`,
                                    }}
                                />
                            </div>
                            <div className="text-xs text-[var(--ash-gray)]">
                                <p>Password requirements:</p>
                                <div className="grid grid-cols-2 gap-1 mt-1">
                                    {Object.entries(
                                        validatePasswordStrength(formData.password)
                                    ).map(([key, valid]) => (
                                        <div
                                            key={key}
                                            className={`flex items-center ${valid ? 'text-green-400' : 'text-red-400'}`}
                                        >
                                            <span className="mr-1">{valid ? '✓' : '✗'}</span>
                                            <span className="text-xs">
                                                {key === 'length'
                                                    ? '8+ characters'
                                                    : key === 'uppercase'
                                                      ? 'Uppercase'
                                                      : key === 'lowercase'
                                                        ? 'Lowercase'
                                                        : key === 'digit'
                                                          ? 'Number'
                                                          : 'Special char'}
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Confirm Password */}
                    <FormField
                        label="Confirm Password"
                        type="password"
                        value={formData.confirmPassword}
                        onChange={(value: string) => handleFieldChange('confirmPassword', value)}
                        placeholder="Confirm your password"
                        error={errors.confirmPassword}
                        disabled={isLoading}
                        autoComplete="new-password"
                        showPasswordToggle
                        showPassword={showConfirmPassword}
                        onPasswordToggle={() => setShowConfirmPassword(!showConfirmPassword)}
                    />

                    {/* Terms and Privacy */}
                    <div className="text-xs text-[var(--ash-gray)] leading-relaxed">
                        By creating an account, you agree to our{' '}
                        <Link
                            href="/terms"
                            className="text-[var(--forge-orange)] hover:text-[var(--spark-yellow)] transition-colors"
                        >
                            Terms of Service
                        </Link>{' '}
                        and{' '}
                        <Link
                            href="/privacy"
                            className="text-[var(--forge-orange)] hover:text-[var(--spark-yellow)] transition-colors"
                        >
                            Privacy Policy
                        </Link>
                    </div>

                    {/* Submit Button */}
                    <Button
                        type="submit"
                        variant="primary"
                        disabled={isLoading}
                        loading={isLoading}
                        fullWidth
                        className="mt-6"
                    >
                        {isLoading ? 'Creating Account...' : 'Create Account'}
                    </Button>
                </form>

                {/* Login Link */}
                <div className="text-center mt-8">
                    <div className="text-[var(--ash-gray)] text-sm">
                        Already have an account?{' '}
                        <Link
                            href="/login"
                            className="text-[var(--forge-orange)] hover:text-[var(--spark-yellow)] transition-colors py-2 px-1 cursor-pointer"
                        >
                            Sign in
                        </Link>
                    </div>
                </div>
            </div>
        </AuthLayout>
    );
}
