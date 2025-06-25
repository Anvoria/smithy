interface FormFieldProps {
    label: string;
    type?: 'text' | 'email' | 'password';
    value: string;
    onChange: (value: string) => void;
    placeholder?: string;
    error?: string;
    disabled?: boolean;
    autoFocus?: boolean;
    autoComplete?: string;
    maxLength?: number;
    className?: string;
    showPasswordToggle?: boolean;
    showPassword?: boolean;
    onPasswordToggle?: () => void;
}

import { Eye, EyeOff } from 'lucide-react';

export function FormField({
    label,
    type = 'text',
    value,
    onChange,
    placeholder,
    error,
    disabled = false,
    autoFocus = false,
    autoComplete,
    maxLength,
    className = '',
    showPasswordToggle = false,
    showPassword = false,
    onPasswordToggle,
}: FormFieldProps) {
    const inputType = type === 'password' && showPassword ? 'text' : type;

    return (
        <div>
            <label className="block text-[var(--ash-gray)] text-sm mb-2">{label}</label>
            <div className="relative">
                <input
                    type={inputType}
                    value={value}
                    onChange={(e) => onChange(e.target.value)}
                    className={`w-full p-3 ${showPasswordToggle ? 'pr-12' : ''} bg-[var(--iron-gray)] text-white border-0 rounded-lg focus:outline-none focus:ring-2 transition-all duration-200 ${
                        error
                            ? 'ring-2 ring-[var(--molten-red)]'
                            : 'focus:ring-[var(--forge-orange)]'
                    } ${className}`}
                    placeholder={placeholder}
                    autoFocus={autoFocus}
                    autoComplete={autoComplete}
                    disabled={disabled}
                    maxLength={maxLength}
                />
                {showPasswordToggle && onPasswordToggle && (
                    <button
                        type="button"
                        onClick={onPasswordToggle}
                        className="absolute right-3 top-1/2 transform -translate-y-1/2 text-[var(--ash-gray)] hover:text-white transition-colors p-1 cursor-pointer"
                        disabled={disabled}
                    >
                        {showPassword ? (
                            <EyeOff className="w-4 h-4" />
                        ) : (
                            <Eye className="w-4 h-4" />
                        )}
                    </button>
                )}
            </div>
            {error && <p className="mt-1 text-[var(--molten-red)] text-xs">{error}</p>}
        </div>
    );
}
