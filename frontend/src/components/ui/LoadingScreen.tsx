import { AnimatedLogo } from '@/components/ui/AnimatedLogo';

interface LoadingScreenProps {
    message?: string;
}

export function LoadingScreen({ message = 'Loading...' }: LoadingScreenProps) {
    return (
        <div className="min-h-screen bg-[var(--charcoal-black)] flex items-center justify-center">
            <div className="text-center">
                <div className="mb-6">
                    <AnimatedLogo />
                </div>

                <p className="text-[var(--ash-gray)] font-medium">{message}</p>
            </div>
        </div>
    );
}
