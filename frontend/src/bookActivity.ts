import type { Status } from "./api/types";

export type BookActivity = "idle" | "ingesting" | "answering";

// 把"这本书当前算不算忙、忙的原因是什么"这个判断收拢成一处——之前
// ImportPanel/BookGrid/GlobalImportCapsule 分别拿 busy/reason/book_id
// 三个原始字段各自拼一遍条件判断，容易漏、容易几处标准悄悄不一致。
export function bookActivity(status: Status | null, bookId: string): BookActivity {
  if (!status || !status.busy || status.book_id !== bookId) return "idle";
  return status.reason as "ingesting" | "answering";
}
