/**
 * Lightweight auth context for the static bearer-token auth used by the
 * backend (API_AUTH_TOKEN — not OAuth).
 *
 * - Exposes the current token plus setToken (persisted to
 *   localStorage["swarm_api_token"], which lib/api.ts reads on every request).
 * - Tracks the most recent 401/403 reported by the API layer (via the
 *   AUTH_ERROR_EVENT window event) so the app can show a banner. No login
 *   wall: with auth disabled on the backend, no token is needed and no error
 *   is ever raised.
 */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import {
  API_TOKEN_STORAGE_KEY,
  AUTH_ERROR_EVENT,
  type AuthErrorDetail,
} from './api'

interface AuthContextValue {
  /** Current bearer token, or null when none is stored. */
  token: string | null
  /** Persist a new token (null clears it). Also resets any auth error. */
  setToken: (token: string | null) => void
  /** Most recent 401/403 from the API, until dismissed or token changes. */
  authError: AuthErrorDetail | null
  clearAuthError: () => void
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

function readStoredToken(): string | null {
  try {
    return window.localStorage.getItem(API_TOKEN_STORAGE_KEY)
  } catch {
    return null
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setTokenState] = useState<string | null>(readStoredToken)
  const [authError, setAuthError] = useState<AuthErrorDetail | null>(null)

  const setToken = useCallback((next: string | null) => {
    try {
      if (next) {
        window.localStorage.setItem(API_TOKEN_STORAGE_KEY, next)
      } else {
        window.localStorage.removeItem(API_TOKEN_STORAGE_KEY)
      }
    } catch {
      // localStorage unavailable; api.ts will simply see no token.
    }
    setTokenState(next)
    setAuthError(null)
  }, [])

  const clearAuthError = useCallback(() => setAuthError(null), [])

  useEffect(() => {
    const handler = (event: Event) => {
      const detail = (event as CustomEvent<AuthErrorDetail>).detail
      setAuthError(
        detail ?? { status: 401, message: 'Authentication failed' },
      )
    }
    window.addEventListener(AUTH_ERROR_EVENT, handler)
    return () => window.removeEventListener(AUTH_ERROR_EVENT, handler)
  }, [])

  const value = useMemo(
    () => ({ token, setToken, authError, clearAuthError }),
    [token, setToken, authError, clearAuthError],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
