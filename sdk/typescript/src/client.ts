import { parseSseStream } from "./sse.js";
import type {
  AiceryClientOptions,
  CreateRunOptions,
  Run,
  SseEvent,
} from "./types.js";

function mapRun(body: Record<string, unknown>): Run {
  return {
    id: String(body.id),
    status: String(body.status),
    agent_id: String(body.agent_id),
    input_text: (body.input_text as string | null | undefined) ?? null,
    output_text: (body.output_text as string | null | undefined) ?? null,
    error_code: (body.error_code as string | null | undefined) ?? null,
    error_message: (body.error_message as string | null | undefined) ?? null,
    conversation_id: (body.conversation_id as string | null | undefined) ?? null,
    created_at: body.created_at as string | undefined,
    updated_at: body.updated_at as string | undefined,
  };
}

export class AiceryClient {
  private readonly baseUrl: string;
  private readonly apiKey: string;

  constructor(options: AiceryClientOptions) {
    this.baseUrl = options.baseUrl.replace(/\/$/, "");
    this.apiKey = options.apiKey;
  }

  static fromEnv(): AiceryClient {
    const apiKey =
      process.env.API_KEY ?? process.env.AICERY_API_KEY ?? "dev";
    const baseUrl =
      process.env.AICERY_RUNTIME_URL ?? "http://localhost:8000";
    return new AiceryClient({ baseUrl, apiKey });
  }

  private headers(extra?: Record<string, string>): Record<string, string> {
    return {
      "X-API-Key": this.apiKey,
      ...extra,
    };
  }

  async createRun(options: CreateRunOptions): Promise<Run> {
    const payload: Record<string, unknown> = {
      input: options.input,
      execute: options.execute ?? true,
    };
    if (options.agentId) {
      payload.agent_id = options.agentId;
    }
    if (options.pipeline) {
      payload.pipeline = options.pipeline;
    }
    if (options.workspaceId) {
      payload.workspace_id = options.workspaceId;
    }
    if (options.conversationId) {
      payload.conversation_id = options.conversationId;
    }
    if (options.providerPolicy) {
      payload.provider_policy = options.providerPolicy;
    }

    const response = await fetch(`${this.baseUrl}/v1/runs`, {
      method: "POST",
      headers: {
        ...this.headers(),
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      const text = await response.text();
      throw new Error(`createRun failed ${response.status}: ${text}`);
    }
    const body = (await response.json()) as Record<string, unknown>;
    return mapRun(body);
  }

  async getRun(runId: string): Promise<Run> {
    const response = await fetch(`${this.baseUrl}/v1/runs/${runId}`, {
      headers: this.headers(),
    });
    if (!response.ok) {
      const text = await response.text();
      throw new Error(`getRun failed ${response.status}: ${text}`);
    }
    const body = (await response.json()) as Record<string, unknown>;
    return mapRun(body);
  }

  async *streamRun(runId: string): AsyncIterable<SseEvent> {
    const response = await fetch(`${this.baseUrl}/v1/runs/${runId}/stream`, {
      headers: this.headers({ Accept: "text/event-stream" }),
    });
    if (!response.ok) {
      const text = await response.text();
      throw new Error(`streamRun failed ${response.status}: ${text}`);
    }
    yield* parseSseStream(response.body);
  }
}
