export interface Status {
  busy: boolean;
  reason: "idle" | "ingesting";
  book_id: string | null;
  pause_requested: boolean;
}

export interface ImportProgress {
  stage: "parsing" | "vlm" | "storing";
  current_file: number | null;
  total_files: number | null;
  current_image: number | null;
  total_images: number | null;
}

export interface ImportFailure {
  file: string;
  error_type: string;
  error_message: string;
  timestamp: string;
}

// 任务正常结束是完整摘要；处理器整体异常时只有 book_id + error 两个键
export interface LastResult {
  book_id: string;
  total_chunks?: number;
  failures?: ImportFailure[];
  not_attempted?: string[];
  aborted_early?: boolean;
  error?: string;
}

// GET /progress 的响应 = Status 全部字段 + progress + last_result
export interface ProgressResponse extends Status {
  progress: ImportProgress | null;
  last_result: LastResult | null;
}

export interface Citation {
  chunk_id: string;
  source_file: string;
  element_type: string;
  citation: string;
  score: number | null;
}

export interface AskResponse {
  answer: string;
  citations: Citation[];
  triggered_tool: string | null;
  total_tokens: number;
  latency_s: number;
}

export interface ConversationSummary {
  id: string;
  title: string;
  updated_at: string;
}

export interface ChatTurnRecord {
  question: string;
  answer: string;
  citations: Citation[];
}

export interface ConversationRecord {
  id: string;
  book_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  turns: ChatTurnRecord[];
}

export interface ChunkDetail {
  chunk_id: string;
  content: string;
  source_file: string;
  element_type: string;
  page_start: number | null;
  page_end: number | null;
  start_sec: number | null;
  end_sec: number | null;
  low_confidence: boolean;
}
