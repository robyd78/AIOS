export function isTauri(): boolean {
  return (
    typeof window !== "undefined" &&
    ("__TAURI_INTERNALS__" in window || (window as any).__TAURI__ != null)
  );
}

export async function safeInvoke<T = any>(
  cmd: string,
  args?: Record<string, any>
): Promise<T> {
  if (!isTauri()) {
    throw new Error("Tauri invoke not available in browser dev mode.");
  }
  const { invoke } = await import("@tauri-apps/api/core");
  return invoke<T>(cmd, args);
}
