import {GenericApiError, GenericApiErrorData} from "@/types/auth";

class ApiClient {
    private readonly baseURL: string;
    private isRefreshing = false;
    private failedQueue: Array<{
        resolve: (value: string) => void;
        reject: (error: unknown) => void;
    }> = [];

    constructor(baseURL: string = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000') {
        this.baseURL = baseURL;
    }

    private getAuthToken(): string | null {
        if (typeof window === 'undefined') return null;
        return localStorage.getItem('smithy_access_token');
    }

    private getRefreshToken(): string | null {
        if (typeof window === 'undefined') return null;
        return localStorage.getItem('smithy_refresh_token');
    }

    private setTokens(accessToken: string, refreshToken: string): void {
        if (typeof window === 'undefined') return;
        localStorage.setItem('smithy_access_token', accessToken);
        localStorage.setItem('smithy_refresh_token', refreshToken);
    }

    private clearTokens(): void {
        if (typeof window === 'undefined') return;
        localStorage.removeItem('smithy_access_token');
        localStorage.removeItem('smithy_refresh_token');
        localStorage.removeItem('smithy_user');
    }

    private processQueue(error: unknown, token: string | null = null): void {
        this.failedQueue.forEach(({ resolve, reject }) => {
            if (error) {
                reject(error);
            } else if (token) {
                resolve(token);
            }
        });

        this.failedQueue = [];
    }

    private async refreshAccessToken(): Promise<string> {
        const refreshToken = this.getRefreshToken();

        if (!refreshToken) {
            throw new Error('No refresh token available');
        }

        try {
            const response = await fetch(`${this.baseURL}/v1/auth/refresh`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ refresh_token: refreshToken }),
            });

            if (!response.ok) {
                throw new Error('Token refresh failed');
            }

            const data = await response.json();
            this.setTokens(data.access_token, data.refresh_token);

            // Update user data if present
            if (data.user && typeof window !== 'undefined') {
                localStorage.setItem('smithy_user', JSON.stringify(data.user));
            }

            return data.access_token;
        } catch (error) {
            this.clearTokens();
            if (typeof window !== 'undefined') {
                window.location.href = '/login';
            }
            throw error;
        }
    }

    async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
        const url = `${this.baseURL}/v1${endpoint}`;
        let token = this.getAuthToken();

        // If we're already refreshing, queue this request
        if (this.isRefreshing) {
            return new Promise((resolve, reject) => {
                this.failedQueue.push({
                    resolve: (newToken: string) => {
                        resolve(this.executeRequest<T>(url, options, newToken));
                    },
                    reject: (error: unknown) => {
                        reject(error);
                    },
                });
            });
        }

        try {
            return await this.executeRequest<T>(url, options, token);
        } catch (error) {
            if (error instanceof GenericApiError && this.isUnauthorizedError(error)) {
                if (endpoint === '/auth/refresh') {
                    this.clearTokens();
                    throw error;
                }

                if (this.isRefreshing) {
                    // If already refreshing, queue this request
                    return new Promise((resolve, reject) => {
                        this.failedQueue.push({
                            resolve: (newToken: string) => {
                                resolve(this.executeRequest<T>(url, options, newToken));
                            },
                            reject: (err: unknown) => {
                                reject(err);
                            },
                        });
                    });
                }

                this.isRefreshing = true;

                try {
                    const newToken = await this.refreshAccessToken();
                    this.processQueue(null, newToken);
                    return await this.executeRequest<T>(url, options, newToken);
                } catch (refreshError) {
                    this.processQueue(refreshError, null);
                    throw refreshError;
                } finally {
                    this.isRefreshing = false;
                }
            }

            throw error;
        }
    }

    private async executeRequest<T>(
        url: string,
        options: RequestInit,
        token: string | null
    ): Promise<T> {
        const config: RequestInit = {
            headers: {
                'Content-Type': 'application/json',
                ...(token && { Authorization: `Bearer ${token}` }),
                ...options.headers,
            },
            ...options,
        };

        const response = await fetch(url, config);

        if (!response.ok) {
            const errorData: GenericApiErrorData = await response.json().catch(() => ({}));
            const error = new GenericApiError(
                errorData.message || `Request failed with status ${response.status}`,
                errorData
            );

            (error as GenericApiError & { statusCode: number }).statusCode = response.status;

            throw error;
        }

        return await response.json();
    }

    private isUnauthorizedError(error: GenericApiError): boolean {
        return (error as GenericApiError & { statusCode?: number }).statusCode === 401;
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