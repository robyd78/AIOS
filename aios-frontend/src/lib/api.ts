import { API_BASE } from "./config";

export type ToolCall = {
  name: string;
  arguments?: Record<string, unknown>;
};

export type ChatOptions = {
  latencyMs?: number;
  model?: string;
};

export type ChatResponse = {
  text?: string;
  model?: string;
  tool_call?: ToolCall;
  tool_result?: Record<string, unknown>;
  note?: string;
  clarify?: {
    kind: string;
    phrase: string;
    category?: string;
    options: Array<{ id?: string; name?: string; source?: string }>;
  };
};

export async function chatOnce(prompt: string, opts?: ChatOptions): Promise<ChatResponse> {
  const url = new URL(`${API_BASE}/chat`);
  if (opts?.latencyMs != null) {
    url.searchParams.set("latency_ms", String(opts.latencyMs));
  }

  const res = await fetch(url.toString(), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(opts?.model ? { "X-AIOS-Model": opts.model } : {}),
    },
    body: JSON.stringify({ messages: [{ role: "user", content: prompt }] }),
  });

  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Chat failed: ${res.status} ${detail}`);
  }

  return (await res.json()) as ChatResponse;
}

export async function ttsSpeak(text: string): Promise<string> {
  const res = await fetch(`${API_BASE}/tts`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });

  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`TTS failed: ${res.status} ${detail}`);
  }

  const wav = await res.arrayBuffer();
  const blob = new Blob([wav], { type: "audio/wav" });
  const url = URL.createObjectURL(blob);
  const audio = new Audio(url);
  await audio.play();
  return url;
}

export async function health(): Promise<{ status: string; ollama: boolean; piper: boolean }> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Health failed: ${res.status} ${detail}`);
  }
  return res.json();
}

export async function listTools(): Promise<any[]> {
  const res = await fetch(`${API_BASE}/tools`);
  if (!res.ok) throw new Error(`List tools failed: ${res.status}`);
  return res.json();
}

export async function execTool(
  name: string,
  args: Record<string, unknown>,
  options?: { overridePermissions?: string[] }
): Promise<{ result: any }> {
  const res = await fetch(`${API_BASE}/tools/execute`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name,
      arguments: args,
      override_permissions: options?.overridePermissions,
    }),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || `execTool failed ${res.status}`);
  }
  return res.json();
}

export async function setPermission(permission: string, allow: boolean) {
  const res = await fetch(`${API_BASE}/tools/permissions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ permission, allow }),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || "setPermission failed");
  }
  return res.json();
}

export async function rememberAliasChoice(payload: {
  choice: string;
  phrase: string;
  category?: string;
  make_default?: boolean;
  force?: boolean;
}) {
  const res = await fetch(`${API_BASE}/memory/alias`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || "rememberAlias failed");
  }
  return res.json();
}

export async function setDefaultKind(kind: string, target: string) {
  const res = await fetch(`${API_BASE}/memory/default`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ kind, target }),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || "setDefault failed");
  }
  return res.json();
}
