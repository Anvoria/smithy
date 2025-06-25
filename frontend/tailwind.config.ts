import type { Config } from "tailwindcss";

const config: Config = {
    content: [
        "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
        "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
    ],
    theme: {
        extend: {
            colors: {
                forge: {
                    orange: '#F18424',
                    charcoal: '#0D0D0D',
                    iron: '#2E2E2E',
                    ash: '#A2A2A2',
                    shadow: '#1A1A1A',
                    spark: '#FFCE5B',
                    molten: '#D9481F',
                }
            },
            fontFamily: {
                mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
                machina: ['PP Neue Machina', 'JetBrains Mono', 'monospace'],
                'machina-inktrap': ['PP Neue Machina Inktrap', 'JetBrains Mono', 'monospace'],
                'machina-plain': ['PP Neue Machina Plain', 'JetBrains Mono', 'monospace'],
                display: ['PP Neue Machina Inktrap', 'JetBrains Mono', 'monospace'],
            },
        },
    },
    plugins: [],
};

export default config;