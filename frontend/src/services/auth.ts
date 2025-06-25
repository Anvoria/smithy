import { apiClient } from '@/lib/api';
import {
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    User,
    RefreshTokenRequest,
    LogoutRequest,
    MFARequiredResponse,
    MFALoginRequest,
    ApiResponse,
} from '@/types/auth';

export class AuthService {
    private static ACCESS_TOKEN_KEY = 'smithy_access_token';
    private static REFRESH_TOKEN_KEY = 'smithy_refresh_token';
    private static USER_KEY = 'smithy_user';

    static getTokens() {
        if (typeof window === 'undefined') return { accessToken: null, refreshToken: null };

        return {
            accessToken: localStorage.getItem(this.ACCESS_TOKEN_KEY),
            refreshToken: localStorage.getItem(this.REFRESH_TOKEN_KEY),
        };
    }

    static getUser(): User | null {
        if (typeof window === 'undefined') return null;

        const userJson = localStorage.getItem(this.USER_KEY);
        return userJson ? JSON.parse(userJson) : null;
    }

    static setAuth(tokenResponse: TokenResponse) {
        localStorage.setItem(this.ACCESS_TOKEN_KEY, tokenResponse.access_token);
        localStorage.setItem(this.REFRESH_TOKEN_KEY, tokenResponse.refresh_token);
        localStorage.setItem(this.USER_KEY, JSON.stringify(tokenResponse.user));
    }

    static clearAuth() {
        localStorage.removeItem(this.ACCESS_TOKEN_KEY);
        localStorage.removeItem(this.REFRESH_TOKEN_KEY);
        localStorage.removeItem(this.USER_KEY);
    }

    static isAuthenticated(): boolean {
        const { accessToken } = this.getTokens();
        return !!accessToken;
    }

    static async login(data: LoginRequest): Promise<TokenResponse | MFARequiredResponse> {
        try {
            const response = await apiClient.post<TokenResponse>('/auth/login', data);

            this.setAuth(response);
            return response;

        } catch (error: any) {
            const responseData = error.responseData;

            if (responseData?.details?.required_mfa) {
                return {
                    requires_mfa: true,
                    message: responseData.message,
                    partial_auth_token: responseData.details.partial_auth_token
                };
            }

            throw error;
        }
    }

    static async completeMFALogin(data: MFALoginRequest): Promise<TokenResponse> {
        const response = await apiClient.post<TokenResponse>('/auth/mfa/complete', data);
        this.setAuth(response);
        return response;
    }

    static async register(data: RegisterRequest): Promise<TokenResponse> {
        const response = await apiClient.post<TokenResponse>('/auth/register', data);
        this.setAuth(response);
        return response;
    }

    static async logout(): Promise<void> {
        const { refreshToken } = this.getTokens();

        try {
            if (refreshToken) {
                const logoutData: LogoutRequest = { refresh_token: refreshToken };
                await apiClient.post('/auth/logout', logoutData);
            }
        } catch (error) {
            console.error('Logout error:', error);
        } finally {
            this.clearAuth();
        }
    }

    static async refreshTokens(): Promise<boolean> {
        const { refreshToken } = this.getTokens();

        if (!refreshToken) return false;

        try {
            const refreshData: RefreshTokenRequest = { refresh_token: refreshToken };
            const response = await apiClient.post<TokenResponse>('/auth/refresh', refreshData);
            this.setAuth(response);
            return true;
        } catch (error) {
            console.error('Token refresh failed:', error);
            this.clearAuth();
            return false;
        }
    }

    static async getCurrentUser(): Promise<User> {
        const response = await apiClient.get<ApiResponse<User>>('/users/me');
        return response.data;
    }

    // Remember email functionality
    static getRememberedEmail(): string | null {
        if (typeof window === 'undefined') return null;
        return localStorage.getItem('smithy_remembered_email');
    }

    static setRememberedEmail(email: string) {
        localStorage.setItem('smithy_remembered_email', email);
    }

    static clearRememberedEmail() {
        localStorage.removeItem('smithy_remembered_email');
    }
}
