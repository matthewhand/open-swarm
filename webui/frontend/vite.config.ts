import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vitejs.dev/config/
export default defineConfig({
    plugins: [
        react(),
        tailwindcss(),
    ],
    server: {
        port: 3000,
        proxy: {
            // Proxy API routes used by the modern React webui (after porting/cleanup)
            // Enables direct fetch('/v1/...') and fetch('/teams/...') etc. in dev
            '/v1': {
                target: 'http://127.0.0.1:8000',
                changeOrigin: true,
            },
            '/teams': {
                target: 'http://127.0.0.1:8000',
                changeOrigin: true,
            },
            '/marketplace': {
                target: 'http://127.0.0.1:8000',
                changeOrigin: true,
            },
            '/api': {
                target: 'http://127.0.0.1:8000',
                changeOrigin: true,
            },
            '/v1': {
                target: 'http://127.0.0.1:8000',
                changeOrigin: true,
            },
            // Agent-creator generate/validate endpoints (Django views).
            // SPA no longer mounts /agent-creator (ADR-001); proxy remains for
            // any remaining client helpers during quarantine.
            '/agent-creator/generate': {
                target: 'http://127.0.0.1:8000',
                changeOrigin: true,
            },
            '/agent-creator/validate': {
                target: 'http://127.0.0.1:8000',
                changeOrigin: true,
            },
            // CSRF cookie priming for Django POSTs; /login/ sets csrftoken.
            '/login': {
                target: 'http://127.0.0.1:8000',
                changeOrigin: true,
            },
            // Read-only settings APIs (Django). SPA /settings is unmounted
            // (ADR-001); proxies remain for quarantined page helpers / Chat CTAs.
            '/settings/api': {
                target: 'http://127.0.0.1:8000',
                changeOrigin: true,
            },
            '/settings/environment': {
                target: 'http://127.0.0.1:8000',
                changeOrigin: true,
            },
            '/ws': {
                target: 'ws://127.0.0.1:8000',
                ws: true,
            }
        }
    },
    build: {
        outDir: 'dist',
    },
    test: {
        environment: 'jsdom',
        setupFiles: ['./src/setupTests.ts'],
        globals: true,
        // Unit/component tests live under src/; e2e/*.spec.ts is Playwright and
        // must not be collected by vitest (different runner).
        // pages/_quarantine is archival (ADR-001) — not mounted, not tested.
        include: ['src/**/*.{test,spec}.{ts,tsx}'],
        exclude: ['**/node_modules/**', '**/dist/**', '**/_quarantine/**'],
    }
})
