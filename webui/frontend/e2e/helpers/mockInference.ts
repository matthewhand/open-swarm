/**
 * REQ-13: LLM-free mock inference for the SPA chat Send path.
 *
 * Replaces `window.WebSocket` before the app boots so `/chat` never talks to
 * Django, LiteLLM, Qwen, or Fly. Frames match DjangoChatConsumer / chatWs.ts:
 * user echo, assistant start, assistant final (HTMx OOB partials).
 *
 * FAST: delayMs = 0 (queueMicrotask).
 * SLOW: delayMs > 60_000; pair with Playwright `page.clock` so CI does not sleep.
 */
import type { Page } from '@playwright/test'

export const MOCK_FAST_REPLY = 'MOCK_INFERENCE_FAST_REPLY'
export const MOCK_SLOW_REPLY = 'MOCK_INFERENCE_SLOW_REPLY'

/** Wall-clock delay the slow mock waits before emitting the assistant reply. */
export const SLOW_INFERENCE_DELAY_MS = 61_000

export type MockInferenceOptions = {
  /** Delay before assistant frames. 0 = next microtask. */
  delayMs?: number
  /** Exact assistant body the UI must render (tests fail if this is missing). */
  reply?: string
}

export type MockInferenceState = {
  delayMs: number
  reply: string
  lastPrompt: string | null
  delivered: number
}

const EMPTY_LIST = { object: 'list', data: [] }

async function stubChatApis(page: Page): Promise<void> {
  await page.route('**/v1/blueprints**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(EMPTY_LIST),
    })
  })
  await page.route('**/v1/models**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(EMPTY_LIST),
    })
  })
  await page.route('**/v1/teams**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(EMPTY_LIST),
    })
  })
  await page.route('**/health**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ status: 'ok' }),
    })
  })
}

/**
 * Install the in-page mock websocket + hermetic /v1 stubs.
 * Must run before `page.goto`.
 */
export async function installMockInference(
  page: Page,
  options: MockInferenceOptions = {},
): Promise<void> {
  const delayMs = options.delayMs ?? 0
  const reply = options.reply ?? MOCK_FAST_REPLY
  await stubChatApis(page)
  await page.addInitScript(
    ({ delayMs: delay, reply: canned }: { delayMs: number; reply: string }) => {
      const escapeHtml = (value: string) =>
        value
          .replace(/&/g, '&amp;')
          .replace(/</g, '&lt;')
          .replace(/>/g, '&gt;')
          .replace(/"/g, '&quot;')

      const userEchoFrame = (text: string) =>
        `<div id="message-list" hx-swap-oob="beforeend"><div class="user-message">${escapeHtml(text)}</div></div>`

      const assistantStartFrame = (id: string) =>
        `<div id="message-list" hx-swap-oob="beforeend"><div id="${id}" class="assistant-message"></div></div>`

      const assistantFinalFrame = (id: string, text: string) =>
        `<div id="${id}" class="assistant-message" hx-swap-oob="true">${escapeHtml(text)}</div>`

      const state = {
        delayMs: delay,
        reply: canned,
        lastPrompt: null as string | null,
        delivered: 0,
      }
      ;(window as unknown as { __MOCK_INFERENCE__: typeof state }).__MOCK_INFERENCE__ =
        state

      class MockInferenceWebSocket {
        static CONNECTING = 0
        static OPEN = 1
        static CLOSING = 2
        static CLOSED = 3

        readonly url: string
        readyState = MockInferenceWebSocket.CONNECTING
        onopen: ((ev: Event) => void) | null = null
        onmessage: ((ev: MessageEvent) => void) | null = null
        onclose: ((ev: CloseEvent) => void) | null = null
        onerror: ((ev: Event) => void) | null = null
        private seq = 0

        constructor(url: string) {
          this.url = url
          queueMicrotask(() => {
            if (this.readyState !== MockInferenceWebSocket.CONNECTING) return
            this.readyState = MockInferenceWebSocket.OPEN
            this.onopen?.(new Event('open'))
          })
        }

        send(data: string) {
          let prompt = ''
          try {
            const parsed = JSON.parse(data) as { message?: unknown }
            prompt = typeof parsed.message === 'string' ? parsed.message : ''
          } catch {
            return
          }
          if (!prompt.trim()) return
          state.lastPrompt = prompt
          this.emit(userEchoFrame(prompt))

          const deliverAssistant = () => {
            this.seq += 1
            const id = `message-response-mock${this.seq}`
            this.emit(assistantStartFrame(id))
            this.emit(assistantFinalFrame(id, canned))
            state.delivered += 1
          }

          if (delay > 0) {
            setTimeout(deliverAssistant, delay)
          } else {
            queueMicrotask(deliverAssistant)
          }
        }

        close(code = 1000) {
          if (this.readyState === MockInferenceWebSocket.CLOSED) return
          this.readyState = MockInferenceWebSocket.CLOSED
          this.onclose?.(new CloseEvent('close', { code }))
        }

        private emit(data: string) {
          this.onmessage?.(new MessageEvent('message', { data }))
        }
      }

      window.WebSocket = MockInferenceWebSocket as unknown as typeof WebSocket
    },
    { delayMs, reply },
  )
}

export async function mockInferenceState(page: Page): Promise<MockInferenceState> {
  return page.evaluate(() => {
    const state = (window as unknown as { __MOCK_INFERENCE__?: MockInferenceState })
      .__MOCK_INFERENCE__
    if (!state) {
      throw new Error('mock inference was not installed')
    }
    return state
  })
}
