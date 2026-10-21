# Optional physical-device rendering checks

The suite uses an already-authorized device browser through an existing Chrome
DevTools connection. It does not install apps, enable debugging, pair new devices,
or send a chat message. Autocomplete is stubbed on the selected test tab so typing
does not invoke its real model backend. Use a dedicated test tab pointed at an isolated
WebUI with synthetic conversation data. It preserves the original message draft
and disconnects its CDP connection without closing the user's Chrome browser.

From `webui/frontend`, set these environment variables privately:

| Variable | Meaning |
| --- | --- |
| `SWARM_DEVICE_CDP_URL` | Existing reachable CDP endpoint, preferably a loopback SSH/ADB forward |
| `SWARM_DEVICE_TEST_URL` | Exact URL of the dedicated test tab already open on the device |
| `SWARM_DEVICE_EXPECT_SOFT_KEYBOARD` | Set to `1` to require observed viewport shrink on a phone |

Run only this suite with:

```sh
npx playwright test e2e/physical-device-ui.spec.ts --workers=1
```

Without the URL variables the test skips. It checks initial compact state,
expanded usage, typing with a real keyboard, horizontal overflow, and input/Send
visibility within the visual viewport. Screenshots and layout measurements are
saved in Playwright's test artifacts. No device serials or credentials belong in
commits. Restore only forwards created for the test; never remove unrelated ADB
forwards or stop a shared ADB server.

## Demonstrated results, 2026-10-21

**Android phone: passed.** Samsung SM-G970F, Android 12, Chrome 155, physical
display 1080 × 2280, configured density 540, effective width 320 CSS pixels.
Compact, expanded, and soft-keyboard states had zero horizontal page/conversation
overflow. The keyboard reduced the visible height from about 537 to 270 CSS
pixels; the input and Send button remained inside that visible area. The original
draft was restored. The user's requested screen timeout increased from five
minutes to two hours and was read back successfully.

**Chromebook native ChromeOS browser: not verified.** The existing authorized ADB
connection identified a kukui Android runtime with a 1920 × 1200 display. It
forwarded web intents to `org.chromium.arc.intent_helper`; there was no Android
Chrome app or Chrome debugging socket. Android screen capture returned a blank
surface rather than the native ChromeOS browser. The inspected gateway ADB
adapter exposes Android operations, with no native ChromeOS screen/browser tool
found. The native Chrome debugging endpoint was not reachable. The device later
became unreachable again, preventing further ADB inspection.

The Chromebook Android screen timeout was already about 25 days; that longer
value was preserved. It does not establish the native ChromeOS host's sleep
policy. No native ChromeOS debugging or new remote access was enabled. A native
ChromeOS capture/control connection, or a supervised manual check, is still
needed before claiming Chromebook compatibility. These checks exercised the
existing ADB service via SSH; they do not certify the gateway's MCP transport.
