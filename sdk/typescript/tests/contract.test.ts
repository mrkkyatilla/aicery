import { describe, expect, it } from "vitest";
import { AiceryClient } from "../src/client.js";

describe("SDK contract", () => {
  it("exposes v1 client methods", () => {
    expect(typeof AiceryClient).toBe("function");
    expect(typeof AiceryClient.fromEnv).toBe("function");
    expect(typeof AiceryClient.prototype.createRun).toBe("function");
    expect(typeof AiceryClient.prototype.getRun).toBe("function");
    expect(typeof AiceryClient.prototype.streamRun).toBe("function");
  });
});
