import { afterEach, describe, expect, it, vi } from "vitest";
import {
  addStagedFile,
  ask,
  getChunk,
  getProgress,
  getStatus,
  listBooks,
  removeStagedFile,
  submitImport,
} from "./client";

afterEach(() => {
  vi.unstubAllGlobals();
});

function stubFetchOnce(status: number, body: unknown) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: status >= 200 && status < 300,
      status,
      json: () => Promise.resolve(body),
    }),
  );
}

describe("getStatus", () => {
  it("returns parsed status on success", async () => {
    stubFetchOnce(200, { busy: false, reason: "idle", book_id: null, pause_requested: false });
    const result = await getStatus();
    expect(result.busy).toBe(false);
  });
});

describe("listBooks", () => {
  it("returns book list", async () => {
    stubFetchOnce(200, { books: ["ostep"] });
    const result = await listBooks();
    expect(result.books).toEqual(["ostep"]);
  });
});

describe("error handling", () => {
  it("throws ApiError with detail message on non-2xx response", async () => {
    stubFetchOnce(404, { detail: "book_id 'ostep' 不存在" });
    await expect(listBooks()).rejects.toMatchObject({
      status: 404,
      message: "book_id 'ostep' 不存在",
    });
  });
});

describe("ask", () => {
  it("posts question as JSON body", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve({
        answer: "答案", citations: [], triggered_tool: null,
        total_tokens: 1, latency_s: 0.1,
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await ask("ostep", "conv1", "fork 是什么？");

    const [, init] = fetchMock.mock.calls[0];
    expect(JSON.parse(init.body)).toEqual({ question: "fork 是什么？" });
  });
});

describe("getChunk", () => {
  it("returns the chunk's content and location", async () => {
    stubFetchOnce(200, {
      chunk_id: "c1", content: "fork() 相关内容", source_file: "ch3.pdf",
      element_type: "text", page_start: 42, page_end: 42,
      start_sec: null, end_sec: null, low_confidence: false,
    });
    const result = await getChunk("ostep", "c1");
    expect(result.content).toBe("fork() 相关内容");
    expect(result.page_start).toBe(42);
  });
});

describe("staged files", () => {
  it("posts file_path when adding a staged file", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ files: ["/data/ch01.pdf"] }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await addStagedFile("ostep", "/data/ch01.pdf");

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toContain("/books/ostep/staged-files");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({ file_path: "/data/ch01.pdf" });
  });

  it("removes a staged file via query param", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ files: [] }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await removeStagedFile("ostep", "/data/ch01.pdf");

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toContain("/books/ostep/staged-files?file_path=");
    expect(url).toContain(encodeURIComponent("/data/ch01.pdf"));
    expect(init.method).toBe("DELETE");
  });
});

describe("submitImport", () => {
  it("posts book_id and returns the task id", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 202,
      json: () => Promise.resolve({ task_id: "task-123", file_count: 2 }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await submitImport("ostep");

    expect(result.task_id).toBe("task-123");
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toContain("/books");
    expect(JSON.parse(init.body)).toEqual({ book_id: "ostep" });
  });
});

describe("getProgress", () => {
  it("returns merged status and progress fields", async () => {
    stubFetchOnce(200, {
      busy: true, reason: "ingesting", book_id: "ostep", pause_requested: false,
      progress: { stage: "vlm", current_file: 3, total_files: 3,
                  current_image: 7, total_images: 40 },
      last_result: null,
    });
    const result = await getProgress();
    expect(result.busy).toBe(true);
    expect(result.progress?.stage).toBe("vlm");
    expect(result.progress?.current_image).toBe(7);
  });
});
