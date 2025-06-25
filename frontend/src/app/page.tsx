import {AuthGuard} from "@/components/auth/AuthGuard";

export default function Home() {
    return (
        <AuthGuard>
            <div className="flex flex-col items-center justify-center min-h-screen">
                <h1 className="text-4xl font-bold mb-4">Welcome to the Home Page</h1>
                <p className="text-lg">This is a protected route.</p>
            </div>
        </AuthGuard>
    )
}
