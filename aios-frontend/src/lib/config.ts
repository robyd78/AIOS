export const API_BASE =
  (import.meta as any)?.env?.VITE_AIOS_API_BASE ??
  (typeof window !== "undefined" && (window as any).__AIOS_API_BASE__) ??
  "http://127.0.0.1:8000";
