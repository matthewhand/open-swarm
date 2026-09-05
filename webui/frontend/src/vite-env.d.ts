/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_SPA_VERSION: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
