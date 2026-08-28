export interface Status {
  busy: boolean;
  reason: "idle" | "ingesting" | "answering";
  book_id: string | null;
  pause_requested: boolean;
}

export interface ImportProgress {
  stage: "parsing" | "vlm" | "storing";
  current_file: number | null;
  total_files: number | null;
  current_image: number | null;
  total_images: number | null;
  // 阶段1（解析）才会有值；后端 scripts/ingest.py 的 ProgressUpdate 早就在
  // 传了，前端类型之前漏声明。可选（而非必填）是因为仓库里已有测试用例
  // 直接写字面量对象、没带这个字段，加成必填会让那些测试编译不过。
  current_filename?: string | null;
}

export interface ImportFailure {
  file: string;
  error_type: string;
  error_message: string;
  timestamp: string;
}

// 任务正常结束是完整摘要；处理器整体异常时只有 book_id + error 两个键。
// task_id 由 ImportQueue 在存档时混入（不是 processor 返回值自带的），
// 供前端区分"内容凑巧相同的两次结果"——暂停发生在文件还没开始处理之前
// 时，重新提交同一批文件产生的结果在内容上会一模一样，不能拿内容本身
// 去重。可选是因为仓库里已有很多测试用例直接写字面量、没带这个字段。
export interface LastResult {
  book_id: string;
  task_id?: string;
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
  used_calculate: boolean;
  attempted_retrieve: boolean;
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
  // 老对话记录（这两个字段上线前存的）可能没有——历史数据不做迁移，
  // 读取时按 false 兜底展示，不强制假设一定存在。
  used_calculate?: boolean;
  attempted_retrieve?: boolean;
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
