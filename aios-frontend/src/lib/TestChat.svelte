<script lang="ts">
  import { onMount } from "svelte";
  import type { ToolCall } from "./api";
  import { chatOnce, ttsSpeak, health, execTool } from "./api";

  let input = "Say hi in one sentence.";
  let reply = "";
  let status = "idle";
  let latencyMs = 900;
  let model = "";
  let healthMsg = "…";
  let busy = false;

  onMount(async () => {
    try {
      const h = await health();
      healthMsg = `status=${h.status} | ollama=${h.ollama} | piper=${h.piper}`;
    } catch (error) {
      healthMsg = `health error: ${String(error)}`;
    }
  });

  async function runTest() {
    busy = true;
    status = "thinking";
    reply = "";
    try {
      const res = await chatOnce(input, { latencyMs, model: model || undefined });
      if (res.tool_call) {
        const result = await execTool(res.tool_call.name, (res.tool_call.arguments as Record<string, unknown>) ?? {});
        reply = JSON.stringify(result.result, null, 2);
        status = `tool ${res.tool_call.name}`;
      } else {
        reply = res.text ?? "";
        status = `speaking via ${res.model ?? "auto"}`;
        await ttsSpeak(reply);
        status = "done";
      }
    } catch (error: any) {
      console.error(error);
      status = `error: ${error?.message ?? String(error)}`;
    } finally {
      busy = false;
    }
  }
</script>

<style>
  .card {
    max-width: 760px;
    margin: 3rem auto;
    padding: 1rem 1.25rem;
    border-radius: 16px;
    background: rgba(255, 255, 255, 0.65);
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.12);
    backdrop-filter: blur(6px);
  }
  .row {
    display: flex;
    gap: 12px;
    align-items: flex-end;
    flex-wrap: wrap;
  }
  .grow {
    flex: 1;
    min-width: 180px;
  }
  textarea,
  input,
  select {
    width: 100%;
    padding: 10px 12px;
    border-radius: 10px;
    border: 1px solid rgba(0, 0, 0, 0.08);
    background: #fff;
  }
  button {
    padding: 10px 16px;
    border-radius: 12px;
    border: none;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
    cursor: pointer;
    min-width: 160px;
  }
  button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
  .label {
    font-size: 0.9rem;
    opacity: 0.8;
    margin-bottom: 6px;
    display: block;
  }
  .reply {
    white-space: pre-wrap;
    padding: 12px;
    border-radius: 10px;
    background: #fff;
    margin-top: 8px;
  }
  .status {
    margin-top: 8px;
    opacity: 0.9;
  }
  .health {
    opacity: 0.8;
    margin-bottom: 10px;
  }
</style>

<div class="card">
  <h2>AIOS Test · Chat → TTS</h2>
  <div class="health">Backend: {healthMsg}</div>

  <div class="label">Prompt</div>
<textarea rows="3" bind:value={input}></textarea>


  <div class="row" style="margin-top:12px;">
    <div>
      <div class="label">Latency (ms)</div>
      <input type="number" min="0" bind:value={latencyMs} style="width:140px;" />
    </div>
    <div class="grow">
      <div class="label">Force Model (optional)</div>
      <select bind:value={model}>
        <option value="">auto (router)</option>
        <option value="qwen2.5:3b-instruct">qwen2.5:3b-instruct</option>
        <option value="phi3:mini">phi3:mini</option>
        <option value="llama3:8b">llama3:8b</option>
      </select>
    </div>
    <div>
      <button on:click={runTest} disabled={busy}>{busy ? "Running…" : "Run Chat → TTS"}</button>
    </div>
  </div>

  <div style="margin-top:16px;">
    <div class="label" style="font-weight:600;">Reply</div>
    <div class="reply">{reply}</div>
  </div>

  <div class="status">Status: {status}</div>
</div>
