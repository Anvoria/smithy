import Link from 'next/link';
import { FormField } from '@/components/forms/FormField';
import { Checkbox } from '@/components/forms/Checkbox';
import { Button } from '@/components/forms/Button';
import { ErrorMessage } from '@/components/ui/ErrorMessage';

interface EmailPasswordStepProps {
    email: string;
    password: string;
    rememberMe: boolean;
    errors: {
        email?: string;
        password?: string;
        general?: string;
    };
    isLoading: boolean;
    showPassword: boolean;
    onEmailChange: (email: string) => void;
    onPasswordChange: (password: string) => void;
    onRememberMeChange: (checked: boolean) => void;
    onPasswordToggle: () => void;
    onSubmit: (e: React.FormEvent) => void;
    onKeyDown: (e: React.KeyboardEvent) => void;
}

export function EmailPasswordStep({
    email,
    password,
    rememberMe,
    errors,
    isLoading,
    showPassword,
    onEmailChange,
    onPasswordChange,
    onRememberMeChange,
    onPasswordToggle,
    onSubmit,
    onKeyDown,
}: EmailPasswordStepProps) {
    return (
        <div className="w-full max-w-sm mx-auto">
            {/* Header */}
            <div className="text-center mb-6">
                <h2 className="font-machina text-2xl font-medium text-white mb-1">Welcome back</h2>
                <p className="text-[var(--ash-gray)] text-sm">Sign in to continue</p>
            </div>

            {/* General Error */}
            {errors.general && (
                <div className="mb-4">
                    <ErrorMessage message={errors.general} />
                </div>
            )}

            {/* Form */}
            <div className="space-y-4" onKeyDown={onKeyDown}>
                {/* Email */}
                <FormField
                    label="Email"
                    type="email"
                    value={email}
                    onChange={onEmailChange}
                    placeholder="your@email.com"
                    error={errors.email}
                    disabled={isLoading}
                    autoFocus
                    autoComplete="email"
                />

                {/* Password */}
                <FormField
                    label="Password"
                    type="password"
                    value={password}
                    onChange={onPasswordChange}
                    placeholder="Enter password"
                    error={errors.password}
                    disabled={isLoading}
                    autoComplete="current-password"
                    showPasswordToggle
                    showPassword={showPassword}
                    onPasswordToggle={onPasswordToggle}
                />

                {/* Remember & Forgot */}
                <div className="flex items-center justify-between py-1">
                    <Checkbox
                        checked={rememberMe}
                        onChange={onRememberMeChange}
                        label="Remember me"
                        disabled={isLoading}
                    />

                    <Link
                        href="/forgot"
                        className="text-[var(--forge-orange)] hover:text-[var(--spark-yellow)]
                                 text-sm transition-colors
                                 focus:outline-none focus:underline"
                    >
                        Forgot password?
                    </Link>
                </div>

                {/* Submit Button */}
                <Button
                    type="submit"
                    variant="primary"
                    disabled={isLoading}
                    loading={isLoading}
                    fullWidth
                    className="mt-5"
                    onClick={() => onSubmit({} as React.FormEvent)}
                >
                    {isLoading ? 'Signing in...' : 'Sign in'}
                </Button>
            </div>
        </div>
    );
}
