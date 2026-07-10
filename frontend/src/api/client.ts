import { isTauri } from "@tauri-apps/api/core";
import type {
  AskResponse,
  ChunkDetail,
  ConversationRecord,
  ConversationSummary,
  ProgressResponse,
  Status,
} from "./types";

const BASE_URL = import.meta.env.VITE_BOOKAGENT_API_URL ?? "http://localhost:8420";

// Tauri webview（webkit2gtk 沙箱）不能直连 localhost，得走 @tauri-apps/plugin-http
// 的 fetch（通过 Rust 后端发请求）。浏览器 / jsdom 测试里用原生 fetch。
// isTauri() 是 @tauri-apps/api 的官方运行时检测函数。
async function _fetch(): Promise<typeof fetch> {
  if (isTauri()) {
    const { fetch: tauriFetch } = await import("@tauri-apps/plugin-http");
    return tauriFetch as unknown as typeof fetch;
  }
  return globalThis.fetch.bind(globalThis);
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const f = await _fetch();
  const resp = await f(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({ detail: resp.statusText }));
    throw new ApiError(resp.status, body.detail ?? resp.statusText);
  }
  return resp.json() as Promise<T>;
}

export function getStatus(): Promise<Status> {
  return request<Status>("/status");
}

export function listBooks(): Promise<{ books: string[] }> {
  return request("/books");
}

export function deleteBook(bookId: string): Promise<{ deleted: string }> {
  return request(`/books/${encodeURIComponent(bookId)}`, { method: "DELETE" });
}

export function renameBook(
  bookId: string,
  newBookId: string,
): Promise<{ book_id: string }> {
  return request(`/books/${encodeURIComponent(bookId)}`, {
    method: "PATCH",
    body: JSON.stringify({ new_book_id: newBookId }),
  });
}

export function listFiles(bookId: string): Promise<{ files: string[] }> {
  return request(`/books/${encodeURIComponent(bookId)}/files`);
}

export function deleteFile(
  bookId: string,
  sourceFile: string,
): Promise<{ deleted_file: string; book_id: string }> {
  return request(
    `/books/${encodeURIComponent(bookId)}/files/${encodeURIComponent(sourceFile)}`,
    { method: "DELETE" },
  );
}

export function listConversations(
  bookId: string,
): Promise<{ conversations: ConversationSummary[] }> {
  return request(`/books/${encodeURIComponent(bookId)}/conversations`);
}

export function createConversation(bookId: string): Promise<ConversationRecord> {
  return request(`/books/${encodeURIComponent(bookId)}/conversations`, {
    method: "POST",
  });
}

export function getConversation(
  bookId: string,
  conversationId: string,
): Promise<ConversationRecord> {
  return request(
    `/books/${encodeURIComponent(bookId)}/conversations/${encodeURIComponent(conversationId)}`,
  );
}

export function deleteConversation(
  bookId: string,
  conversationId: string,
): Promise<{ deleted: string }> {
  return request(
    `/books/${encodeURIComponent(bookId)}/conversations/${encodeURIComponent(conversationId)}`,
    { method: "DELETE" },
  );
}

export function ask(
  bookId: string,
  conversationId: string,
  question: string,
): Promise<AskResponse> {
  return request(
    `/books/${encodeURIComponent(bookId)}/conversations/${encodeURIComponent(conversationId)}/ask`,
    { method: "POST", body: JSON.stringify({ question }) },
  );
}

export function getChunk(bookId: string, chunkId: string): Promise<ChunkDetail> {
  return request(`/books/${encodeURIComponent(bookId)}/chunks/${encodeURIComponent(chunkId)}`);
}

export function listStagedFiles(bookId: string): Promise<{ files: string[] }> {
  return request(`/books/${encodeURIComponent(bookId)}/staged-files`);
}

export function addStagedFile(
  bookId: string,
  filePath: string,
): Promise<{ files: string[] }> {
  return request(`/books/${encodeURIComponent(bookId)}/staged-files`, {
    method: "POST",
    body: JSON.stringify({ file_path: filePath }),
  });
}

export function removeStagedFile(
  bookId: string,
  filePath: string,
): Promise<{ files: string[] }> {
  return request(
    `/books/${encodeURIComponent(bookId)}/staged-files?file_path=${encodeURIComponent(filePath)}`,
    { method: "DELETE" },
  );
}

export function submitImport(
  bookId: string,
): Promise<{ task_id: string; file_count: number }> {
  return request("/books", {
    method: "POST",
    body: JSON.stringify({ book_id: bookId }),
  });
}

export function getProgress(): Promise<ProgressResponse> {
  return request<ProgressResponse>("/progress");
}

export function pauseImport(): Promise<Status> {
  return request<Status>("/import/pause", { method: "POST" });
}

export function resumeImport(): Promise<Status> {
  return request<Status>("/import/resume", { method: "POST" });
}

export function cancelImport(taskId: string): Promise<{ cancelled: string }> {
  return request(`/import/${encodeURIComponent(taskId)}/cancel`, { method: "POST" });
}
