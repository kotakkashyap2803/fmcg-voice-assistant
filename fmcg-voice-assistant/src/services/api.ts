
import axios, {
    type AxiosRequestConfig,
    type InternalAxiosRequestConfig,
} from "axios";

const API_BASE_URL =
    import.meta.env.VITE_API_BASE_URL ||
    "http://127.0.0.1:8000/api/v1";

const ACCESS_TOKEN_KEY = "access_token";
const REFRESH_TOKEN_KEY = "refresh_token";

interface RefreshResponse {
    access: string;
    refresh?: string;
}

interface RetryableRequest extends InternalAxiosRequestConfig {
    _retry?: boolean;
}

// --------------------------------------------------
// Token helpers
// --------------------------------------------------

export function saveTokens(access: string, refresh: string): void {
    localStorage.setItem(ACCESS_TOKEN_KEY, access);
    localStorage.setItem(REFRESH_TOKEN_KEY, refresh);
}

export function getRefreshToken(): string | null {
    return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function clearTokens(): void {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
}

// --------------------------------------------------
// Axios instance
// --------------------------------------------------

const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        "Content-Type": "application/json",
    },
});

// Attach access token to outgoing requests.
api.interceptors.request.use((config) => {
    const accessToken = localStorage.getItem(ACCESS_TOKEN_KEY);

    if (accessToken) {
        config.headers.Authorization = `Bearer ${accessToken}`;
    }

    return config;
});

// --------------------------------------------------
// Automatic access-token refresh
// --------------------------------------------------

let refreshPromise: Promise<string> | null = null;

api.interceptors.response.use(
    (response) => response,
    async (error) => {
        const originalRequest =
            error.config as RetryableRequest | undefined;

        if (
            error.response?.status !== 401 ||
            !originalRequest ||
            originalRequest._retry ||
            originalRequest.url?.includes("/auth/refresh/")
        ) {
            return Promise.reject(error);
        }

        const refreshToken = getRefreshToken();

        if (!refreshToken) {
            clearTokens();
            window.dispatchEvent(new Event("auth:logout"));
            return Promise.reject(error);
        }

        originalRequest._retry = true;

        try {
            if (!refreshPromise) {
                refreshPromise = axios
                    .post<RefreshResponse>(
                        `${API_BASE_URL}/auth/refresh/`,
                        { refresh: refreshToken }
                    )
                    .then((response) => {
                        const newAccessToken = response.data.access;

                        localStorage.setItem(
                            ACCESS_TOKEN_KEY,
                            newAccessToken
                        );

                        if (response.data.refresh) {
                            localStorage.setItem(
                                REFRESH_TOKEN_KEY,
                                response.data.refresh
                            );
                        }

                        return newAccessToken;
                    })
                    .finally(() => {
                        refreshPromise = null;
                    });
            }

            const newAccessToken = await refreshPromise;

            originalRequest.headers.Authorization =
                `Bearer ${newAccessToken}`;

            return api(originalRequest);
        } catch (refreshError) {
            clearTokens();
            window.dispatchEvent(new Event("auth:logout"));

            return Promise.reject(refreshError);
        }
    }
);

// --------------------------------------------------
// Generic API request helper
// --------------------------------------------------

interface ApiRequestOptions extends AxiosRequestConfig {
    requiresAuth?: boolean;
    body?: unknown;
}

export async function apiRequest<T = any>(
    url: string,
    options: ApiRequestOptions = {}
): Promise<T> {
    const {
        requiresAuth = true,
        body,
        ...config
    } = options;

    // Login requests bypass the authenticated Axios instance.
    const client = requiresAuth ? api : axios;

    const response = await client.request<T>({
		...config,
		baseURL: API_BASE_URL,
		url,
		data: body,
		headers: {
			...config.headers,
			"Content-Type": "application/json",
		},
	});

    return response.data;
}

export default api;
