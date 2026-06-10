import type { SseEvent } from "./types.js";

/**
 * Parse SSE lines from a ReadableStream (same event:/data: format as Python SDK).
 */
export async function* parseSseStream(
  body: ReadableStream<Uint8Array> | null,
): AsyncIterable<SseEvent> {
  if (!body) {
    return;
  }
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let eventName: string | null = null;
  const dataLines: string[] = [];

  const flush = (): SseEvent | null => {
    if (!eventName || dataLines.length === 0) {
      return null;
    }
    const raw = dataLines.join("\n");
    dataLines.length = 0;
    const name = eventName;
    eventName = null;
    return {
      event: name,
      data: JSON.parse(raw) as Record<string, unknown>,
    };
  };

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";

      for (const rawLine of lines) {
        const line = rawLine.replace(/\r$/, "").trimEnd();
        if (!line) {
          const ev = flush();
          if (ev) {
            yield ev;
          }
          continue;
        }
        if (line.startsWith("event:")) {
          eventName = line.slice(6).trim();
        }
         else if (line.startsWith("data:")) {
          dataLines.push(line.slice(5).trim());
        }
      }
    }
    if (buffer.trim()) {
      const line = buffer.replace(/\r$/, "").trimEnd();
      if (line.startsWith("event:")) {
        eventName = line.slice(6).trim();
      } else if (line.startsWith("data:")) {
        dataLines.push(line.slice(5).trim());
      }
    }
    const ev = flush();
    if (ev) {
      yield ev;
    }
  } finally {
    reader.releaseLock();
  }
}
