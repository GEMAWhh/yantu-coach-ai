import { isDemoApiEnabled } from "./demoClient";

const ACCESS_KEY_STORAGE_KEY = "yantu.personalAccessKey";
let volatileAccessKey: string | null = null;

export function isPersonalAuthRequired(): boolean {
  return (
    !isDemoApiEnabled() &&
    String(import.meta.env.VITE_YANTU_AUTH_REQUIRED).toLowerCase() === "true"
  );
}

export function getPersonalAccessKey(): string | null {
  try {
    return window.sessionStorage.getItem(ACCESS_KEY_STORAGE_KEY) ?? volatileAccessKey;
  } catch {
    return volatileAccessKey;
  }
}

export function setPersonalAccessKey(accessKey: string): void {
  try {
    window.sessionStorage.setItem(ACCESS_KEY_STORAGE_KEY, accessKey);
    volatileAccessKey = null;
  } catch {
    volatileAccessKey = accessKey;
  }
}

export function clearPersonalAccessKey(): void {
  volatileAccessKey = null;
  try {
    window.sessionStorage.removeItem(ACCESS_KEY_STORAGE_KEY);
  } catch {
    // Storage can be unavailable in hardened browser contexts.
  }
}
