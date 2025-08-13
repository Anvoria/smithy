'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Home, ArrowLeft } from 'lucide-react';

export default function NotFound() {
    const router = useRouter();

    return (
        <div className="min-h-screen bg-gradient-to-br from-[var(--charcoal-black)] via-[var(--charcoal-black)] to-[var(--coal-shadow)] flex items-center justify-center p-4">
            <div className="text-center max-w-md mx-auto">
                <div className="mb-12 relative">
                    <div className="absolute inset-0 flex items-center justify-center opacity-10">
                        <div className="w-64 h-64 rounded-full bg-gradient-to-br from-[var(--forge-orange)] to-[var(--molten-red)] blur-3xl"></div>
                    </div>
                    <div className="relative">
                        <div className="text-9xl font-machina font-bold text-transparent bg-gradient-to-br from-[var(--forge-orange)] via-[var(--spark-yellow)] to-[var(--forge-orange)] bg-clip-text mb-6 leading-none">
                            404
                        </div>
                    </div>
                </div>

                <div className="space-y-4 mb-8">
                    <h1 className="text-3xl font-machina font-bold text-white">
                        Page Not Found
                    </h1>
                    <p className="text-[var(--ash-gray)] text-lg">
                        The forge couldn't find what you're looking for.
                    </p>
                    <p className="text-[var(--ash-gray)] text-sm">
                        The page may have been moved, deleted, or you entered the wrong URL.
                    </p>
                </div>

                <div className="flex flex-col sm:flex-row gap-3 justify-center">
                    <button
                        onClick={() => router.back()}
                        className="px-4 py-2.5 text-sm font-medium rounded-lg transition-all duration-200 ease-out
                                 flex items-center justify-center gap-2 focus:outline-none focus:ring-2 
                                 focus:ring-offset-2 focus:ring-offset-transparent active:scale-[0.98]
                                 bg-[var(--forge-orange)] text-[var(--charcoal-black)] 
                                 hover:bg-[var(--spark-yellow)] hover:scale-[1.01] focus:ring-[var(--forge-orange)]/40
                                 shadow-sm hover:shadow-md"
                    >
                        <ArrowLeft className="w-4 h-4" />
                        Go Back
                    </button>
                    
                    <Link href="/" className="inline-block">
                        <button className="px-4 py-2.5 text-sm font-medium rounded-lg transition-all duration-200 ease-out
                                         flex items-center justify-center gap-2 focus:outline-none focus:ring-2 
                                         focus:ring-offset-2 focus:ring-offset-transparent active:scale-[0.98]
                                         bg-[var(--coal-shadow)] text-white border border-gray-600/30
                                         hover:bg-[var(--iron-gray)] hover:border-gray-500/40 focus:ring-gray-500/40
                                         shadow-sm hover:shadow w-full">
                            <Home className="w-4 h-4" />
                            Home
                        </button>
                    </Link>
                </div>
            </div>
        </div>
    );
}