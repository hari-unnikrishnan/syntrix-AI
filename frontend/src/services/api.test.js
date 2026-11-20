import { afterEach, describe, expect, it, vi } from "vitest";

import api, { workspaceApi } from "./api.js";

describe("workspace API client", () => {
  const defaultAdapter = api.defaults.adapter;

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
    api.defaults.adapter = defaultAdapter;
  });

  it("attaches the session token and posts chat messages to Django", async () => {
    const storage = {
      getItem: vi.fn().mockReturnValue("test-token"),
    };
    const adapter = vi.fn(async (config) => ({
      config,
      data: {},
      headers: {},
      status: 201,
      statusText: "Created",
    }));
    vi.stubGlobal("sessionStorage", storage);
    api.defaults.adapter = adapter;

    await workspaceApi.sendMessage("Hello", 42);

    const [request] = adapter.mock.calls[0];
    expect(request.url).toBe("/chat/");
    expect(request.method).toBe("post");
    expect(request.headers.Authorization).toBe("Token test-token");
    expect(JSON.parse(request.data)).toEqual({
      message: "Hello",
      conversation_id: 42,
    });
  });
});
