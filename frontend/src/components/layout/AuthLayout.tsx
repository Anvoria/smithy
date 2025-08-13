import Image from 'next/image';

interface AuthLayoutProps {
    children: React.ReactNode;
}

export function AuthLayout({ children }: AuthLayoutProps) {
    return (
        <div className="min-h-screen bg-gradient-to-br from-[var(--charcoal-black)] via-[var(--charcoal-black)] to-[var(--coal-shadow)] flex items-center justify-center p-4">
            <div className="w-full max-w-sm">
                <div className="text-center mb-8">
                    <div className="flex items-center justify-center space-x-2 mb-2">
                        <Image
                            src="/images/logo-64.svg"
                            alt="Smithy"
                            width={24}
                            height={24}
                            className="w-6 h-6"
                        />
                        <span className="font-machina text-lg font-bold text-white">Smithy</span>
                    </div>
                </div>

                {children}
            </div>
        </div>
    );
}
