/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_YANTU_API_BASE_URL?: string;
  readonly VITE_YANTU_AUTH_REQUIRED?: string;
  readonly VITE_YANTU_DEMO_API?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
