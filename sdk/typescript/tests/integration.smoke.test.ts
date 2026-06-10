import { describe, expect, it } from "vitest";
import { AiceryClient } from "../src/client.js";

const baseUrl = process.env.AICERY_RUNTIME_URL ?? "http://localhost:8000";

async function apiHealthy(): Promise<boolean> {
  try {
    const res = await fetch(`${baseUrl}/health`);
    return res.ok;
  } catch {
    return false;
  }
}

describe("integration smoke", () => {
  it("createRun and getRun against live API", async () => {
    if (!(await apiHealthy())) {
      throw new Error(`API not reachable at ${baseUrl}`);
    }

    const client = new AiceryClient({
      baseUrl,
      apiKey: process.env.API_KEY ?? process.env.AICERY_API_KEY ?? "dev",
    });

    const run = await client.createRun({
      input: "TypeScript SDK smoke test",
      agentId: "research",
      execute: false,
    });
    expect(run.id).toBeTruthy();
    expect(run.agent_id).toBe("research");

    const fetched = await client.getRun(run.id);
    expect(fetched.id).toBe(run.id);
  }, 60_000);
});
