export interface User {
    id: string;
    email: string;
    username?: string;
    role: 'admin' | 'moderator' | 'user' | 'guest';
    is_verified: boolean;
    is_active: boolean;
    full_name?: string;
    avatar_url?: string;
    first_name?: string;
    last_name?: string;
    display_name?: string;
    bio?: string;
    timezone?: string;
    locale?: string;
    mfa_enabled?: boolean;
    login_provider?: string;
    created_at: string;
    updated_at: string;
}

export interface LoginRequest {
    email: string;
    password: string;
    mfa_code?: string;
    remember_me?: boolean;
}

export interface RegisterRequest {
    email: string;
    password: string;
    first_name?: string;
    last_name?: string;
    username?: string;
}

export interface TokenResponse {
    access_token: string;
    refresh_token: string;
    token_type: string;
    expires_in: number;
    user: User;
}

export interface RefreshTokenRequest {
    refresh_token: string;
}

export interface LogoutRequest {
    refresh_token?: string;
}

export interface MFARequiredResponse {
    message: string;
    requires_mfa: boolean;
    partial_auth_token?: string;
}

export interface MFALoginRequest {
    partial_auth_token: string;
    mfa_code: string;
}

export interface AuthState {
    user: User | null;
    isAuthenticated: boolean;
    isLoading: boolean;
}

export interface MFARequiredErrorResponse {
    message: string;
    details: {
        required_mfa: true;
        partial_auth_token: string;
    };
}

// API Response wrappers
export interface ApiResponse<T> {
    success: boolean;
    message: string;
    data: T;
    timestamp: string;
}

export interface ApiError {
    error: boolean;
    message: string;
    code: string;
    status_code: number;
    timestamp: string;
    details?: Record<string, unknown>;
}

export interface GenericApiErrorData {
    message?: string;
    details?: {
        required_mfa?: boolean;
        partial_auth_token?: string;
        [key: string]: unknown;
    };
    [key: string]: unknown;
}

export class GenericApiError extends Error {
    responseData: GenericApiErrorData;

    constructor(message: string, responseData: GenericApiErrorData) {
        super(message);
        this.name = 'GenericApiError';
        this.responseData = responseData;
    }
}