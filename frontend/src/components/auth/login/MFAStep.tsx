import { FormField } from '@/components/forms/FormField';
import { Button } from '@/components/forms/Button';
import { ErrorMessage } from '@/components/ui/ErrorMessage';

interface MFAStepProps {
    mfaCode: string;
    error?: string;
    generalError?: string;
    isLoading: boolean;
    onMfaCodeChange: (code: string) => void;
    onSubmit: (e: React.FormEvent) => void;
    onBack: () => void;
    onKeyDown: (e: React.KeyboardEvent) => void;
}

export function MFAStep({
    mfaCode,
    error,
    generalError,
    isLoading,
    onMfaCodeChange,
    onSubmit,
    onBack,
    onKeyDown,
}: MFAStepProps) {
    const handleMfaCodeChange = (value: string) => {
        // Only allow digits, max 6 characters
        const cleanValue = value.replace(/\D/g, '').slice(0, 6);
        onMfaCodeChange(cleanValue);
    };

    return (
        <div className="w-full max-w-sm mx-auto">
            {/* Header  */}
            <div className="text-center mb-6">
                <h2 className="font-machina text-2xl font-medium text-white mb-1">Verification</h2>
                <p className="text-[var(--ash-gray)] text-sm">
                    Enter your 6-digit authentication code
                </p>
            </div>

            {/* General Error */}
            {generalError && (
                <div className="mb-4">
                    <ErrorMessage message={generalError} />
                </div>
            )}

            {/* Form */}
            <div className="space-y-4" onKeyDown={onKeyDown}>
                {/* MFA Code */}
                <FormField
                    label="Authentication Code"
                    type="text"
                    value={mfaCode}
                    onChange={handleMfaCodeChange}
                    placeholder="000000"
                    error={error}
                    disabled={isLoading}
                    autoFocus
                    autoComplete="one-time-code"
                    maxLength={6}
                    className="text-center font-mono text-lg tracking-[0.3em] font-medium"
                />

                {/* Helper text */}
                <p className="text-xs text-[var(--ash-gray)] text-center">
                    Check your authenticator app for the code
                </p>

                {/* Submit Button */}
                <Button
                    type="submit"
                    variant="primary"
                    disabled={isLoading || mfaCode.length !== 6}
                    loading={isLoading}
                    fullWidth
                    className="mt-5"
                    onClick={() => onSubmit({} as React.FormEvent)}
                >
                    {isLoading ? 'Verifying...' : 'Verify Code'}
                </Button>

                {/* Back Button */}
                <Button
                    type="button"
                    variant="secondary"
                    onClick={onBack}
                    disabled={isLoading}
                    fullWidth
                    className="mt-3"
                >
                    Back to Login
                </Button>
            </div>

            {/* Backup codes hint */}
            <div className="mt-6 text-center">
                <p className="text-xs text-[var(--ash-gray)]">
                    Lost your device?{' '}
                    <button
                        type="button"
                        className="text-[var(--forge-orange)] hover:text-[var(--spark-yellow)] transition-colors focus:outline-none focus:underline"
                        disabled={isLoading}
                    >
                        Use backup code
                    </button>
                </p>
            </div>
        </div>
    );
}
