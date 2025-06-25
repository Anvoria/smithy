import { GuestGuard } from '@/components/auth/GuestGuard';
import LoginForm from '@/components/auth/login/LoginForm';

export default function LoginPage() {
    return (
        <GuestGuard>
            <LoginForm />
        </GuestGuard>
    );
}
