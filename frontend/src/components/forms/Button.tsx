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
    const baseClasses = "p-3 font-machina font-medium rounded-lg transition-all duration-200 flex items-center justify-center cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100";

    const variantClasses = {
        primary: "bg-[var(--forge-orange)] text-[var(--charcoal-black)] hover:bg-[var(--spark-yellow)] hover:scale-[1.02]",
        secondary: "bg-[var(--coal-shadow)] text-white hover:bg-[var(--iron-gray)]"
    };

    const widthClass = fullWidth ? 'w-full' : '';

    return (
        <button
            type={type}
            disabled={disabled || loading}
            onClick={onClick}
            className={`${baseClasses} ${variantClasses[variant]} ${widthClass} ${className}`}
        >
            {loading ? (
                <>
                    <Loader2 className="w-4 h-4 animate-spin mr-2" />
                    {children}
                </>
            ) : (
                children
            )}
        </button>
    );
}