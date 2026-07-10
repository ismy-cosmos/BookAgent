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
