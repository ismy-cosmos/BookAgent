import { WebviewWindow } from "@tauri-apps/api/webviewWindow";

// Tauri 窗口 label 只允许 a-zA-Z0-9-/:_，但 book_id 用户自定义、不限格式
// （可能含中文/空格/任意字符，见 docs/book-management.md），所以不能直接拼进
// label，要先编码成安全字符集——用 base64url（把标准 base64 的 +/= 换成 Tauri
// 允许的 -_，末尾不留 padding）。
function encodeToSafeLabel(value: string): string {
  const base64 = btoa(unescape(encodeURIComponent(value)));
  return base64.replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

export function toWindowLabel(kind: "import" | "chat", bookId: string): string {
  return `${kind}-${encodeToSafeLabel(bookId)}`;
}

export async function openOrFocusWindow(
  kind: "import" | "chat",
  bookId: string,
  title: string,
): Promise<void> {
  const label = toWindowLabel(kind, bookId);
  const existing = await WebviewWindow.getByLabel(label);
  if (existing) {
    await existing.setFocus();
    return;
  }
  new WebviewWindow(label, {
    url: `index.html?view=${kind}&book=${encodeURIComponent(bookId)}`,
    title,
  });
}

const WINDOW_KINDS = ["import", "chat"] as const;

// 书被删掉之后，它对应的导入/对话窗口如果还开着，会一直留着删除前的
// 内存状态——同名书重新建出来时，openOrFocusWindow 按 label 找到的是
// 这个没被销毁的旧窗口，直接聚焦它、不会重新拉取数据，旧状态就跟着
// "复活"了。删除时把窗口一起关掉，避免这个问题。
export async function closeBookWindows(bookId: string): Promise<void> {
  for (const kind of WINDOW_KINDS) {
    const w = await WebviewWindow.getByLabel(toWindowLabel(kind, bookId));
    if (w) await w.destroy();
  }
}

// 改名会改变 book_id，而窗口 label 是按旧 book_id 算出来的、窗口内部
// React 状态也认定 bookId 不会变——与其在改名后想办法把窗口迁移到新
// label／刷新内部状态，不如改名前先检查，窗口开着就不允许改。
export async function hasOpenWindows(bookId: string): Promise<boolean> {
  for (const kind of WINDOW_KINDS) {
    if (await WebviewWindow.getByLabel(toWindowLabel(kind, bookId))) return true;
  }
  return false;
}
