import type { ReactNode } from "react";

// chunk 原文来自 PDF→markdown 解析（marker），**bold** 这类语法会原样
// 存进 chunk 内容——embedding/喂给 LLM 那份不动（markdown 强调对模型
// 理解重点可能有帮助，不值得为了展示层去改解析管线、牵动已有语料），
// 只在展示给人看时把它渲成真正的加粗，而不是让用户看见一堆星号。
// 目前只处理观察到的这一种语法（**bold**），没有引入完整 markdown 解析器。
export function renderInlineMarkdown(text: string): ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) =>
    part.startsWith("**") && part.endsWith("**") && part.length > 4 ? (
      <strong key={i}>{part.slice(2, -2)}</strong>
    ) : (
      part
    ),
  );
}
