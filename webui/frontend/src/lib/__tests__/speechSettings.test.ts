import { describe, expect, it } from 'vitest'
import {
  describeSpeechPath,
  isCustomSpeechConfigured,
  parseSpeechSettings,
} from '../speechSettings'

describe('speechSettings (REQ-77)', () => {
  it('defaults missing payload to system and never invents a host', () => {
    const empty = parseSpeechSettings(null)
    expect(empty.stt.source).toBe('system')
    expect(empty.tts.source).toBe('system')
    expect(empty.stt.base_url).toBe('')
    expect(empty.tts.base_url).toBe('')
    expect(empty.stt.status).toBe('system')
    expect(isCustomSpeechConfigured(empty.stt)).toBe(false)
    expect(isCustomSpeechConfigured(parseSpeechSettings({ object: 'list', data: [] }).stt)).toBe(
      false,
    )
  })

  it('parses env names only and keeps system source when a custom URL is stored', () => {
    const parsed = parseSpeechSettings({
      stt: {
        source: 'system',
        base_url: 'http://127.0.0.1:9',
        model: 'whisper-1',
        api_key_env: 'STT_API_KEY',
        api_key: 'sk-should-not-be-required',
      },
      tts: {
        source: 'custom',
        base_url: '',
        model: 'tts-1',
        api_key_env: 'TTS_API_KEY',
      },
    })
    expect(parsed.stt.source).toBe('system')
    expect(parsed.stt.base_url).toBe('http://127.0.0.1:9')
    expect(parsed.stt.api_key_env).toBe('STT_API_KEY')
    expect(parsed.tts.source).toBe('custom')
    expect(parsed.tts.base_url).toBe('')
    expect(parsed.tts.status).toBe('off')
    expect(isCustomSpeechConfigured(parsed.stt)).toBe(true)
    expect(isCustomSpeechConfigured(parsed.tts)).toBe(false)
    expect(describeSpeechPath('system', 'stt')).toMatch(/system/)
    expect(describeSpeechPath('custom', 'tts')).toMatch(/custom/)
  })
})
