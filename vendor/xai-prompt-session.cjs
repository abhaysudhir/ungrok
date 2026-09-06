"use strict";
const SYNTHETIC_USER = Symbol("ungrok synthetic continuation");

/**
 * Sand / Grok Bot custom inference session.
 *
 * ungrok hardened derivative; see UPSTREAM.md and LICENSE.
 * Runs the official subscription client; Grok remains the tool executor.
 * Configuration is an immutable
 * per-session snapshot read only from the explicit envFile argument.
 */

const fs = require("fs");
const path = require("path");
const { URL } = require("url");
const { AsyncLocalStorage } = require("async_hooks");
const configContext = new AsyncLocalStorage();
const { loadConfig, runStep } = require("./subscription-runtime.cjs");

function env(name, fallback) {
  const v = configContext.getStore()?.[name];
  if (v == null || v === "") return fallback;
  return v;
}

function truthy(v) {
  if (v == null || v === "") return false;
  const s = String(v).trim().toLowerCase();
  return s === "1" || s === "true" || s === "yes" || s === "on" || s === "enabled";
}

function unwrapRedacted(value, seen) {
  if (value == null) return value;
  const t = typeof value;
  if (t === "string" || t === "number" || t === "boolean") return value;
  if (t !== "object") return value;
  // Preserve bytes before object enumeration/toJSON. Enumerating Uint8Array
  // expands every image byte into a numeric JSON property.
  if (Buffer.isBuffer(value) || ArrayBuffer.isView(value) || value instanceof ArrayBuffer || value instanceof URL) return value;
  seen = seen || new WeakSet();
  if (seen.has(value)) return undefined;
  seen.add(value);
  if (typeof value.unwrap === "function") {
    try {
      return unwrapRedacted(value.unwrap("unsafe_always_allowed", {}), seen);
    } catch {
      /* fall through */
    }
  }
  if (Array.isArray(value)) return value.map((v) => unwrapRedacted(v, seen));
  if (typeof value.toJSON === "function") {
    try {
      const j = value.toJSON();
      if (j !== value) return unwrapRedacted(j, seen);
    } catch {
      /* ignore */
    }
  }
  if (typeof value.valueOf === "function") {
    try {
      const v = value.valueOf();
      if (v !== value && (typeof v === "string" || typeof v === "number")) return v;
    } catch {
      /* ignore */
    }
  }
  const protoToString = Object.prototype.toString;
  if (typeof value.toString === "function" && value.toString !== protoToString) {
    try {
      const s = value.toString();
      if (s && s !== "[object Object]" && Object.keys(value).length === 0) return s;
    } catch {
      /* ignore */
    }
  }
  const out = {};
  for (const [k, v] of Object.entries(value)) {
    out[k] = unwrapRedacted(v, seen);
  }
  return out;
}

function asString(value) {
  const v = unwrapRedacted(value);
  if (v instanceof URL) return v.href;
  if (Buffer.isBuffer(v) || ArrayBuffer.isView(v) || v instanceof ArrayBuffer) return "[binary data omitted]";
  if (v == null) return "";
  if (typeof v === "string") return v;
  if (typeof v === "number" || typeof v === "boolean") return String(v);
  try {
    return JSON.stringify(v);
  } catch {
    return String(v);
  }
}

function sanitizeToolId(id) {
  const raw = asString(id) || "tool";
  const cleaned = raw.replace(/[^a-zA-Z0-9_-]/g, "_");
  return cleaned || "tool";
}

function sanitizeToolName(name) {
  const raw = asString(name) || "tool";
  const cleaned = raw.replace(/[^a-zA-Z0-9_-]/g, "_");
  return cleaned || "tool";
}

function isPlainObject(v) {
  return v != null && typeof v === "object" && !Array.isArray(v);
}

function normalizeToolParameters(raw) {
  let schema = raw;
  if (schema && typeof schema === "object") {
    if (schema.jsonSchema) schema = schema.jsonSchema;
    else if (schema.inputSchema) schema = schema.inputSchema;
    else if (schema.schema) schema = schema.schema;
  }
  schema = unwrapRedacted(schema);
  if (!isPlainObject(schema) || Array.isArray(schema)) {
    return { type: "object", properties: {} };
  }
  const type = schema.type;
  if (type == null || type === "object") {
    return {
      ...schema,
      type: "object",
      properties: isPlainObject(schema.properties) ? schema.properties : {},
    };
  }
  return {
    type: "object",
    properties: { value: schema },
  };
}

function mapModelId(requestedModel) {
  const config = configContext.getStore();
  if (!config) throw new Error("ungrok model requires a session configuration");
  return config.UNGROK_MODEL || config.UNGROK_PROVIDER + "-default";
}


function normalizeUsage(usage) {
  const u = usage && typeof usage === "object" ? usage : {};
  const promptTokens = Number(u.promptTokens ?? u.prompt_tokens ?? u.inputTokens ?? u.input_tokens ?? 0) || 0;
  const completionTokens =
    Number(u.completionTokens ?? u.completion_tokens ?? u.outputTokens ?? u.output_tokens ?? 0) || 0;
  const totalTokens = Number(u.totalTokens ?? u.total_tokens ?? 0) || promptTokens + completionTokens;
  return { promptTokens, completionTokens, totalTokens };
}

function normalizeExtendedUsage(usage) {
  const u = usage && typeof usage === "object" ? usage : {};
  return {
    inputTokens: Number(u.inputTokens ?? u.prompt_tokens ?? u.promptTokens ?? 0) || 0,
    outputTokens: Number(u.outputTokens ?? u.completion_tokens ?? u.completionTokens ?? 0) || 0,
    cacheReadTokens: Number(u.cacheReadTokens ?? u.cache_read_tokens ?? 0) || 0,
    cacheWriteTokens: Number(u.cacheWriteTokens ?? u.cache_write_tokens ?? 0) || 0,
    maxTokens: Number(u.maxTokens ?? u.max_tokens ?? 0) || 0,
  };
}

function parseArgs(raw) {
  if (raw == null || raw === "") return {};
  if (typeof raw === "object") return unwrapRedacted(raw) || {};
  const s = asString(raw).trim();
  if (!s) return {};
  try {
    return JSON.parse(s);
  } catch {
    return { _raw: s };
  }
}

function binaryImageUrl(value, declaredMime) {
  let bytes;
  if (Buffer.isBuffer(value)) bytes = value;
  else if (ArrayBuffer.isView(value)) bytes = Buffer.from(value.buffer, value.byteOffset, value.byteLength);
  else if (value instanceof ArrayBuffer) bytes = Buffer.from(value);
  else return null;
  if (bytes.length > 20 * 1024 * 1024) throw new Error("image exceeds 20 MiB limit");
  let mime;
  if (bytes.length >= 8 && bytes.subarray(0, 8).equals(Buffer.from([137,80,78,71,13,10,26,10]))) mime = "image/png";
  else if (bytes.length >= 3 && bytes[0] === 255 && bytes[1] === 216 && bytes[2] === 255) mime = "image/jpeg";
  else if (bytes.length >= 6 && /^(GIF87a|GIF89a)$/.test(bytes.subarray(0,6).toString("ascii"))) mime = "image/gif";
  else if (bytes.length >= 12 && bytes.subarray(0,4).toString("ascii") === "RIFF" && bytes.subarray(8,12).toString("ascii") === "WEBP") mime = "image/webp";
  if (!mime) return null;
  if (declaredMime != null && String(declaredMime).toLowerCase().replace("image/jpg", "image/jpeg") !== mime) return null;
  return `data:${mime};base64,${bytes.toString("base64")}`;
}

function convertContentPart(part) {
  const p = unwrapRedacted(part);
  if (p == null) return null;
  if (typeof p === "string") return { kind: "text", text: p };
  if (typeof p !== "object") return { kind: "text", text: asString(p) };
  const type = asString(p.type || p.kind || "");
  if (type === "text" || type === "input_text" || type === "output_text") {
    return { kind: "text", text: asString(p.text ?? p.content ?? "") };
  }
  if (type === "reasoning" || type === "thinking") {
    return { kind: "reasoning", text: asString(p.text ?? p.textDelta ?? p.thinking ?? "") };
  }
  if (type === "tool-call" || type === "tool_use" || type === "function_call") {
    return {
      kind: "tool-call",
      id: sanitizeToolId(p.toolCallId ?? p.tool_call_id ?? p.id),
      name: sanitizeToolName(p.toolName ?? p.tool_name ?? p.name ?? p.function?.name),
      args: parseArgs(p.args ?? p.arguments ?? p.input ?? p.function?.arguments),
    };
  }
  if (type === "tool-result" || type === "tool_result") {
    const result = p.result ?? p.content ?? p.output ?? p.value;
    return {
      kind: "tool-result",
      id: sanitizeToolId(p.toolCallId ?? p.tool_call_id ?? p.id),
      name: sanitizeToolName(p.toolName ?? p.tool_name ?? p.name),
      content: typeof result === "string" ? result : asString(result),
      isError: Boolean(p.isError ?? p.is_error),
    };
  }
  if (type === "image" || type === "image_url" || type === "input_image") {
    const binary = p.image ?? p.data ?? p.source?.data;
    const declaredMime = p.mediaType ?? p.mimeType ?? p.mime_type ?? p.media_type ?? p.source?.media_type ?? p.source?.mimeType;
    const binaryUrl = binaryImageUrl(binary, declaredMime);
    if (binaryUrl) return { kind: "image", url: binaryUrl };
    const urlObject = p.image_url?.url ?? p.image_url ?? p.url ?? p.image ?? p.source?.url;
    if (urlObject instanceof URL) {
      if (!["https:", "http:"].includes(urlObject.protocol)) throw new Error("unsupported image URL");
      return { kind: "image", url: urlObject.href };
    }
    const url = p.image_url?.url ?? (typeof p.image_url === "string" ? p.image_url : undefined) ??
      p.url ?? (typeof p.image === "string" ? p.image : undefined) ??
      (p.source?.type === "url" ? p.source.url : undefined);
    if (typeof url === "string" && url) {
      if (/^data:image\/(png|jpeg|gif|webp);base64,[A-Za-z0-9+/]+={0,2}$/i.test(url)) return { kind: "image", url };
      let parsed;
      try { parsed = new URL(url); } catch { throw new Error("invalid image URL"); }
      if (!["https:", "http:"].includes(parsed.protocol)) throw new Error("unsupported image URL");
      return { kind: "image", url };
    }
    const source = p.source?.type === "base64" ? p.source : p;
    const mime = source.media_type ?? source.mimeType ?? source.mime_type;
    const data = source.data;
    // Do not stringify binary objects or truncate image bytes into invalid URLs.
    if (typeof mime === "string" && /^image\/(png|jpeg|gif|webp)$/i.test(mime) &&
        typeof data === "string" && data.length && data.length <= Math.ceil(20 * 1024 * 1024 / 3) * 4 && /^[A-Za-z0-9+/]*={0,2}$/.test(data) &&
        data.length % 4 !== 1 && (Buffer.from(data, "base64").toString("base64") === data ||
          Buffer.from(data, "base64").toString("base64").replace(/=+$/, "") === data)) {
      return { kind: "image", url: `data:${mime.toLowerCase()};base64,${data}` };
    }
    throw new Error("missing or unsupported image payload");
  }
  if (p.text) return { kind: "text", text: asString(p.text) };
  return null;
}

function convertMessage(rawMsg) {
  const msg = unwrapRedacted(rawMsg) || {};
  const role = asString(msg.role || "user");
  const out = [];

  if (role === "tool") {
    const id = sanitizeToolId(msg.tool_call_id ?? msg.toolCallId ?? msg.id);
    out.push({
      role: "tool",
      tool_call_id: id,
      content: asString(msg.content ?? msg.result ?? ""),
    });
    return out;
  }

  const texts = [];
  const toolCalls = [];
  const toolResults = [];
  const images = [];
  const promoteReasoning = truthy(env("SAND_XAI_PROMOTE_REASONING", "0"));

  const pushContent = (content) => {
    if (content == null) return;
    if (typeof content === "string") {
      if (content) texts.push(content);
      return;
    }
    if (Array.isArray(content)) {
      for (const part of content) {
        const c = convertContentPart(part);
        if (!c) continue;
        if (c.kind === "text" && c.text) texts.push(c.text);
        else if (c.kind === "reasoning" && c.text && promoteReasoning) texts.push(c.text);
        else if (c.kind === "tool-call") toolCalls.push(c);
        else if (c.kind === "tool-result") toolResults.push(c);
        else if (c.kind === "image") images.push(c);
      }
      return;
    }
    const s = asString(content);
    if (s) texts.push(s);
  };

  pushContent(msg.content);
  if (Array.isArray(msg.toolCalls) || Array.isArray(msg.tool_calls)) {
    for (const tc of msg.toolCalls || msg.tool_calls) {
      const c = convertContentPart({ type: "tool-call", ...unwrapRedacted(tc) });
      if (c && c.kind === "tool-call") toolCalls.push(c);
    }
  }

  for (const tr of toolResults) {
    out.push({
      role: "tool",
      tool_call_id: tr.id,
      content: tr.isError ? `ERROR: ${tr.content}` : tr.content,
    });
  }

  if (role === "assistant" || role === "user" || role === "system") {
    const openai = { role };
    if (images.length && (role === "user" || role === "system")) {
      openai.content = [
        ...texts.map((t) => ({ type: "text", text: t })),
        ...images.map((img) => ({ type: "image_url", image_url: { url: img.url } })),
      ];
    } else {
      openai.content = texts.join("\n") || (toolCalls.length ? "" : "");
      if (!openai.content) openai.content = toolCalls.length ? null : "";
    }
    if (role === "assistant" && toolCalls.length) {
      openai.tool_calls = toolCalls.map((tc) => ({
        id: tc.id,
        type: "function",
        function: {
          name: tc.name,
          arguments: JSON.stringify(tc.args ?? {}),
        },
      }));
    }
    if (openai.content || openai.tool_calls) out.push(openai);
  }

  return out;
}

function convertMessages(rawList) {
  const list = Array.isArray(rawList) ? rawList : rawList == null ? [] : [rawList];
  const out = [];
  for (const msg of list) {
    try {
      out.push(...convertMessage(msg));
    } catch (err) {
      throw new Error("ungrok message conversion failed; no partial conversation was sent");
    }
  }
  if (out.length && out[out.length - 1].role === "assistant") {
    out.push({ role: "user", content: "(continue)", [SYNTHETIC_USER]: true });
  }
  if (!out.length) {
    out.push({ role: "user", content: "(empty)" });
  }
  return out;
}

function intEnv(name, fallback) {
  const n = Number(env(name, String(fallback)));
  return Number.isFinite(n) && n >= 1 ? Math.min(Math.floor(n), 2000000) : fallback;
}

function messageChars(msg) {
  if (!msg) return 0;
  let n = 0;
  if (typeof msg.content === "string") n += msg.content.length;
  else if (Array.isArray(msg.content)) {
    for (const p of msg.content) {
      if (!p) continue;
      if (p.type === "image_url") continue; // Image bytes have separate request-size limits.
      if (typeof p === "string") n += p.length;
      else if (typeof p.text === "string") n += p.text.length;
      else n += JSON.stringify(p).length;
    }
  }
  if (Array.isArray(msg.tool_calls)) n += JSON.stringify(msg.tool_calls).length;
  return n;
}

function clipText(s, max) {
  if (typeof s !== "string" || s.length <= max) return s;
  const keep = Math.max(64, Math.floor((max - 48) / 2));
  return `${s.slice(0, keep)}\n…[truncated ${s.length - max} chars]…\n${s.slice(-keep)}`;
}

function clipMessageContent(msg, max) {
  if (msg && Array.isArray(msg.content)) {
    let remaining = max;
    return { ...msg, content: msg.content.map(part => {
      if (typeof part === "string") {
        const clipped = remaining > 0 ? clipText(part, remaining) : "";
        remaining = Math.max(0, remaining - clipped.length);
        return clipped;
      }
      if (part && typeof part.text === "string") {
        const clipped = remaining > 0 ? clipText(part.text, remaining) : "";
        remaining = Math.max(0, remaining - clipped.length);
        return { ...part, text: clipped };
      }
      return part;
    }) };
  }
  if (!msg || typeof msg.content !== "string" || msg.content.length <= max) return msg;
  return { ...msg, content: clipText(msg.content, max) };
}

function hasToolCalls(msg) {
  return Boolean(msg && msg.role === "assistant" && Array.isArray(msg.tool_calls) && msg.tool_calls.length);
}

function mergeConsecutiveRoles(msgs) {
  const out = [];
  for (const raw of msgs) {
    const m = { ...raw };
    if (Array.isArray(m.tool_calls)) m.tool_calls = m.tool_calls.map((t) => ({ ...t }));
    const last = out[out.length - 1];
    if (m.role === "user" && last && last.role === "user") {
      if (Array.isArray(last.content) || Array.isArray(m.content)) {
        const parts = (content) => Array.isArray(content) ? content :
          typeof content === "string" && content ? [{ type: "text", text: content }] : [];
        last.content = [...parts(last.content), ...parts(m.content)];
      } else {
        const a = typeof last.content === "string" ? last.content : "";
        const b = typeof m.content === "string" ? m.content : "";
        last.content = [a, b].filter(Boolean).join("\n\n");
      }
      continue;
    }
    if (m.role === "assistant" && last && last.role === "assistant") {
      const texts = [];
      if (typeof last.content === "string" && last.content) texts.push(last.content);
      if (typeof m.content === "string" && m.content) texts.push(m.content);
      if (texts.length) last.content = texts.join("\n");
      if (m.tool_calls && m.tool_calls.length) {
        last.tool_calls = [...(last.tool_calls || []), ...m.tool_calls];
      }
      continue;
    }
    out.push(m);
  }
  return out;
}

// Gemini: a function-call turn must follow a user or function-response turn.
// Never start (after system) with assistant/tool, and never leave orphan tool rows.
function normalizeToolTurns(msgs) {
  let list = mergeConsecutiveRoles(msgs);
  const out = [];
  for (const m of list) {
    if (m.role === "system") {
      out.push(m);
      continue;
    }
    if (m.role === "tool") {
      const last = out[out.length - 1];
      if (last && (hasToolCalls(last) || last.role === "tool")) out.push(m);
      continue;
    }
    if (hasToolCalls(m)) {
      const last = out[out.length - 1];
      if (!last || (last.role !== "user" && last.role !== "tool")) continue;
    }
    out.push(m);
  }
  // After system, conversation must start with user.
  let i = 0;
  while (i < out.length && out[i].role === "system") i++;
  while (i < out.length && out[i].role !== "user") {
    if (out[i].role === "assistant") {
      let j = i + 1;
      while (j < out.length && out[j].role === "tool") j++;
      out.splice(i, j - i);
      continue;
    }
    out.splice(i, 1);
  }
  if (i >= out.length) {
    out.push({ role: "user", content: "(continue)" });
  }
  return out;
}

function dropOldestTurn(msgs) {
  let i = 0;
  while (i < msgs.length && msgs[i].role === "system") i++;
  if (i >= msgs.length - 1) return false;
  // Drop the oldest user turn AND the agent loop that followed it, so a
  // function-call never becomes the first turn after system.
  if (msgs[i].role === "user") {
    let j = i + 1;
    while (j < msgs.length && (msgs[j].role !== "user" || msgs[j][SYNTHETIC_USER])) j++;
    if (j >= msgs.length) return false;
    msgs.splice(i, j - i);
    return true;
  }
  if (msgs[i].role === "assistant") {
    let j = i + 1;
    while (j < msgs.length - 1 && msgs[j].role === "tool") j++;
    msgs.splice(i, j - i);
    return true;
  }
  msgs.splice(i, 1);
  return true;
}

// Gemini / Antigravity reject requests over ~1,048,576 input tokens. Long Grok Bot
// threads plus one huge tool result (file dump) blow that. Keep system + recent turns.
function trimConvertedMessages(messages, model) {
  const list = Array.isArray(messages) ? messages.map((m) => ({ ...m })) : [];
  // Keep a bounded number of recent images across multi-message uploads.
  // Never count their encoded bytes as text tokens or silently remove the
  // latest request. Older images are replaced by an explicit context marker.
  const lastRequest = list.findLastIndex(m => m.role === "user" && !m[SYNTHETIC_USER]);
  let recentImages = 0;
  for (let i = list.length - 1; i >= 0; i--) {
    if (!Array.isArray(list[i].content)) continue;
    const parts = [...list[i].content];
    for (let j = parts.length - 1; j >= 0; j--) {
      if (parts[j]?.type !== "image_url") continue;
      recentImages++;
      if (recentImages > 20) {
        if (i >= lastRequest) throw new Error("latest request exceeds 20 image context limit");
        parts[j] = { type: "text", text: "[Earlier image omitted from context; reattach if needed.]" };
      }
    }
    list[i].content = parts;
  }
  const gemini = /gemini/i.test(String(model || ""));
  const maxTool = intEnv("SAND_XAI_MAX_TOOL_CHARS", 12000);
  const maxSys = intEnv("SAND_XAI_MAX_SYSTEM_CHARS", 60000);
  const maxOther = intEnv("SAND_XAI_MAX_MESSAGE_CHARS", 24000);
  const defaultTotal = gemini ? 280000 : 400000;
  const maxTotal = intEnv("SAND_XAI_MAX_INPUT_CHARS", defaultTotal);

  const before = list.reduce((n, m) => n + messageChars(m), 0);
  const beforeCount = list.length;

  for (let i = 0; i < list.length; i++) {
    const role = list[i].role;
    const cap = role === "system" ? maxSys : role === "tool" ? maxTool : maxOther;
    list[i] = clipMessageContent(list[i], cap);
  }

  let total = list.reduce((n, m) => n + messageChars(m), 0);
  let dropped = 0;
  while (total > maxTotal && list.length > 3 && dropOldestTurn(list)) {
    dropped += 1;
    total = list.reduce((n, m) => n + messageChars(m), 0);
  }

  if (total > maxTotal) {
    for (let i = 0; i < list.length && total > maxTotal; i++) {
      if (list[i].role !== "tool") continue;
      const prev = messageChars(list[i]);
      list[i] = { ...list[i], content: "[truncated: prior tool output omitted to fit context]" };
      total += messageChars(list[i]) - prev;
    }
  }

  const normalized = normalizeToolTurns(list);
  const after = normalized.reduce((n, m) => n + messageChars(m), 0);
  if (after > maxTotal) throw new Error("latest request and tool context exceed text budget; start a shorter task");
  if (after !== before || dropped || normalized.length !== beforeCount) {
    console.error(
      `[ungrok] trimmed input chars ${before}→${after} msgs ${beforeCount}→${normalized.length} droppedTurns=${dropped} model=${model}`
    );
  }
  return normalized;
}

async function prepareInlineImages(messages, signal) {
  const maxInputChars = Math.ceil((20 * 1024 * 1024) / 3) * 4;
  const maxOutputBytes = 6 * 1024 * 1024;
  const copied = messages.map((message) => ({
    ...message,
    content: Array.isArray(message.content)
      ? message.content.map((part) => part && typeof part === "object" ? { ...part } : part)
      : message.content,
  }));
  for (const message of copied) {
    if (!Array.isArray(message.content)) continue;
    for (const part of message.content) {
      if (signal?.aborted) throw new Error("provider request cancelled");
      const url = part?.type === "image_url" ? part.image_url?.url : undefined;
      if (typeof url !== "string" || url.length <= 200000) continue;
      const prefix = /^data:image\/[A-Za-z0-9.+-]+;base64,/.exec(url);
      if (!prefix) continue; // Remote URLs are never fetched by this helper.
      const data = url.slice(prefix[0].length);
      if (data.length > maxInputChars) throw new Error("ungrok image exceeds 20 MiB input limit");
      const installed = path.join(__dirname, "ungrok-resize-image.py");
      const source = path.join(__dirname, "../scripts/resize_image.py");
      const helper = fs.existsSync(installed) ? installed : fs.existsSync(source) ? source : null;
      if (!helper) throw new Error("ungrok large image requires the resize helper and Python Pillow");
      const resized = await new Promise((resolve, reject) => {
        let child;
        let settled = false;
        let timer;
        let size = 0;
        const chunks = [];
        const finish = (error, value) => {
          if (settled) return;
          settled = true;
          clearTimeout(timer);
          signal?.removeEventListener("abort", onAbort);
          if (error && child && child.exitCode === null) child.kill("SIGKILL");
          if (error) reject(error); else resolve(value);
        };
        const fail = () => finish(new Error("ungrok image resize failed; check Python Pillow and image limits"));
        const onAbort = () => finish(new Error("provider request cancelled"));
        try {
          child = require("child_process").spawn("python3", [helper], {
            shell: false, stdio: ["pipe", "pipe", "ignore"],
          });
        } catch { fail(); return; }
        timer = setTimeout(() => finish(new Error("ungrok image resize deadline exceeded")), 20000);
        signal?.addEventListener("abort", onAbort, { once: true });
        child.on("error", fail);
        child.stdin.on("error", fail);
        child.stdout.on("error", fail);
        child.stdout.on("data", (chunk) => {
          if (settled) return;
          size += chunk.length;
          if (size > maxOutputBytes) {
            finish(new Error("ungrok image resize output exceeds limit"));
            return;
          }
          chunks.push(chunk);
        });
        child.on("close", (code) => {
          if (settled) return;
          if (code !== 0) { fail(); return; }
          try {
            const result = JSON.parse(Buffer.concat(chunks).toString("utf8"));
            if (result?.mimeType !== "image/jpeg" || typeof result.data !== "string" ||
                !result.data || result.data.length > Math.ceil((4 * 1024 * 1024) / 3) * 4 ||
                result.data.length % 4 !== 0 || !/^[A-Za-z0-9+/]+={0,2}$/.test(result.data)) {
              fail(); return;
            }
            finish(null, result);
          } catch { fail(); }
        });
        if (signal?.aborted) { onAbort(); return; }
        try { child.stdin.end(JSON.stringify({ data })); } catch { fail(); }
      });
      part.image_url = { ...part.image_url, url: "data:" + resized.mimeType + ";base64," + resized.data };
    }
  }
  return copied;
}

function convertTools(tools) {
  if (!Array.isArray(tools) || tools.length === 0) return undefined;
  return tools.map((tool) => {
    const t = unwrapRedacted(tool) || {};
    return {
      type: "function",
      function: {
        name: sanitizeToolName(t.name),
        description: clipText(asString(t.description || t.name || ""), 800),
        parameters: normalizeToolParameters(t.parameters ?? t.inputSchema ?? t.schema),
      },
    };
  });
}


function buildResponseMessages(text, toolCalls) {
  if (toolCalls.length) {
    const content = [];
    if (text) content.push({ type: "text", text });
    for (const tc of toolCalls) {
      content.push({
        type: "tool-call",
        toolCallId: tc.id,
        toolName: tc.name,
        args: tc.args,
      });
    }
    return [{ role: "assistant", content }];
  }
  return [{ role: "assistant", content: text || "" }];
}

function errorResult(modelId, invocationId, err) {
  const message = err && err.message ? err.message : String(err);
  const usage = normalizeUsage({});
  const response = {
    modelId,
    messages: [{ role: "assistant", content: "" }],
    finishReason: "error",
  };
  const parts = [
    { type: "error", error: err instanceof Error ? err : new Error(message) },
    { type: "finish", finishReason: "error", usage, response },
  ];
  return {
    parts,
    response,
    usage,
    extendedUsage: normalizeExtendedUsage({}),
    providerMetadata: {},
    invocationId,
  };
}

async function runStream({ model, messages, tools, invocationId, config, signal, onPart }) {
  try {
    const converted = await prepareInlineImages(trimConvertedMessages(convertMessages(messages), model), signal);
    const result = await runStep({ config, messages: converted, tools: convertTools(tools) || [], signal });
    const parts = [];
    const push = part => { parts.push(part); if (onPart) onPart(part); };
    if (result.text) push({ type: "text-delta", textDelta: result.text });
    const toolCalls = result.toolCalls.map(call => ({
      id: "call_" + require("crypto").randomUUID().replace(/-/g, ""),
      name: call.name,
      args: JSON.parse(call.arguments),
    }));
    for (const call of toolCalls) push({ type: "tool-call", toolCallId: call.id, toolName: call.name, args: call.args });
    const usage = normalizeUsage(result.usage || {});
    const response = { modelId: model, messages: buildResponseMessages(result.text, toolCalls), finishReason: toolCalls.length ? "tool-calls" : "stop" };
    push({ type: "finish", finishReason: response.finishReason, usage, response });
    return { parts, response, usage, extendedUsage: normalizeExtendedUsage(result.usage || {}), providerMetadata: {}, invocationId };
  } catch (error) {
    const message = error?.code === "PROVIDER_REFUSED"
      ? "native provider refused this request; no retry was attempted"
      : "native subscription step failed; run ungrok doctor or probe to check client readiness";
    return errorResult(model, invocationId, new Error(message));
  }
}

// A custom iterator, not an async generator: return() must cancel even while
// next() is waiting for upstream data.
function liveParts(controller) {
  const values = [];
  const waiters = [];
  let ended = false;
  const finish = () => {
    ended = true;
    while (waiters.length) waiters.shift()({ done: true, value: undefined });
  };
  return {
    push(value) {
      if (ended) return;
      if (waiters.length) waiters.shift()({ done: false, value });
      else if (values.length < 10000) values.push(value);
      else { controller.abort(); finish(); }
    },
    finish,
    [Symbol.asyncIterator]() { return this; },
    next() {
      if (values.length) return Promise.resolve({ done: false, value: values.shift() });
      if (ended) return Promise.resolve({ done: true, value: undefined });
      return new Promise(resolve => waiters.push(resolve));
    },
    return() {
      values.length = 0;
      controller.abort();
      finish();
      return Promise.resolve({ done: true, value: undefined });
    },
  };
}

function createExecutor(session, config) {
  const state = { messages: [] };
  return {
    appendMessages(messages) {
      const list = Array.isArray(messages) ? messages : messages == null ? [] : [messages];
      state.messages.push(...list);
      return this;
    },
    getMessages() {
      return [...state.messages];
    },
    getState() {
      return [...state.messages];
    },
    clearMessages() {
      state.messages = [];
    },
    stream(ctx, invocationId, tools, requestOptions) {
      const controller = new AbortController();
      const fullStream = liveParts(controller);
      const signals = [...new Set([ctx?.abortSignal, ctx?.signal, requestOptions?.abortSignal, requestOptions?.signal])]
        .filter(signal => signal && typeof signal.addEventListener === "function");
      const onAbort = () => controller.abort();
      for (const signal of signals) {
        signal.addEventListener("abort", onAbort, { once: true });
        if (signal.aborted) controller.abort();
      }
      if (typeof session.onRequestId === "function") {
        try {
          session.onRequestId(invocationId);
        } catch {
          /* ignore */
        }
      }
      const processing = configContext.run(config, async () => {
        const model = mapModelId(session.requestedModel);
        return runStream({
          model,
          messages: [...state.messages],
          tools,
          invocationId,
          config,
          signal: controller.signal,
          onPart: part => fullStream.push(part),
        });
      }).catch(() => errorResult(session.getModelId(), invocationId, new Error("provider request preparation failed")))
        .then(result => {
          if (result.response.finishReason === "error") {
            for (const part of result.parts) fullStream.push(part);
          }
          fullStream.finish();
          for (const signal of signals) signal.removeEventListener("abort", onAbort);
          return result;
        });

      return {
        fullStream,
        response: processing.then((r) => r.response),
        usage: processing.then((r) => r.usage),
        extendedUsage: processing.then((r) => r.extendedUsage),
        providerMetadata: processing.then((r) => r.providerMetadata),
        invocationId: processing.then((r) => r.invocationId ?? invocationId),
      };
    },
  };
}

function createXaiPromptSession(options) {
  const opts = options || {};
  const config = loadConfig(opts.envFile);
  return configContext.run(config, () => {
  const requestedModel = opts.requestedModel;
  const model = mapModelId(requestedModel);
  console.error(
    `[ungrok] native session provider=${config.UNGROK_PROVIDER} model=${model}`
  );
  const session = {
    requestedModel,
    onRequestId: opts.onRequestId,
    sessionOptions: opts.sessionOptions,
    getModelId() {
      return config.UNGROK_MODEL || config.UNGROK_PROVIDER + "-default";
    },
    getExecutor(initialMessages) {
      const ex = createExecutor(session, config);
      if (initialMessages) ex.appendMessages(initialMessages);
      return ex;
    },
  };
  return session;
  });
}

module.exports = {
  createXaiPromptSession,
  convertMessages,
  normalizeToolParameters,
  mapModelId,
  trimConvertedMessages,
  prepareInlineImages,
};
