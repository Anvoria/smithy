interface ErrorMessageProps {
    message: string;
    className?: string;
}

export function ErrorMessage({ message, className = '' }: ErrorMessageProps) {
    return (
        <div
            className={`p-3 bg-[var(--molten-red)]/10 border border-[var(--molten-red)]/30 text-[var(--molten-red)] text-sm rounded-lg ${className}`}
        >
            {message}
        </div>
    );
}
