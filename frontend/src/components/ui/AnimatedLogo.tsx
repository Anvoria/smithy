'use client';

export function AnimatedLogo() {
    return (
        <div className="w-72 h-72 relative">
            <svg
                viewBox="0 0 1080 1080"
                className="w-full h-full"
                xmlns="http://www.w3.org/2000/svg"
            >
                <style jsx>{`
                    path {
                        fill: none;
                        stroke: var(--forge-orange);
                        stroke-width: 3;
                        stroke-linecap: round;
                        stroke-linejoin: round;
                        stroke-dasharray: 1500;
                        stroke-dashoffset: 1500;
                        opacity: 0;
                    }

                    @keyframes draw {
                        0% {
                            stroke-dashoffset: 1500;
                            opacity: 0;
                            filter: brightness(0.5);
                        }
                        20% {
                            opacity: 1;
                            filter: brightness(1);
                        }
                        60% {
                            stroke-dashoffset: 0;
                            opacity: 1;
                            filter: brightness(1.2);
                        }
                        80% {
                            stroke-dashoffset: 0;
                            opacity: 1;
                            filter: brightness(1);
                        }
                        100% {
                            stroke-dashoffset: -1500;
                            opacity: 0;
                            filter: brightness(0.5);
                        }
                    }

                    @keyframes sparkGlow {
                        0%,
                        100% {
                            filter: brightness(1) drop-shadow(0 0 5px var(--forge-orange));
                        }
                        50% {
                            filter: brightness(1.5) drop-shadow(0 0 15px var(--spark-yellow))
                                drop-shadow(0 0 25px var(--forge-orange));
                        }
                    }

                    .main-hammer {
                        animation: draw 4s ease-in-out infinite;
                        animation-delay: 0s;
                    }

                    .handle {
                        animation: draw 4s ease-in-out infinite;
                        animation-delay: 0.3s;
                    }

                    .spark-1 {
                        animation:
                            draw 4s ease-in-out infinite,
                            sparkGlow 4s ease-in-out infinite;
                        animation-delay: 0.6s;
                        stroke: var(--spark-yellow);
                        stroke-width: 4;
                    }

                    .spark-2 {
                        animation:
                            draw 4s ease-in-out infinite,
                            sparkGlow 4s ease-in-out infinite;
                        animation-delay: 0.9s;
                        stroke: var(--spark-yellow);
                        stroke-width: 4;
                    }

                    .spark-3 {
                        animation:
                            draw 4s ease-in-out infinite,
                            sparkGlow 4s ease-in-out infinite;
                        animation-delay: 1.2s;
                        stroke: var(--spark-yellow);
                        stroke-width: 4;
                    }
                `}</style>

                <g>
                    <g>
                        <path
                            className="main-hammer"
                            d="M488.24,469.78c1.47,0,2.74,0,4.01,0c53.81,0,107.61,0,161.42,0.01c5.4,0,5.49,0.02,5.42,5.53
                c-0.12,9.64,1.88,8.29-8.71,12.97c-17.65,7.79-35.29,15.6-52.87,23.54c-7.81,3.52-14.88,8.13-19.81,15.41
                c-7.49,11.07-5.46,24.11,4.99,32.39c5.45,4.32,11.75,6.91,18.26,8.99c3.05,0.97,4.52,2.46,4.33,5.78c-0.21,3.64,0,7.3-0.04,10.95
                c-0.03,3.42-0.73,4.2-4.14,4.22c-11.18,0.05-22.37-0.05-33.55,0.05c-2.41,0.02-3.19-1.5-4.18-3.13
                c-6.53-10.71-17.57-15.16-29.41-11.82c-6.68,1.88-11.73,5.95-15.02,12.02c-1.17,2.16-2.6,2.92-5.01,2.9
                c-10.83-0.1-21.66-0.02-32.49-0.03c-3.79,0-4.28-0.5-4.33-4.27c-0.05-3.77,0.07-7.54-0.13-11.3c-0.16-3,1.18-4.37,3.92-5.36
                c4.96-1.79,9.98-3.61,14.6-6.11c10.02-5.44,14.95-14.91,13.64-25.01c-1.24-9.5-7.84-15.38-17.39-15.37
                c-2.24,0-3.94-0.13-3.94-3.07c0.04-15.78-0.01-31.55-0.01-47.33C487.79,471.29,487.99,470.85,488.24,469.78z"
                        />

                        <path
                            className="handle"
                            d="M420.83,473.94c19.42,0,38.76,0,58.31,0c0,11.46,0,22.8,0,34.11C462.38,510.19,425.38,488.59,420.83,473.94z"
                        />

                        <path
                            className="spark-1"
                            d="M541.06,375.1c2.32,7.22,4.56,14,6.67,20.83c2.54,8.2,4.86,16.47,7.49,24.63c1.06,3.29,0.76,5.96-1.19,8.92
                c-3.87,5.89-7.3,12.08-10.92,18.14c-0.65,1.08-1.32,2.16-2.17,3.56c-0.79-1.01-1.43-1.65-1.87-2.41
                c-4.11-7.13-8.26-14.25-12.22-21.47c-0.67-1.21-1.01-3.04-0.64-4.32c4.63-15.79,9.42-31.53,14.18-47.28
                C540.41,375.62,540.54,375.56,541.06,375.1z"
                        />

                        <path
                            className="spark-2"
                            d="M552.54,452.88c3.43-5.72,4.27-12.8,11.23-16.64c8.84-4.87,17.2-10.62,25.78-15.97
                c0.78-0.49,1.64-0.85,3.13-1.62c-0.55,1.37-0.78,2.19-1.18,2.91c-5.48,9.73-11.05,19.42-16.44,29.2
                c-1.25,2.26-2.74,3.16-5.31,3.08c-5.51-0.17-11.02-0.05-16.54-0.05C552.99,453.49,552.76,453.19,552.54,452.88z"
                        />

                        <path
                            className="spark-3"
                            d="M490.02,419.22c6.68,4.12,13.36,8.24,20.04,12.36c1.1,0.68,2.11,1.57,3.28,2.06
                c8.47,3.55,12.6,10.85,16.27,18.58c0.14,0.29,0.1,0.67,0.21,1.59c-5.01,0-9.89,0.05-14.77-0.01c-8.6-0.12-6.28,1.24-10.33-6.18
                c-5.07-9.28-10.1-18.58-15.14-27.87C489.73,419.58,489.88,419.4,490.02,419.22z"
                        />
                    </g>
                </g>
            </svg>
        </div>
    );
}
