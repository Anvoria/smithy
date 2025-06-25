import { GuestGuard } from '@/components/auth/GuestGuard';
import LoginForm from '@/components/auth/LoginForm';

export default function LoginPage() {
    return (
        <GuestGuard>
            <LoginForm />
        </GuestGuard>
    );
}
