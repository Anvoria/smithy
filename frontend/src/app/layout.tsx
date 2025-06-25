import type { Metadata } from 'next';
import './globals.css';
import GlobalProviders from '@/app/providers';

export const metadata: Metadata = {
    title: "Smithy | Forge Your Workflow",
    description: "A minimalist, atmospheric project management platform built for developers, freelancers, and builders who are tired of boring, bloated tools.",
    keywords: [
        "project management",
        "task management",
        "developer tools",
        "freelancer",
        "productivity",
        "open source",
        "minimalist",
        "workflow"
    ],
    authors: [{ name: "Anvoria" }],
    creator: "Smithy",
    publisher: "Smithy",
    formatDetection: {
        email: false,
        address: false,
        telephone: false,
    },
    metadataBase: new URL("https://smithy.sh"),
    alternates: {
        canonical: "/",
    },
    openGraph: {
        title: "Smithy | Forge Your Workflow",
        description: "A minimalist, atmospheric project management platform built for developers, freelancers, and builders.",
        url: "https://smithy.sh",
        siteName: "Smithy",
        type: "website",
        locale: "en_US",
        images: [
            {
                url: "/og-image.jpg",
                width: 1200,
                height: 630,
                alt: "Smithy - Forge Your Workflow",
            },
        ],
    },
    twitter: {
        card: "summary_large_image",
        title: "Smithy | Forge Your Workflow",
        description: "A minimalist, atmospheric project management platform built for developers, freelancers, and builders.",
        images: ["/og-image.jpg"],
    },
    robots: {
        index: true,
        follow: true,
        googleBot: {
            index: true,
            follow: true,
            "max-video-preview": -1,
            "max-image-preview": "large",
            "max-snippet": -1,
        },
    },
    icons: {
        icon: [
            { url: "/favicon-16x16.png", sizes: "16x16", type: "image/png" },
            { url: "/favicon-32x32.png", sizes: "32x32", type: "image/png" },
        ],
        apple: [
            { url: "/apple-touch-icon.png", sizes: "180x180", type: "image/png" },
        ],
    },
    // manifest: "/site.webmanifest",
};

export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <html lang="en" className="scroll-smooth">
            <body className="antialiased bg-forge-charcoal text-white overflow-x-hidden">
                <GlobalProviders>{children}</GlobalProviders>
            </body>
        </html>
    );
}
