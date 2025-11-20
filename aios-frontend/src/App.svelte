<script lang="ts">
  import * as THREE from "three";
  import { getCurrentWindow } from "@tauri-apps/api/window";
  import { onDestroy, onMount, tick } from "svelte";
  import type { ToolCall } from "./lib/api";
  import {
    chatOnce,
    ttsSpeak,
    health,
    listTools,
    execTool,
    setPermission,
    rememberAliasChoice,
    setDefaultKind,
  } from "./lib/api";
  import { pickWallpaper, type WallpaperSelection } from "./lib/wallpaper";
  import { isTauri, safeInvoke } from "./lib/tauriSafe";
  import { startLoop, stopLoop } from "./three-runtime";
  import TestChat from "./lib/TestChat.svelte";

  type PulseWindow = Window & { __pulse?: number };

  const appWindow = isTauri() ? getCurrentWindow() : null;
  const DEBUG = true;

  console.log("🔎 App.svelte evaluated");
  if (typeof window !== "undefined") {
    (window as any).__APP_PROBE__ = "loaded";
  }
  let state: "idle" | "listening" | "thinking" | "speaking" = "idle";
  let showInput = false;
  let allowBlur = false;
  let query = "";
  let inputEl: HTMLInputElement | null = null;
  let response = "";
  let unlistenBlur: (() => void) | null = null;
  let renderer: THREE.WebGLRenderer | null = null;
  let scene: THREE.Scene | null = null;
  let camera: THREE.PerspectiveCamera | null = null;
  let globeMesh: THREE.Mesh | null = null;
  let canvasEl: HTMLCanvasElement | null = null;
  let resizeObserver: ResizeObserver | null = null;
  let globeUniforms: {
    uTime: { value: number };
    uAspect: { value: number };
    uRadius: { value: number };
    uBase: { value: THREE.Color };
    uCore: { value: THREE.Color };
    uRippleAmp: { value: number };
    uTrigger: { value: number };
  } | null = null;
  let viewMode: "prod" | "test" = "prod";
  let wallpaperUrl: string | null = null;
  let wallpaperObjectUrl: string | null = null;
  let backendStatus = "…";
  $: wallpaperStyle = `background-image:url(${wallpaperUrl ?? "/wallpapers/default_1.jpg"});`;
  let tools: Array<{ name: string; description: string }> = [];
  let pendingToolCall: ToolCall | null = null;
  let permissionPrompt: { perms: string[]; call: ToolCall } | null = null;
  let contextMenu = { visible: false, x: 0, y: 0 };
  let wallpaperDebug = { message: "", preview: "" };
  let showTestChat = true;
  let showWallpaperDebug = true;
  let lastHints: string[] = [];
  let lastPlan: Array<{ channel?: string; cmd?: string; reason?: string; available?: boolean }> = [];
  let clarifyPrompt: {
    kind: string;
    phrase: string;
    category?: string;
    options: Array<{ id?: string; name?: string; source?: string }>;
  } | null = null;
  let clarifyMakeDefault = false;
  if (typeof window !== "undefined") {
    const url = new URL(window.location.href);
    if (url.searchParams.get("test") === "1") {
      viewMode = "test";
    }
  }

  const toggleListen = () => (state = state === "idle" ? "listening" : "idle");

  function closeContextMenu() {
    contextMenu = { visible: false, x: 0, y: 0 };
  }

  function openContextMenu(event: MouseEvent) {
    event.preventDefault();
    contextMenu = { visible: true, x: event.clientX, y: event.clientY };
  }

  function setWallpaper(selection: WallpaperSelection) {
    if (wallpaperObjectUrl) {
      URL.revokeObjectURL(wallpaperObjectUrl);
      wallpaperObjectUrl = null;
    }
    wallpaperUrl = selection.url;
    if (selection.needsRevoke) {
      wallpaperObjectUrl = selection.url;
    }
  }

  function setFallbackWallpaper() {
    const fallback = `/wallpapers/default_${Math.floor(Math.random() * 5) + 1}.jpg`;
    if (wallpaperObjectUrl) {
      URL.revokeObjectURL(wallpaperObjectUrl);
      wallpaperObjectUrl = null;
    }
    wallpaperUrl = fallback;
    wallpaperDebug = { message: "Fallback wallpaper", preview: fallback };
  }

  async function loadRandomWallpaper() {
    if (isTauri()) {
      const selection = await pickWallpaper();
      if (selection) {
        setWallpaper(selection);
        wallpaperDebug = { message: "Picked via dialog", preview: selection.url };
        return;
      }
    } else {
      console.warn("Wallpaper picker unavailable outside of Tauri; using fallback image");
    }
    setFallbackWallpaper();
  }

  async function testWallpaperPicker() {
    wallpaperDebug = { message: "Opening picker…", preview: "" };
    try {
      const selection = await pickWallpaper();
      if (selection) {
        setWallpaper(selection);
        wallpaperDebug = { message: `Picked: ${selection.url}`, preview: selection.url };
      } else {
        wallpaperDebug = { message: "Picker cancelled or unavailable", preview: "" };
      }
    } catch (error) {
      console.error("wallpaper picker test failed", error);
      wallpaperDebug = {
        message: `Error: ${error instanceof Error ? error.message : String(error)}`,
        preview: "",
      };
    }
  }

  async function openTerminal() {
    allowBlur = true;
    if (isTauri()) {
      try {
        await safeInvoke("launch_app", { cmd: "kitty", args: [] });
      } catch (error) {
        console.warn("launch_app invoke failed", error);
      }
    }
    setTimeout(() => (allowBlur = false), 800);
  }

  const goWorkspace3 = () =>
    isTauri()
      ? safeInvoke("hypr_dispatch", { args: ["workspace", "3"] }).catch((error) =>
          console.warn("hypr_dispatch failed", error)
        )
      : Promise.resolve();

  function formatToolResult(call: ToolCall, result: Record<string, unknown>): string {
    if (call.name === "get_datetime") {
      if (typeof result.human === "string") {
        return `It is ${result.human}.`;
      }
      if (typeof result.iso === "string") {
        return `It is ${result.iso}.`;
      }
    }
    if (call.name === "open_app") {
      const args = (call.arguments as Record<string, unknown> | undefined) ?? {};
      const app =
        (args.app as string) ||
        (args.app_name as string) ||
        (args.name as string) ||
        "the app";
      if (!result.ok) {
        const hintText =
          Array.isArray(result.hints) && result.hints.length
            ? `\nHints:\n${(result.hints as string[]).join("\n")}`
            : "";
        return `Launch failed for ${app}: ${result.error ?? "unknown error"}${hintText}`;
      }
      const note =
        typeof result.note === "string" && result.note.trim()
          ? result.note
          : `Launching ${app} now.`;
      const command = typeof result.command === "string" ? `\nCommand: ${result.command}` : "";
      return `${note}${command}`;
    }
    if (call.name === "open_terminal") {
      const args = (call.arguments as Record<string, unknown> | undefined) ?? {};
      const program = (args.program as string) ?? "the program";
      const terminal = (args.terminal as string) ?? "terminal";
      const workspace = args.workspace ? ` on workspace ${args.workspace}` : "";
      const base =
        typeof result.note === "string" && result.note.trim()
          ? result.note
          : `Opening ${program} in ${terminal}${workspace}.`;
      const command = typeof result.command === "string" ? `\nCommand: ${result.command}` : "";
      return `${base}${command}`;
    }
    if (call.name === "close_empty_aios_workspaces") {
      if (typeof result.note === "string") return result.note;
      const closed = Array.isArray(result.closed) ? result.closed.join(", ") : "";
      const kept = Array.isArray(result.kept) ? result.kept.join(", ") : "";
      return `Closed: ${closed || "none"} | Kept: ${kept || "none"}`;
    }
    if (call.name === "session_switch_plan") {
      const steps = Array.isArray(result.steps)
        ? result.steps
            .map((step: any, idx: number) => {
              if (step.type === "write_file") {
                return `${idx + 1}. Write ${step.path}`;
              }
              if (step.type === "command") {
                return `${idx + 1}. Run ${step.cmd}`;
              }
              return `${idx + 1}. ${JSON.stringify(step)}`;
            })
            .join("\n")
        : JSON.stringify(result, null, 2);
      const note = typeof result.post_note === "string" ? `\n${result.post_note}` : "";
      return `Session plan for ${result.target ?? ""}:\n${steps}${note}`;
    }
    return JSON.stringify(result, null, 2);
  }

  function describeToolCall(call: ToolCall): string {
    const args = (call.arguments as Record<string, unknown> | undefined) ?? {};
    switch (call.name) {
      case "open_app": {
        const app =
          (args.app as string) ||
          (args.app_name as string) ||
          (args.name as string) ||
          "the app";
        const channel = args.channel ? ` (${String(args.channel)})` : "";
        return `Open ${app}${channel}`;
      }
      case "close_empty_aios_workspaces":
        return "Close empty AIOS workspaces";
      case "session_switch_plan": {
        const target =
          ((call.arguments as Record<string, unknown>) ?? {}).target ?? "target session";
        return `Plan switch to ${target}`;
      }
      case "open_terminal": {
        const program = (args.program as string) ?? "the program";
        const terminal = (args.terminal as string) ?? "terminal";
        const workspace = args.workspace ? ` on workspace ${args.workspace}` : "";
        return `Run ${program} in ${terminal}${workspace}`;
      }
      case "mkdir": {
        const path = (args.path as string) ?? "the folder";
        return `Create folder ${path}`;
      }
      case "touch": {
        const path = (args.path as string) ?? "the file";
        return `Create file ${path}`;
      }
      case "run_command_safe": {
        const cmd = Array.isArray(args.cmd) ? args.cmd.join(" ") : "command";
        return `Run command: ${cmd}`;
      }
      case "pkg_plan_install": {
        const pkg = (args.name as string) ?? "package";
        const channel = args.channel ? ` via ${args.channel}` : "";
        return `Plan install ${pkg}${channel}`;
      }
      case "pkg_install": {
        const pkg = (args.name as string) ?? "package";
        const channel = args.channel ? ` (${args.channel})` : "";
        return `Install ${pkg}${channel}`;
      }
      case "pkg_remove": {
        const pkg = (args.name as string) ?? "package";
        return `Remove ${pkg}`;
      }
      case "pkg_update": {
        const pkg = (args.name as string) ?? "package";
        return `Update ${pkg}`;
      }
      default:
        return `Run tool ${call.name}`;
    }
  }

  async function handleClarifySelection(option: { id?: string; name?: string; source?: string }) {
    const phrase = clarifyPrompt?.phrase ?? "";
    const category = clarifyPrompt?.category ?? "";
    const makeDefault = clarifyMakeDefault && Boolean(category);
    const choiceId = option.id;
    clarifyPrompt = null;
    clarifyMakeDefault = false;
    const followup = (phrase || "").trim() || (choiceId ? `open ${choiceId}` : option.name || "");
    if (!followup.trim()) return;
    state = "thinking";
    try {
      if (choiceId) {
        await rememberAliasChoice({
          choice: choiceId,
          phrase: phrase || followup,
          category: category || undefined,
          make_default: makeDefault,
          force: true,
        });
        if (makeDefault && category) {
          await setDefaultKind(category, choiceId);
        }
      }
      const res = await chatOnce(followup, { latencyMs: 900 });
      await processChatResponse(res);
    } catch (error) {
      console.error(error);
      response =
        error instanceof Error
          ? `Error: ${error.message}`
          : `Error: ${String(error)}`;
      state = "idle";
    }
  }

  async function runToolCall(call: ToolCall, overrides?: string[]) {
    try {
      const execRes = await execTool(
        call.name,
        ((call.arguments as Record<string, unknown>) ?? {}),
        overrides ? { overridePermissions: overrides } : undefined
      );
      const resultPayload = execRes.result ?? {};
      const message = formatToolResult(call, resultPayload);
      response = message;
      const hints = Array.isArray(resultPayload?.hints) ? (resultPayload?.hints as string[]) : [];
      lastHints = hints;
      lastPlan = Array.isArray(resultPayload?.plan) ? ((resultPayload?.plan as unknown) as any[]) : [];
      permissionPrompt = null;
      pendingToolCall = null;
      state = "speaking";
      await ttsSpeak(message);
    } catch (error: any) {
      let detail: any = null;
      try {
        detail = JSON.parse(error?.message ?? "{}");
      } catch (err) {
        detail = null;
      }
      const missing = detail?.detail?.missing || detail?.missing;
      if (missing) {
        permissionPrompt = { perms: missing, call };
      } else {
        response = `Tool error: ${error?.message ?? String(error)}`;
      }
      lastHints = [];
    }
  }

  async function allowOnce() {
    if (!permissionPrompt) return;
    const perms = permissionPrompt.perms;
    const call = permissionPrompt.call;
    permissionPrompt = null;
    const overrides = new Set(perms);
    if (call.arguments) {
      call.arguments.__override = Array.from(overrides);
    } else {
      call.arguments = { __override: Array.from(overrides) };
    }
    await runToolCall(call, perms);
  }

  async function allowAlways() {
    if (!permissionPrompt) return;
    const perms = permissionPrompt.perms;
    const call = permissionPrompt.call;
    for (const perm of perms) {
      try {
        await setPermission(perm, true);
      } catch (error) {
        console.error("Failed to persist permission", error);
      }
    }
    permissionPrompt = null;
    await runToolCall(call);
  }

  function denyPermission() {
    permissionPrompt = null;
    pendingToolCall = null;
    response = "Permission denied.";
  }

  function onKeydownGlobal(e: KeyboardEvent) {
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    if (e.key.length === 1 || e.key === "Backspace") {
      showInput = true;
      requestAnimationFrame(() => inputEl?.focus());
    } else if (e.key === "Escape") {
      if (query.length) query = "";
      else showInput = false;
    }
  }

  async function submitQuery() {
    if (!query.trim()) return;
    state = "thinking";
    try {
      const res = await chatOnce(query, { latencyMs: 900 });
      await processChatResponse(res);
    } catch (error) {
      console.error(error);
      response =
        error instanceof Error
          ? `Error: ${error.message}`
          : `Error: ${String(error)}`;
      lastHints = [];
      state = "idle";
    }
  }

  async function processChatResponse(res: any) {
    if (res.clarify) {
      clarifyPrompt = res.clarify;
      clarifyMakeDefault = false;
      response = res.text ?? "Which app should I use?";
      state = "idle";
      return;
    }
    clarifyPrompt = null;
    clarifyMakeDefault = false;
    permissionPrompt = null;
    pendingToolCall = null;
    if (res.tool_call) {
      pendingToolCall = res.tool_call;
      await runToolCall(res.tool_call);
      return;
    }
    if (res.text) {
      response = res.text ?? "";
      if (res.tool_result && Array.isArray((res.tool_result as any).hints)) {
        lastHints = ((res.tool_result as any).hints as string[]) ?? [];
      } else {
        lastHints = [];
      }
      if (res.tool_result && Array.isArray((res.tool_result as any).plan)) {
        lastPlan = ((res.tool_result as any).plan as any[]) ?? [];
      } else {
        lastPlan = [];
      }
      state = "speaking";
      await ttsSpeak(response);
      state = "idle";
      return;
    }
    state = "idle";
  }

  function resizeRenderer() {
    if (!renderer || !camera || !canvasEl) return;
    const { width, height } = canvasEl.getBoundingClientRect();
    if (!width || !height) return;
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    if (globeUniforms && height !== 0) {
      globeUniforms.uAspect.value = width / height;
    }
  }

  function setupThree() {
    if (!canvasEl) {
      console.error("❌ canvas element not ready");
      return false;
    }

    renderer = new THREE.WebGLRenderer({
      canvas: canvasEl,
      antialias: true,
      alpha: true,
    });
    if (typeof window !== "undefined") {
      (window as any).renderer = renderer;
    }
    renderer.setSize(canvasEl.clientWidth, canvasEl.clientHeight, false);
    if ("ColorManagement" in THREE && (THREE as any).ColorManagement) {
      (THREE as any).ColorManagement.enabled = true;
    }
    if ("outputColorSpace" in renderer) {
      // @ts-ignore - property exists on newer Three versions
      renderer.outputColorSpace = THREE.SRGBColorSpace;
    } else {
      // @ts-ignore - fallback for older releases
      renderer.outputEncoding = THREE.sRGBEncoding;
    }
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.0;
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setClearColor(0x000000, 0);
    (renderer as any).physicallyCorrectLights = true;

    scene = new THREE.Scene();
    camera = new THREE.PerspectiveCamera(35, 1, 0.1, 100);
    camera.position.set(0, 0.1, 3.4);
    scene.add(camera);

    const geom = new THREE.PlaneGeometry(2, 2);
    const uniforms = {
      uTime: { value: 0 },
      uAspect: { value: 1 },
      uRadius: { value: 0.9 },
      uBase: { value: new THREE.Color(0xffe6f5) },
      uCore: { value: new THREE.Color(0xffffff) },
      uRippleAmp: { value: 0 },
      uTrigger: { value: 0 },
    };
    if (canvasEl.clientHeight) {
      uniforms.uAspect.value = canvasEl.clientWidth / canvasEl.clientHeight;
    }
    const mat = new THREE.ShaderMaterial({
      uniforms,
      transparent: true,
      depthTest: false,
      vertexShader: `
        varying vec2 vUv;
        void main() {
          vUv = uv;
          gl_Position = vec4(position, 1.0);
        }
      `,
      fragmentShader: `
        precision highp float;
        varying vec2 vUv;
        uniform float uTime;
        uniform float uAspect;
        uniform float uRadius;
        uniform float uRippleAmp;
        uniform float uTrigger;
        uniform vec3 uBase;
        uniform vec3 uCore;

        vec2 centerUV(vec2 uv) {
          vec2 p = uv * 2.0 - 1.0;
          p.x *= uAspect;
          return p;
        }

        void main() {
          vec2 p = centerUV(vUv);
          float d = length(p);
          float edge = 0.008;
          float mask = 1.0 - smoothstep(uRadius - edge, uRadius + edge, d);
          float fall = smoothstep(1.0, 0.0, d / uRadius);
          float w1 = sin(dot(p, vec2(1.0, 0.0)) * 24.0 - uTime * 3.5);
          float w2 = sin(dot(p, vec2(0.6, 0.8)) * 28.0 + uTime * 3.0);
          float wr = sin(d * 40.0 - uTime * 5.0);
          float waves = (w1 + w2) * 0.5 * uRippleAmp;
          waves += wr * 0.25 * uRippleAmp;
          waves *= smoothstep(0.0, 0.2, uTrigger) * smoothstep(1.0, 0.8, uTrigger);
          vec3 col = mix(uBase, uCore, pow(fall, 1.6));
          col += waves * 0.08;
          col *= 1.0 - 0.12 * pow(d / uRadius, 2.0);
          gl_FragColor = vec4(col, mask);
          if (gl_FragColor.a < 0.01) discard;
        }
      `,
    });
    globeMesh = new THREE.Mesh(geom, mat);
    globeUniforms = uniforms;
    scene.add(globeMesh);

    resizeRenderer();
    resizeObserver = new ResizeObserver(() => resizeRenderer());
    resizeObserver.observe(canvasEl);
    window.addEventListener("resize", resizeRenderer);

    return true;
  }

  function disposeThree() {
    stopLoop();
    window.removeEventListener("resize", resizeRenderer);
    resizeObserver?.disconnect();
    resizeObserver = null;

    if (globeMesh) {
      scene?.remove(globeMesh);
      globeMesh.geometry.dispose();
      const materials = Array.isArray(globeMesh.material)
        ? globeMesh.material
        : [globeMesh.material];
      materials.forEach((material: THREE.Material) => material.dispose());
      globeMesh = null;
    }
    globeUniforms = null;

    renderer?.dispose();
    renderer = null;
    scene = null;
    camera = null;
  }

  let healthRetry: ReturnType<typeof setTimeout> | null = null;

  onMount(() => {
    let mounted = true;
    const fetchHealth = async () => {
      try {
        const h = await health();
        backendStatus = `status=${h.status} | ollama=${h.ollama} | piper=${h.piper}`;
        if (healthRetry) {
          clearTimeout(healthRetry);
          healthRetry = null;
        }
      } catch (error) {
        backendStatus = "backend status: waiting…";
        if (mounted) {
          healthRetry = setTimeout(fetchHealth, 3000);
        }
      }
    };

    fetchHealth();
    setFallbackWallpaper();
    window.addEventListener("click", closeContextMenu);
    listTools()
      .then((items) => {
        tools = items ?? [];
      })
      .catch((error) => console.warn("tools fetch failed", error));
    if (appWindow) {
      appWindow
        .listen("tauri://blur", async () => {
          if (allowBlur) return;
          try {
            await appWindow.setFocus();
          } catch (error) {
            console.warn("focus blocked on blur, continuing anyway", error);
          }
        })
        .then((unlisten) => {
          if (mounted) unlistenBlur = unlisten;
          else unlisten();
        });
    }

    window.addEventListener("keydown", onKeydownGlobal);

    console.log("✅ onMount fired");
    (async () => {
      await tick();
      if (appWindow) {
        try {
          await appWindow.setFocus();
        } catch (error) {
          console.warn("focus blocked during mount, continuing anyway", error);
        }
      }
      if (!setupThree() || !globeMesh || !renderer || !scene || !camera) {
        console.error("❌ three runtime not ready");
        return;
      }
      const period = 1.8;
      startLoop((t, dt) => {
        if (!globeMesh || !globeUniforms) {
          console.warn("❌ globeMesh missing at runtime");
          return;
        }
        if (!globeMesh.parent) {
          console.warn("⚠️ globeMesh not attached to scene");
        }
        const timeSeconds = t / 1000;
        globeUniforms.uTime.value = timeSeconds;
        if (canvasEl && canvasEl.clientHeight) {
          globeUniforms.uAspect.value =
            canvasEl.clientWidth / canvasEl.clientHeight;
        }

        const idleAmp = 0.15;
        let pulseWindow: PulseWindow | null = null;
        if (typeof window !== "undefined") {
          pulseWindow = window as PulseWindow;
          if (
            !pulseWindow.__pulse ||
            performance.now() - pulseWindow.__pulse > 4000
          ) {
            if (Math.random() < 0.005) {
              pulseWindow.__pulse = performance.now();
            }
          }
        }
        const pulseAge =
          pulseWindow && pulseWindow.__pulse
            ? (performance.now() - pulseWindow.__pulse) / 1000
            : 10;
        let trig = 0;
        if (pulseAge >= 0 && pulseAge <= 2) {
          trig = pulseAge < 1 ? pulseAge : 2 - pulseAge;
        }
        globeUniforms.uTrigger.value = trig;
        globeUniforms.uRippleAmp.value = idleAmp + 0.6 * trig;
      }, renderer, scene, camera);
      if (DEBUG) console.log("🌍 render loop started");
    })();

    return () => {
      mounted = false;
      if (healthRetry) {
        clearTimeout(healthRetry);
        healthRetry = null;
      }
    };
  });

  onDestroy(() => {
    window.removeEventListener("keydown", onKeydownGlobal);
    window.removeEventListener("click", closeContextMenu);
    unlistenBlur?.();
    disposeThree();
    if (wallpaperObjectUrl) {
      URL.revokeObjectURL(wallpaperObjectUrl);
      wallpaperObjectUrl = null;
    }
  });
</script>

{#if viewMode === "prod"}
  <div
    class="stage"
    role="button"
    tabindex="0"
    on:click={toggleListen}
    on:keydown={(e)=> (e.key==='Enter'||e.key===' ') && toggleListen()}
    on:contextmenu={openContextMenu}
    style={wallpaperStyle}
  >
    <div class="ambient"></div>
    <div class="orb {state}">
      <canvas class="orb-canvas" bind:this={canvasEl}></canvas>
    </div>
    {#if response}
      <div class="reply" aria-live="polite">{response}</div>
    {/if}
    {#if lastHints.length}
      <div class="hint-panel">
        <div class="label">Install hints</div>
        <div class="hint-list">
          {#each lastHints as hint}
            <button on:click|stopPropagation={() => navigator.clipboard.writeText(hint)}>{hint}</button>
          {/each}
        </div>
      </div>
    {/if}
    {#if lastPlan.length}
      <div class="plan-panel">
        <div class="label">Install plan</div>
        <div class="plan-list">
          {#each lastPlan as step}
            <div class="plan-row">
              <div class="plan-info">
                <strong>{step.channel ?? "channel"}</strong>
                <span>{step.reason}</span>
                <span class="availability">{step.available ? "available" : "unavailable"}</span>
              </div>
              {#if step.cmd}
                {@const planCmd = step.cmd}
                <button on:click|stopPropagation={() => navigator.clipboard.writeText(planCmd)}>Copy cmd</button>
              {/if}
            </div>
          {/each}
        </div>
      </div>
    {/if}

    {#if permissionPrompt}
      {@const actionSummary = describeToolCall(permissionPrompt.call)}
      <div class="permission-card">
        <div class="label">{actionSummary}</div>
        <div class="perm-meta">Needs: {permissionPrompt.perms.join(", ")}</div>
        <div class="perm-buttons">
          <button class="primary" on:click|stopPropagation={allowOnce}>Allow</button>
          <button class="secondary" on:click|stopPropagation={denyPermission}>Cancel</button>
        </div>
        <button class="always-link" on:click|stopPropagation={allowAlways}>Always allow</button>
      </div>
    {/if}

    <!-- SOFT INPUT -->
    <div class="input-wrap {showInput ? 'visible' : ''}" role="group">
      <input
        bind:this={inputEl}
        bind:value={query}
        placeholder="Type to ask…"
        on:keydown={(e)=> {
          if (!showInput) showInput = true;
          if (e.key==='Enter') submitQuery();
        }}
        on:blur={() => { if (!query) showInput = false; }}
      />
    </div>

    {#if tools.length}
      <div class="tool-hint">
        Tools: {tools.map((t) => t.name).join(", ")}
      </div>
    {/if}

    <div class="wallpaper-hint">Right-click for options</div>

    {#if contextMenu.visible}
      <div
        class="context-menu"
        style={`top:${contextMenu.y}px;left:${contextMenu.x}px;`}
      >
        <button on:click={() => { loadRandomWallpaper(); closeContextMenu(); }}>Change wallpaper</button>
        <button on:click={() => { openTerminal(); closeContextMenu(); }}>Open terminal</button>
        <button on:click={() => { closeContextMenu(); window.location.reload(); }}>Refresh</button>
      </div>
    {/if}
    {#if clarifyPrompt}
      <div class="clarify-modal">
        <div class="clarify-card">
          <h3>Which app should I use?</h3>
          <p>{clarifyPrompt.phrase}</p>
          <div class="clarify-options">
            {#each clarifyPrompt.options as opt}
              <button on:click={() => handleClarifySelection(opt)}>
                {opt.name ?? opt.id}
                {#if opt.source}
                  <span>{opt.source}</span>
                {/if}
              </button>
            {/each}
          </div>
          {#if clarifyPrompt.category}
            <label class="clarify-default">
              <input type="checkbox" bind:checked={clarifyMakeDefault} />
              Make this my default for {clarifyPrompt.category} tasks.
            </label>
          {/if}
          <button class="secondary" on:click={() => { clarifyPrompt = null; clarifyMakeDefault = false; }}>Cancel</button>
        </div>
      </div>
    {/if}
  </div>
{/if}

<div class="mode-toggle">
  <button class:active={viewMode === "prod"} on:click={() => (viewMode = "prod")}>prod</button>
  <button class:active={viewMode === "test"} on:click={() => (viewMode = "test")}>test</button>
</div>

{#if viewMode === "test"}
  <div class="test-settings">
    <h2>Diagnostics</h2>
    <div class="status-line">
      {backendStatus} {isTauri() ? "(tauri)" : "(web)"}
    </div>
    <label class="toggle">
      <input type="checkbox" bind:checked={showTestChat} />
      <span>Chat → TTS panel</span>
    </label>
    <label class="toggle">
      <input type="checkbox" bind:checked={showWallpaperDebug} />
      <span>Wallpaper picker debug</span>
    </label>
    {#if showTestChat}
      <TestChat />
    {/if}
    {#if showWallpaperDebug}
      <div class="wallpaper-debug">
        <button on:click={testWallpaperPicker}>Test wallpaper picker</button>
        <div class="debug-text">{wallpaperDebug.message}</div>
        {#if wallpaperDebug.preview}
          <img src={wallpaperDebug.preview} alt="preview" />
        {/if}
      </div>
    {/if}
  </div>
{/if}

<style>
  :global(html, body){margin:0;height:100%;overflow:hidden;background:#f4f1ff;font-family:"Inter",system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;}
  .stage{
    position:relative;
    width:100vw;
    height:100vh;
    display:grid;
    place-items:center;
    background-size:cover;
    background-position:center;
    background-repeat:no-repeat;
  }
  .ambient{position:absolute;inset:0;background:radial-gradient(1200px 800px at 60% 70%, rgba(255,0,150,.06), transparent 60%);animation:drift 10s ease-in-out infinite alternate;}
  @keyframes drift{from{transform:translate(0,0) scale(1)} to{transform:translate(3%,-2%) scale(1.05)}}

  .orb{
    position:relative;
    width:140px;height:140px;border-radius:50%;
    background:radial-gradient(circle,#fff 0%,#fbe6ff 60%,#f0d4ff 100%);
    box-shadow:0 0 80px rgba(255,0,150,.25);
    transition:box-shadow .4s ease;
    will-change: transform, box-shadow, filter;
    overflow:hidden;
  }

  .orb-canvas{
    position:absolute;
    inset:0;
    width:100%;
    height:100%;
    border-radius:50%;
    display:block;
    pointer-events:none;
  }

  .orb.listening{
    animation: listenPulse .9s cubic-bezier(.2,.7,.2,1) infinite alternate;
    box-shadow:0 0 120px rgba(255,0,150,.45);
  }
  @keyframes listenPulse{
    from{ transform: translate3d(0,0,0) scale(1.06); }
    to{ transform: translate3d(0,0,0) scale(0.94); }
  }

  .reply{
    position:absolute;
    bottom:22%;
    max-width:360px;
    padding:16px 22px;
    border-radius:18px;
    background:rgba(255,255,255,.85);
    box-shadow:0 25px 60px rgba(41,0,82,.15);
    font-size:1rem;
    line-height:1.5;
    color:#4b2b52;
    text-align:center;
    backdrop-filter:blur(12px);
  }

  .input-wrap{
    position:absolute;
    bottom:40px;
    width:100%;
    display:flex;
    justify-content:center;
    transition:opacity .2s ease, transform .2s ease;
    opacity:0;
    transform:translateY(12px);
    pointer-events:none;
  }
  .input-wrap.visible{
    opacity:1;
    pointer-events:auto;
    transform:translateY(0);
  }
  .input-wrap input{
    width:240px;
    padding:12px 16px;
    border-radius:999px;
    border:1px solid rgba(75,43,82,.2);
    background:rgba(255,255,255,.95);
    font-size:.95rem;
    outline:none;
    box-shadow:0 12px 25px rgba(41,0,82,.08);
  }

  .permission-card{
    position:absolute;
    top:20%;
    left:50%;
    transform:translateX(-50%);
    padding:14px 18px;
    border-radius:14px;
    background:rgba(255,255,255,.9);
    box-shadow:0 15px 30px rgba(0,0,0,.15);
    width:260px;
  }
  .permission-card .perm-meta{
    margin:6px 0 10px;
    font-size:.85rem;
    color:#6b4c73;
  }
  .perm-buttons{
    margin-top:10px;
    display:flex;
    gap:8px;
    flex-wrap:wrap;
  }
  .perm-buttons button{
    flex:1;
    padding:10px 12px;
    border-radius:10px;
    cursor:pointer;
    border:1px solid transparent;
  }
  .perm-buttons .primary{
    background:#4b2b52;
    color:#fff;
  }
  .perm-buttons .secondary{
    background:#fff;
    border-color:rgba(75,43,82,.25);
  }
  .always-link{
    margin-top:8px;
    border:none;
    background:none;
    color:#6b4c73;
    text-decoration:underline;
    font-size:.85rem;
    cursor:pointer;
  }
  .tool-hint{
    position:absolute;
    top:28px;
    right:24px;
    font-size:.85rem;
    opacity:.75;
    background:rgba(255,255,255,.5);
    padding:6px 10px;
    border-radius:10px;
  }
  .mode-toggle{
    position:fixed;
    top:14px;
    right:12px;
    display:flex;
    gap:6px;
    z-index:30;
  }
  .mode-toggle button{
    border:none;
    padding:6px 10px;
    border-radius:8px;
    cursor:pointer;
    background:rgba(255,255,255,.55);
  }
  .mode-toggle button.active{
    background:#4b2b52;
    color:#fff;
  }
  .wallpaper-hint{
    position:absolute;
    bottom:90px;
    right:24px;
    font-size:.75rem;
    opacity:.7;
    background:rgba(255,255,255,.4);
    padding:4px 8px;
    border-radius:8px;
  }
  .context-menu{
    position:fixed;
    background:rgba(30,22,45,.95);
    color:#fff;
    border-radius:10px;
    padding:6px;
    display:flex;
    flex-direction:column;
    gap:4px;
    z-index:99;
    min-width:140px;
    box-shadow:0 12px 24px rgba(0,0,0,.25);
  }
  .context-menu button{
    border:none;
    background:transparent;
    color:inherit;
    text-align:left;
    padding:6px 8px;
    border-radius:6px;
    cursor:pointer;
  }
  .context-menu button:hover{
    background:rgba(255,255,255,.15);
  }
  .hint-panel{
    position:absolute;
    bottom:15%;
    left:50%;
    transform:translateX(-50%);
    background:rgba(255,255,255,.92);
    padding:12px 16px;
    border-radius:14px;
    max-width:320px;
    box-shadow:0 12px 30px rgba(0,0,0,.2);
    font-size:.85rem;
  }
  .hint-panel .hint-list{
    margin-top:8px;
    display:flex;
    flex-direction:column;
    gap:6px;
  }
  .hint-panel .hint-list button{
    border:none;
    border-radius:8px;
    padding:6px 8px;
    background:rgba(75,43,82,.1);
    cursor:pointer;
    text-align:left;
    font-size:.8rem;
  }
  .plan-panel{
    position:absolute;
    bottom:5%;
    left:50%;
    transform:translateX(-50%);
    background:rgba(255,255,255,.95);
    padding:14px 18px;
    border-radius:14px;
    width:360px;
    max-width:90vw;
    box-shadow:0 12px 30px rgba(0,0,0,.22);
    font-size:.85rem;
  }
  .clarify-modal{
    position:fixed;
    inset:0;
    background:rgba(10,9,19,.45);
    display:flex;
    align-items:center;
    justify-content:center;
    z-index:120;
    backdrop-filter:blur(6px);
  }
  .clarify-card{
    background:#fff;
    padding:18px 20px;
    border-radius:16px;
    width:320px;
    box-shadow:0 18px 40px rgba(0,0,0,.25);
    text-align:center;
  }
  .clarify-options{
    display:flex;
    flex-direction:column;
    gap:10px;
    margin:16px 0;
  }
  .clarify-options button{
    border:none;
    border-radius:10px;
    padding:10px 12px;
    cursor:pointer;
    background:rgba(75,43,82,.1);
    font-size:.9rem;
    display:flex;
    flex-direction:column;
    gap:2px;
  }
  .clarify-options button span{
    font-size:.7rem;
    opacity:.7;
  }
  .clarify-default{
    margin-bottom:12px;
    display:flex;
    align-items:center;
    justify-content:center;
    gap:8px;
    font-size:.85rem;
    color:#3a2b4d;
  }
  .clarify-default input{
    accent-color:#4b2b52;
  }
  .plan-list{
    margin-top:10px;
    display:flex;
    flex-direction:column;
    gap:10px;
  }
  .plan-row{
    display:flex;
    align-items:flex-start;
    justify-content:space-between;
    gap:10px;
    background:rgba(75,43,82,.05);
    padding:8px;
    border-radius:10px;
  }
  .plan-row button{
    border:none;
    border-radius:8px;
    padding:6px 8px;
    cursor:pointer;
    font-size:.75rem;
    background:rgba(75,43,82,.15);
  }
  .plan-info span{
    display:block;
    font-size:.75rem;
    opacity:.8;
  }
  .plan-info .availability{
    text-transform:uppercase;
  }
  .test-settings{
    position:fixed;
    inset:0;
    padding:80px 40px 40px;
    overflow:auto;
    background:rgba(22,16,28,.95);
    color:#fff;
    z-index:10;
  }
  .test-settings h2{
    margin-top:0;
  }
  .status-line{
    font-size:.85rem;
    opacity:.85;
    margin-bottom:12px;
  }
  .test-settings .toggle{
    display:flex;
    align-items:center;
    gap:8px;
    margin-bottom:12px;
    font-weight:500;
  }
  .test-settings input[type="checkbox"]{
    width:18px;
    height:18px;
  }
  .wallpaper-debug{
    margin-top:20px;
    background:rgba(255,255,255,.08);
    padding:16px;
    border-radius:12px;
    max-width:320px;
  }
  .wallpaper-debug button{
    width:100%;
    margin-bottom:8px;
    padding:6px 8px;
  }
  .wallpaper-debug img{
    width:100%;
    max-height:200px;
    object-fit:cover;
    border-radius:8px;
    margin-top:8px;
  }
</style>
