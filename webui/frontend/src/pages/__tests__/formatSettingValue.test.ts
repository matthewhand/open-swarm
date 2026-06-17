import { describe, it, expect } from 'vitest'
import { formatSettingValue } from '../SettingsPage'

// formatSettingValue is the client-side masking applied on top of the server's
// own masking. It is security-relevant (it must never echo a raw secret), so
// pin its branches down.
describe('formatSettingValue', () => {
  it('renders empty-ish values as an em dash', () => {
    expect(formatSettingValue('FOO', null)).toBe('—')
    expect(formatSettingValue('FOO', undefined)).toBe('—')
    expect(formatSettingValue('FOO', '')).toBe('—')
  })

  it('passes server mask sentinels through untouched', () => {
    expect(formatSettingValue('API_KEY', '***HIDDEN***')).toBe('***HIDDEN***')
    expect(formatSettingValue('API_KEY', '***SET***')).toBe('***SET***')
    expect(formatSettingValue('API_KEY', 'Not Set')).toBe('Not Set')
  })

  it('masks secret-looking names to the last 4 characters', () => {
    expect(formatSettingValue('OPENAI_API_KEY', 'sk-abcd1234')).toBe('••••1234')
    expect(formatSettingValue('AUTH_TOKEN', 'tok_wxyz')).toBe('••••wxyz')
    expect(formatSettingValue('DB_PASSWORD', 'hunter2')).toBe('••••ter2')
    expect(formatSettingValue('CLIENT_SECRET', 'abcdef')).toBe('••••cdef')
  })

  it('matches the secret pattern case-insensitively', () => {
    expect(formatSettingValue('my_api_key', 'value123')).toBe('••••e123')
  })

  it('leaves non-secret values as their raw text', () => {
    expect(formatSettingValue('DEBUG', 'true')).toBe('true')
    expect(formatSettingValue('PORT', '8000')).toBe('8000')
  })

  it('stringifies non-string values before formatting', () => {
    expect(formatSettingValue('DEBUG', true)).toBe('true')
    expect(formatSettingValue('COUNT', 42)).toBe('42')
    expect(formatSettingValue('LIST', ['a', 'b'])).toBe('["a","b"]')
  })

  it('masks a secret-named value even when it is numeric', () => {
    // JSON.stringify(12345678) -> "12345678", last 4 -> "5678"
    expect(formatSettingValue('SECRET_KEY', 12345678)).toBe('••••5678')
  })
})
