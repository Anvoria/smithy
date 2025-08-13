import { Check } from 'lucide-react';

interface CheckboxProps {
    checked: boolean;
    onChange: (checked: boolean) => void;
    label: string;
    disabled?: boolean;
}

export function Checkbox({ checked, onChange, label, disabled = false }: CheckboxProps) {
    return (
        <label
            className={`
            flex items-center group cursor-pointer
            ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
        `}
        >
            <div className="relative flex-shrink-0">
                <input
                    type="checkbox"
                    checked={checked}
                    onChange={(e) => onChange(e.target.checked)}
                    className="sr-only"
                    disabled={disabled}
                />
                <div
                    className={`
                        w-4 h-4 rounded-sm border transition-all duration-200 ease-out
                        flex items-center justify-center
                        ${
                            checked
                                ? 'bg-[var(--forge-orange)] border-[var(--forge-orange)] scale-100'
                                : 'bg-transparent border-gray-600/50 group-hover:border-gray-500/70 group-hover:bg-gray-800/30'
                        }
                        ${!disabled && 'group-active:scale-95'}
                        focus-within:ring-2 focus-within:ring-[var(--forge-orange)]/30
                    `}
                >
                    <Check
                        className={`
                            w-3 h-3 text-[var(--charcoal-black)] 
                            transition-all duration-150 ease-out
                            ${checked ? 'opacity-100 scale-100' : 'opacity-0 scale-75'}
                        `}
                    />
                </div>
            </div>
            <span
                className={`
                ml-2.5 text-sm leading-tight
                transition-colors duration-200
                ${disabled ? 'text-gray-500' : 'text-[var(--ash-gray)] group-hover:text-gray-300'}
            `}
            >
                {label}
            </span>
        </label>
    );
}
