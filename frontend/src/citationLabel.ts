import type { Citation } from "./api/types";

export type CitationLabelState =
  | { kind: "pills"; citations: Citation[] }
  | { kind: "text"; text: string };

// citations 非空：优先展示可点击的引用胶囊。citations 为空时，
// attemptedRetrieve 用来区分"真查了没有"和"这轮没重新查"两种情况——
// 不能都显示同一句话，"这轮没查"（比如追问/复述性问题，模型判断已经
// 查过、基于上文回答）如果也显示"未找到参考资料"，会误导用户以为
// 书里没有这部分内容。
export function citationLabel(
  citations: Citation[],
  attemptedRetrieve: boolean,
): CitationLabelState {
  if (citations.length > 0) return { kind: "pills", citations };
  if (attemptedRetrieve) return { kind: "text", text: "书中未检索到相关内容" };
  return { kind: "text", text: "本轮未重新检索原文" };
}
