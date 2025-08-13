import { Eye, EyeOff } from 'lucide-react';

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
        <div className="space-y-1.5">
            <label className="block text-[var(--ash-gray)] text-xs font-medium tracking-wide uppercase">
                {label}
            </label>

            <div className="relative">
                <input
                    type={inputType}
                    value={value}
                    onChange={(e) => onChange(e.target.value)}
                    className={`
                        w-full px-3 py-2.5 text-sm
                        ${showPasswordToggle ? 'pr-10' : ''}
                        bg-[var(--iron-gray)] text-white 
                        border border-gray-700/30
                        rounded-lg
                        placeholder-gray-500
                        transition-all duration-200 ease-out
                        focus:outline-none 
                        focus:border-[var(--forge-orange)]/60
                        focus:ring-1 focus:ring-[var(--forge-orange)]/20
                        focus:bg-[var(--iron-gray)]/80
                        disabled:opacity-50 disabled:cursor-not-allowed
                        ${
                            error
                                ? 'border-red-500/60 ring-1 ring-red-500/20 focus:border-red-500 focus:ring-red-500/30'
                                : ''
                        }
                        ${className}
                    `}
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
                        className="absolute right-3 top-1/2 -translate-y-1/2
                                 text-gray-500 hover:text-gray-300
                                 transition-colors duration-200
                                 p-0.5 rounded-sm
                                 focus:outline-none focus:text-[var(--forge-orange)]
                                 disabled:opacity-50"
                        disabled={disabled}
                        tabIndex={-1}
                    >
                        {showPassword ? (
                            <EyeOff className="w-4 h-4" />
                        ) : (
                            <Eye className="w-4 h-4" />
                        )}
                    </button>
                )}
            </div>

            {error && <p className="text-red-400 text-xs leading-tight">{error}</p>}
        </div>
    );
}
