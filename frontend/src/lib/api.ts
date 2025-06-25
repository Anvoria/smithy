import {GenericApiError, GenericApiErrorData} from "@/types/auth";

class ApiClient {
    private readonly baseURL: string;

    constructor(baseURL: string = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000') {
        this.baseURL = baseURL;
    }

    private getAuthToken(): string | null {
        if (typeof window === 'undefined') return null;
        return localStorage.getItem('smithy_access_token');
    }

    async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
        const url = `${this.baseURL}/v1${endpoint}`;
        const token = this.getAuthToken();

        const config: RequestInit = {
            headers: {
                'Content-Type': 'application/json',
                ...(token && { Authorization: `Bearer ${token}` }),
                ...options.headers,
            },
            ...options,
        };

        try {
            const response = await fetch(url, config);

            if (!response.ok) {
                const errorData: GenericApiErrorData = await response.json().catch(() => ({}));
                throw new GenericApiError(errorData.message || `Request failed`, errorData);
            }

            return await response.json();
        } catch (error) {
            console.error('API request failed:', error);
            throw error;
        }
    }

    // Generic HTTP methods
    async get<T>(endpoint: string, options?: RequestInit): Promise<T> {
        return this.request<T>(endpoint, { method: 'GET', ...options });
    }

    async post<T, D = unknown>(endpoint: string, data?: D, options?: RequestInit): Promise<T> {
        return this.request<T>(endpoint, {
            method: 'POST',
            body: data ? JSON.stringify(data) : undefined,
            ...options,
        });
    }

    async put<T, D = unknown>(endpoint: string, data?: D, options?: RequestInit): Promise<T> {
        return this.request<T>(endpoint, {
            method: 'PUT',
            body: data ? JSON.stringify(data) : undefined,
            ...options,
        });
    }

    async patch<T, D = unknown>(endpoint: string, data?: D, options?: RequestInit): Promise<T> {
        return this.request<T>(endpoint, {
            method: 'PATCH',
            body: data ? JSON.stringify(data) : undefined,
            ...options,
        });
    }

    async delete<T>(endpoint: string, options?: RequestInit): Promise<T> {
        return this.request<T>(endpoint, { method: 'DELETE', ...options });
    }
}

export const apiClient = new ApiClient();
