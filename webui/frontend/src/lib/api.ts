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

// ---------------------------------------------------------------------------
// Agent creator (swarm/views/agent_creator_views.py)
//
// /agent-creator/generate/ and /agent-creator/validate/ are plain Django POST
// views protected by CsrfViewMiddleware (verified: they 403 without a CSRF
// cookie + X-CSRFToken header). ensureCsrfCookie() primes the cookie via a
// cheap GET to /login/ (which sets csrftoken); buildHeaders() then attaches
// the matching X-CSRFToken header automatically.
//
// Saving deliberately uses POST /v1/blueprints/custom/ (a DRF view, CSRF-free
// for token/anonymous access) instead of /agent-creator/save/: the latter
// writes loose files under user_blueprints/ with no list/delete API, whereas
// the custom-blueprints library gives the page a coherent list/save/delete
// story against a single store.
// ---------------------------------------------------------------------------

/**
 * Make sure Django's csrftoken cookie is set before calling CSRF-protected
 * (non-DRF) endpoints. No-op when the cookie already exists.
 */
export async function ensureCsrfCookie(): Promise<void> {
  if (getCookie('csrftoken')) return
  try {
    await fetch('/login/', { headers: { Accept: 'text/html' } })
  } catch {
    // Network failure: the subsequent POST will surface a real error.
  }
}

/** Validation report returned by generate/validate (BlueprintCodeValidator). */
export interface CodeValidationResult {
  valid: boolean
  errors: string[]
  warnings: string[]
  syntax_valid: boolean
  structure_valid: boolean
  lint_clean: boolean
}

/** POST /agent-creator/generate/ request body (name/description/instructions required). */
export interface GenerateAgentRequest {
  name: string
  description: string
  instructions: string
  personality?: string
  expertise?: string[]
  communication_style?: string
  tags?: string[]
}

export interface GenerateAgentResponse {
  success: boolean
  code: string
  validation: CodeValidationResult
}

export interface ValidateAgentResponse {
  success: boolean
  validation: CodeValidationResult
}

export async function generateAgentCode(
  spec: GenerateAgentRequest,
): Promise<GenerateAgentResponse> {
  await ensureCsrfCookie()
  return apiPost<GenerateAgentResponse>('/agent-creator/generate/', spec)
}

export async function validateAgentCode(
  code: string,
): Promise<ValidateAgentResponse> {
  await ensureCsrfCookie()
  return apiPost<ValidateAgentResponse>('/agent-creator/validate/', { code })
}

// ---------------------------------------------------------------------------
// Custom blueprints CRUD (/v1/blueprints/custom/, swarm/views/api_views.py)
// ---------------------------------------------------------------------------

export interface CustomBlueprint {
  id: string
  name: string
  description: string
  category: string
  tags: string[]
  requirements: string
  code: string
  required_mcp_servers: string[]
  env_vars: string[]
}

export interface CreateCustomBlueprintRequest {
  name: string
  description?: string
  code?: string
  category?: string
  tags?: string[]
}

export function fetchCustomBlueprints(): Promise<ListResponse<CustomBlueprint>> {
  return apiGet<ListResponse<CustomBlueprint>>('/v1/blueprints/custom/')
}

export function createCustomBlueprint(
  blueprint: CreateCustomBlueprintRequest,
): Promise<CustomBlueprint> {
  return apiPost<CustomBlueprint>('/v1/blueprints/custom/', blueprint)
}

export function deleteCustomBlueprint(blueprintId: string): Promise<void> {
  return apiDelete(`/v1/blueprints/custom/${encodeURIComponent(blueprintId)}/`)
}

// ---------------------------------------------------------------------------
// Server settings (read-only; swarm/views/settings_views.py)
// ---------------------------------------------------------------------------

/** One entry inside a settings group (SettingsManager.collect_all_settings). */
export interface ServerSettingEntry {
  value: unknown
  env_var: string | null
  type: string
  description: string
  category: string
  sensitive: boolean
}

export interface ServerSettingsGroup {
  title: string
  description: string
  icon: string
  settings: Record<string, ServerSettingEntry>
}

/** GET /settings/api/ */
export interface ServerSettingsResponse {
  success: boolean
  settings: Record<string, ServerSettingsGroup>
}

/** GET /settings/environment/ */
export interface EnvironmentVariablesResponse {
  success: boolean
  environment_variables: Record<string, string>
  count: number
}

export function fetchServerSettings(): Promise<ServerSettingsResponse> {
  return apiGet<ServerSettingsResponse>('/settings/api/')
}

export function fetchEnvironmentVariables(): Promise<EnvironmentVariablesResponse> {
  return apiGet<EnvironmentVariablesResponse>('/settings/environment/')
}
