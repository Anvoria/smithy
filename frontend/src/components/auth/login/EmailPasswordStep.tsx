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
        <div>
            {/* Header */}
            <div className="mb-8">
                <h2 className="font-machina text-3xl font-medium text-white mb-2">Login</h2>
                <p className="text-[var(--ash-gray)] text-sm">Enter your credentials</p>
            </div>

            {/* General Error */}
            {errors.general && <ErrorMessage message={errors.general} className="mb-6" />}

            {/* Form */}
            <form onSubmit={onSubmit} onKeyDown={onKeyDown} className="space-y-5">
                {/* Email */}
                <FormField
                    label="Email"
                    type="email"
                    value={email}
                    onChange={onEmailChange}
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
                    value={password}
                    onChange={onPasswordChange}
                    placeholder="Enter your password"
                    error={errors.password}
                    disabled={isLoading}
                    autoComplete="current-password"
                    showPasswordToggle
                    showPassword={showPassword}
                    onPasswordToggle={onPasswordToggle}
                />

                {/* Remember & Forgot */}
                <div className="flex items-center justify-between text-sm">
                    <Checkbox
                        checked={rememberMe}
                        onChange={onRememberMeChange}
                        label="Remember me"
                        disabled={isLoading}
                    />

                    <Link
                        href="/forgot"
                        className="text-[var(--forge-orange)] hover:text-[var(--spark-yellow)] transition-colors py-2 px-1 cursor-pointer"
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
                    className="mt-6"
                >
                    {isLoading ? 'Logging in...' : 'Login'}
                </Button>
            </form>
        </div>
    );
}
