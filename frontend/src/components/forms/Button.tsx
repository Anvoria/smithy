import { Loader2 } from 'lucide-react';

interface ButtonProps {
    children: React.ReactNode;
    type?: 'button' | 'submit';
    variant?: 'primary' | 'secondary';
    disabled?: boolean;
    loading?: boolean;
    onClick?: () => void;
    className?: string;
    fullWidth?: boolean;
}

export function Button({
    children,
    type = 'button',
    variant = 'primary',
    disabled = false,
    loading = false,
    onClick,
    className = '',
    fullWidth = false,
}: ButtonProps) {
    const baseClasses = `
        px-4 py-2.5 text-sm font-medium 
        rounded-lg 
        transition-all duration-200 ease-out
        flex items-center justify-center gap-2
        focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-transparent
        disabled:opacity-60 disabled:cursor-not-allowed 
        disabled:transform-none disabled:hover:scale-100
        active:scale-[0.98]
    `;

    const variantClasses = {
        primary: `
            bg-[var(--forge-orange)] text-[var(--charcoal-black)] 
            hover:bg-[var(--spark-yellow)] hover:scale-[1.01]
            focus:ring-[var(--forge-orange)]/40
            shadow-sm hover:shadow-md
        `,
        secondary: `
            bg-[var(--coal-shadow)] text-white border border-gray-600/30
            hover:bg-[var(--iron-gray)] hover:border-gray-500/40
            focus:ring-gray-500/40
            shadow-sm hover:shadow
        `,
    };

    const widthClass = fullWidth ? 'w-full' : '';

    return (
        <button
            type={type}
            disabled={disabled || loading}
            onClick={onClick}
            className={`${baseClasses} ${variantClasses[variant]} ${widthClass} ${className}`.trim()}
        >
            {loading && <Loader2 className="w-4 h-4 animate-spin" />}
            <span className={loading ? 'opacity-75' : ''}>{children}</span>
        </button>
    );
}
