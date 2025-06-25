import Image from 'next/image';

interface AuthLayoutProps {
    children: React.ReactNode;
}

export function AuthLayout({ children }: AuthLayoutProps) {
    return (
        <div className="min-h-screen bg-[var(--charcoal-black)] lg:grid lg:grid-cols-2">
            {/* Left Side */}
            <div className="hidden lg:flex lg:flex-col lg:justify-center px-16 bg-[var(--coal-shadow)]">
                <div className="max-w-md mx-auto">
                    <div className="flex items-center space-x-4 mb-12">
                        <Image
                            src="/images/logo-64.svg"
                            alt="Smithy"
                            width={48}
                            height={48}
                            className="w-12 h-12"
                        />
                        <span className="font-machina text-4xl font-black text-white">Smithy</span>
                    </div>

                    <h1 className="font-machina text-5xl font-black text-white mb-6 leading-tight">
                        Forge your
                        <br />
                        <span className="text-[var(--forge-orange)]">workflow</span>
                    </h1>

                    <p className="text-lg text-[var(--ash-gray)] mb-8 leading-relaxed">
                        Self-hosted project management built for developers.
                    </p>

                    <div className="text-[var(--ash-gray)]">
                        <ul className="list-disc pl-5">
                            <li>Open source</li>
                            <li>Minimal interface</li>
                            <li>Developer-first</li>
                        </ul>
                    </div>
                </div>
            </div>

            {/* Right Side */}
            <div className="flex items-center justify-center px-6 py-12">
                <div className="w-full max-w-sm">
                    {/* Mobile Logo */}
                    <div className="lg:hidden text-center mb-8">
                        <div className="flex items-center justify-center space-x-3 mb-4">
                            <Image
                                src="/images/logo-64.svg"
                                alt="Smithy"
                                width={32}
                                height={32}
                                className="w-8 h-8"
                            />
                            <span className="font-machina text-2xl font-black text-white">
                                Smithy
                            </span>
                        </div>
                    </div>

                    {children}
                </div>
            </div>
        </div>
    );
}
