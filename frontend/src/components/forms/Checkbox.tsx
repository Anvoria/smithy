import { Check } from 'lucide-react';

interface CheckboxProps {
    checked: boolean;
    onChange: (checked: boolean) => void;
    label: string;
    disabled?: boolean;
}

export function Checkbox({ checked, onChange, label, disabled = false }: CheckboxProps) {
    return (
        <label className="flex items-center cursor-pointer group py-2">
            <div className="relative">
                <input
                    type="checkbox"
                    checked={checked}
                    onChange={(e) => onChange(e.target.checked)}
                    className="sr-only"
                    disabled={disabled}
                />
                <div
                    className={`w-4 h-4 rounded transition-colors duration-200 ${
                        checked
                            ? 'bg-[var(--forge-orange)]'
                            : 'bg-[var(--coal-shadow)] group-hover:bg-[var(--iron-gray)]'
                    }`}
                >
                    {checked && (
                        <Check className="w-3 h-3 text-[var(--charcoal-black)] absolute top-0.5 left-0.5" />
                    )}
                </div>
            </div>
            <span className="ml-3 text-[var(--ash-gray)] group-hover:text-white transition-colors">
        {label}
      </span>
        </label>
    );
}