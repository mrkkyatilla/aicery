import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { AiceryClient } from "../src/client.js";

function sseBody(events: Array<{ event: string; data: Record<string, unknown> }>): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  const chunks = events
    .map(
      (e) =>
        `event: ${e.event}\ndata: ${JSON.stringify(e.data)}\n\n`,
    )
    .join("");
  return new ReadableStream({
    start(controller) {
      controller.enqueue(encoder.encode(chunks));
      controller.close();
    },
  });
}

describe("AiceryClient", () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    fetchMock.mockReset();
  });

  it("createRun parses 201 response", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          id: "run-1",
          status: "running",
          agent_id: "research",
          input_text: "hello",
        }),
        { status: 201, headers: { "Content-Type": "application/json" } },
      ),
    );

    const client = new AiceryClient({
      baseUrl: "http://localhost:8000",
      apiKey: "dev",
    });
    const run = await client.createRun({
      input: "hello",
      agentId: "research",
      execute: false,
    });

    expect(run.id).toBe("run-1");
    expect(run.status).toBe("running");
    expect(run.agent_id).toBe("research");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/v1/runs",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({ "X-API-Key": "dev" }),
      }),
    );
  });

  it("getRun maps response fields", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          id: "run-2",
          status: "completed",
          agent_id: "research",
          output_text: "done",
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    const client = new AiceryClient({
      baseUrl: "http://localhost:8000/",
      apiKey: "key",
    });
    const run = await client.getRun("run-2");
    expect(run.status).toBe("completed");
    expect(run.output_text).toBe("done");
  });

  it("streamRun yields parsed SSE events", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        sseBody([
          { event: "token", data: { text: "hi" } },
          { event: "done", data: { status: "completed" } },
        ]),
        { status: 200, headers: { "Content-Type": "text/event-stream" } },
      ),
    );

    const client = new AiceryClient({
      baseUrl: "http://localhost:8000",
      apiKey: "dev",
    });
    const events = [];
    for await (const ev of client.streamRun("run-3")) {
      events.push(ev);
    }
    expect(events).toHaveLength(2);
    expect(events[0]?.event).toBe("token");
    expect(events[1]?.event).toBe("done");
  });
});
