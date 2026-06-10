/**
 * Minimal typed fetch wrapper for the Open Swarm backend API.
 *
 * In dev, requests to /v1/* are proxied to the Django backend by Vite
 * (see vite.config.ts). An optional bearer token is read from localStorage
 * under the key "swarm_api_token".
 */

export const API_TOKEN_STORAGE_KEY = 'swarm_api_token'

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

/**
 * Thrown when the backend rejects a request with 401/403. A matching
 * AUTH_ERROR_EVENT is dispatched on `window` so the AuthContext can surface
 * a visible indicator (banner) regardless of which query failed.
 */
export class ApiAuthError extends ApiError {
  constructor(status: number, message: string) {
    super(status, message)
    this.name = 'ApiAuthError'
  }
}

export function isAuthError(error: unknown): error is ApiAuthError {
  return error instanceof ApiAuthError
}

export interface AuthErrorDetail {
  status: number
  message: string
}

export const AUTH_ERROR_EVENT = 'swarm:auth-error'

function getAuthToken(): string | null {
  try {
    return window.localStorage.getItem(API_TOKEN_STORAGE_KEY)
  } catch {
    return null
  }
}

function getCookie(name: string): string | null {
  try {
    const match = document.cookie
      .split('; ')
      .find((row) => row.startsWith(`${name}=`))
    return match ? decodeURIComponent(match.split('=').slice(1).join('=')) : null
  } catch {
    return null
  }
}

function buildHeaders(hasBody: boolean): Record<string, string> {
  const headers: Record<string, string> = { Accept: 'application/json' }
  const token = getAuthToken()
  if (token) {
    headers.Authorization = `Bearer ${token}`
  }
  if (hasBody) {
    headers['Content-Type'] = 'application/json'
  }
  // Django session auth enforces CSRF on unsafe methods; include the token
  // when the cookie is present (harmless for token/anonymous access).
  const csrfToken = getCookie('csrftoken')
  if (csrfToken) {
    headers['X-CSRFToken'] = csrfToken
  }
  return headers
}

async function throwApiError(path: string, response: Response): Promise<never> {
  let detail = ''
  try {
    const body = await response.json()
    detail = body?.error ?? body?.detail ?? ''
  } catch {
    // Non-JSON error body; fall through to generic message.
  }
  const message =
    detail || `Request to ${path} failed with status ${response.status}`

  if (response.status === 401 || response.status === 403) {
    const eventDetail: AuthErrorDetail = { status: response.status, message }
    try {
      window.dispatchEvent(
        new CustomEvent<AuthErrorDetail>(AUTH_ERROR_EVENT, {
          detail: eventDetail,
        }),
      )
    } catch {
      // Non-browser environment (tests); the typed error below still surfaces.
    }
    throw new ApiAuthError(response.status, message)
  }

  throw new ApiError(response.status, message)
}

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(path, { headers: buildHeaders(false) })

  if (!response.ok) {
    await throwApiError(path, response)
  }

  return (await response.json()) as T
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(path, {
    method: 'POST',
    headers: buildHeaders(true),
    body: JSON.stringify(body),
  })

  if (!response.ok) {
    await throwApiError(path, response)
  }

  return (await response.json()) as T
}

export async function apiDelete(path: string): Promise<void> {
  const response = await fetch(path, {
    method: 'DELETE',
    headers: buildHeaders(false),
  })

  if (!response.ok) {
    await throwApiError(path, response)
  }
}

// ---------------------------------------------------------------------------
// Endpoint types (shapes verified against src/swarm/views/api_views.py)
// ---------------------------------------------------------------------------

export interface ListResponse<T> {
  object: 'list'
  data: T[]
}

/** GET /v1/blueprints/ (BlueprintsListView) */
export interface Blueprint {
  id: string
  object: 'blueprint'
  name: string
  description: string
  abbreviation: string | null
  required_mcp_servers: string[]
  tags: string[]
  installed: boolean | null
  compiled: boolean | null
}

/** GET /v1/models/ (OpenAI-style model list) */
export interface Model {
  id: string
  object: 'model'
  created: number
  owned_by: string
}

/** GET/POST /v1/teams/ and DELETE /v1/teams/<id>/ (swarm/views/teams_api.py) */
export interface Team {
  id: string
  object: 'team'
  description: string
  llm_profile: string
}

export interface CreateTeamRequest {
  name: string
  description?: string
  llm_profile?: string
}

export function fetchBlueprints(): Promise<ListResponse<Blueprint>> {
  return apiGet<ListResponse<Blueprint>>('/v1/blueprints/')
}

export function fetchModels(): Promise<ListResponse<Model>> {
  return apiGet<ListResponse<Model>>('/v1/models/')
}

export function fetchTeams(): Promise<ListResponse<Team>> {
  return apiGet<ListResponse<Team>>('/v1/teams/')
}

export function createTeam(team: CreateTeamRequest): Promise<Team> {
  return apiPost<Team>('/v1/teams/', team)
}

export function deleteTeam(teamId: string): Promise<void> {
  return apiDelete(`/v1/teams/${encodeURIComponent(teamId)}/`)
}
