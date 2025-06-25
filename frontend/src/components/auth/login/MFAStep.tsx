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
        <div>
            {/* Header */}
            <div className="mb-8">
                <h2 className="font-machina text-3xl font-medium text-white mb-2">
                    Enter MFA Code
                </h2>
                <p className="text-[var(--ash-gray)] text-sm">
                    Enter the 6-digit code from your authenticator app
                </p>
            </div>

            {/* General Error */}
            {generalError && <ErrorMessage message={generalError} className="mb-6" />}

            {/* Form */}
            <form onSubmit={onSubmit} onKeyDown={onKeyDown} className="space-y-5">
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
                    className="text-center font-mono text-lg tracking-widest"
                />

                {/* Submit Button */}
                <Button
                    type="submit"
                    variant="primary"
                    disabled={isLoading}
                    loading={isLoading}
                    fullWidth
                    className="mt-6"
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
                >
                    Back to Login
                </Button>
            </form>
        </div>
    );
}
