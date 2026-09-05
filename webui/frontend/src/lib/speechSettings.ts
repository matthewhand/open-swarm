/**
 * Settings helpers for mic STT + read-aloud TTS (REQ-77 / #422).
 * Persist stores ${ENV} names, not keys. Empty custom URL never guesses a host.
 * Default source is system even when a custom URL is stored.
 */

import {
  EMPTY_SPEECH,
  EMPTY_SPEECH_ENDPOINT,
  type SpeechEndpointSettings,
  type SpeechSettings,
  type SpeechSource,
} from './api'

export const SPEECH_QUERY_KEY = ['speech-settings'] as const

export function parseSpeechSource(raw: unknown): SpeechSource {
  return raw === 'custom' ? 'custom' : 'system'
}

export function parseSpeechEndpoint(raw: unknown, kind: 'stt' | 'tts'): SpeechEndpointSettings {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) {
    return { ...EMPTY_SPEECH_ENDPOINT, kind }
  }
  const row = raw as Record<string, unknown>
  const baseUrl = typeof row.base_url === 'string' ? row.base_url.trim() : ''
  const model = typeof row.model === 'string' ? row.model.trim() : ''
  const apiKeyEnv = typeof row.api_key_env === 'string' ? row.api_key_env.trim() : ''
  const source = parseSpeechSource(row.source)
  const configured = typeof row.configured === 'boolean' ? row.configured : Boolean(baseUrl)
  const status =
    typeof row.status === 'string' && row.status.trim()
      ? row.status
      : source === 'custom'
        ? configured
          ? 'unknown'
          : 'off'
        : 'system'
  const detail =
    typeof row.detail === 'string' && row.detail.trim()
      ? row.detail
      : source === 'custom'
        ? configured
          ? `Custom ${kind.toUpperCase()} is configured.`
          : `Custom ${kind.toUpperCase()} is off. No host is used until you set a base URL.`
        : EMPTY_SPEECH_ENDPOINT.detail
  return {
    kind,
    source,
    configured,
    base_url: baseUrl,
    model,
    api_key_env: apiKeyEnv,
    api_key_set: row.api_key_set === true,
    status,
    detail,
  }
}

export function parseSpeechSettings(raw: unknown): SpeechSettings {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) {
    return {
      object: 'speech',
      stt: { ...EMPTY_SPEECH.stt },
      tts: { ...EMPTY_SPEECH.tts },
    }
  }
  const row = raw as Record<string, unknown>
  return {
    object: 'speech',
    stt: parseSpeechEndpoint(row.stt, 'stt'),
    tts: parseSpeechEndpoint(row.tts, 'tts'),
  }
}

export function isCustomSpeechConfigured(endpoint?: SpeechEndpointSettings | null): boolean {
  if (!endpoint) return false
  return Boolean(endpoint.base_url.trim())
}

export function describeSpeechPath(path: 'system' | 'custom', kind: 'stt' | 'tts'): string {
  if (path === 'custom') {
    return kind === 'stt'
      ? 'custom OpenAI-compatible transcription'
      : 'custom OpenAI-compatible speech'
  }
  return kind === 'stt' ? 'system / browser transcription' : 'system / browser read-aloud'
}
