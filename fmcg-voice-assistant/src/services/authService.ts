import {
    apiRequest,
    clearTokens,
    getRefreshToken,
    saveTokens,
} from './api'

export interface AuthUser {
    id: number
    username: string
    email: string
    first_name: string
    last_name: string
    full_name: string
    is_staff: boolean
    is_superuser: boolean
}

interface LoginResponse {
    success: boolean
    message: string
    data: {
        user: AuthUser
        tokens: {
            access: string
            refresh: string
        }
    }
}

interface CurrentUserResponse {
    success: boolean
    message: string
    data: AuthUser
}

const USER_KEY = 'fmcg_user'

export function getStoredUser(): AuthUser | null {
    const storedUser = localStorage.getItem(USER_KEY)

    if (!storedUser) return null

    try {
        return JSON.parse(storedUser) as AuthUser
    } catch {
        localStorage.removeItem(USER_KEY)
        return null
    }
}

export async function login(
    credentials: { username?: string; email?: string; password: string },
): Promise<AuthUser> {

    console.log("credentials" + JSON.stringify(credentials));

    const response = await apiRequest<LoginResponse>('/auth/login/', {
        method: 'POST',
        requiresAuth: false,
        body: JSON.stringify(credentials),
    })

    if (!response.success || !response.data?.tokens?.access) {
        throw new Error('Invalid login response from server.')
    }

    saveTokens(
        response.data.tokens.access,
        response.data.tokens.refresh,
    )

    localStorage.setItem(USER_KEY, JSON.stringify(response.data.user))

    return response.data.user
}

export async function getCurrentUser(): Promise<AuthUser> {
    const response = await apiRequest<CurrentUserResponse>('/auth/me/')

    localStorage.setItem(USER_KEY, JSON.stringify(response.data))

    return response.data
}

export async function logout(): Promise<void> {
    const refresh = getRefreshToken()

    try {
        if (refresh) {
            await apiRequest('/auth/logout/', {
                method: 'POST',
                body: JSON.stringify({ refresh }),
            })
        }
    } finally {
        clearTokens()
        localStorage.removeItem(USER_KEY)
    }
}
