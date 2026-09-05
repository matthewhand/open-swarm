/**
 * Settings helpers for the opt-in OpenAI-compat image-gen endpoint (REQ-83).
 * Persist stores ${ENV} names, not keys. Empty URL is off — never guess a host.
 */

import { EMPTY_IMAGE_GEN, type ImageGenSettings } from './api'

export const IMAGE_GEN_QUERY_KEY = ['image-gen-settings'] as const

export function parseImageGenSettings(raw: unknown): ImageGenSettings {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) {
    return { ...EMPTY_IMAGE_GEN }
  }
  const row = raw as Record<string, unknown>
  const baseUrl = typeof row.base_url === 'string' ? row.base_url.trim() : ''
  const model = typeof row.model === 'string' ? row.model.trim() : ''
  const apiKeyEnv = typeof row.api_key_env === 'string' ? row.api_key_env.trim() : ''
  const avatars =
    row.avatars && typeof row.avatars === 'object' && !Array.isArray(row.avatars)
      ? Object.fromEntries(
          Object.entries(row.avatars as Record<string, unknown>).filter(
            (entry): entry is [string, string] =>
              typeof entry[0] === 'string' && typeof entry[1] === 'string' && Boolean(entry[1].trim()),
          ),
        )
      : {}
  const configured =
    typeof row.configured === 'boolean' ? row.configured : Boolean(baseUrl)
  return {
    object: 'image_gen',
    configured,
    base_url: baseUrl,
    model,
    api_key_env: apiKeyEnv,
    api_key_set: row.api_key_set === true,
    status: typeof row.status === 'string' ? row.status : configured ? 'unknown' : 'off',
    detail:
      typeof row.detail === 'string' && row.detail.trim()
        ? row.detail
        : configured
          ? 'Image generation is configured.'
          : EMPTY_IMAGE_GEN.detail,
    avatars,
    source: typeof row.source === 'string' ? row.source : undefined,
  }
}

export function isImageGenConfigured(settings?: ImageGenSettings | null): boolean {
  if (!settings) return false
  return Boolean(settings.configured && settings.base_url.trim())
}

export function defaultAvatarPrompt(name: string, role?: string | null): string {
  const label = name.trim() || 'agent'
  const roleBit = (role || '').trim()
  if (roleBit && roleBit !== 'default') {
    return `Still portrait avatar of ${label}, a ${roleBit} agent, simple icon, no animation`
  }
  return `Still portrait avatar of ${label}, simple icon, no animation`
}

export function isGeneratedStillSrc(src?: string | null): boolean {
  const trimmed = typeof src === 'string' ? src.trim() : ''
  if (!trimmed) return false
  return /\/avatars\/[^/?#]+_still\.(png|jpe?g|webp)$/i.test(trimmed)
}
