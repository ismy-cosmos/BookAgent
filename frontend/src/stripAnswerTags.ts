const NO_CITATION_TAG = "[未找到参考资料]";
const USED_CALCULATE_TAG = "[已使用计算工具]";
const CITATION_TAG_PREFIX = "[引用来源：";

// 跟后端 pipeline/agent/client.py 的 _strip_known_tags 对等：只负责把已知
// 标记行从展示文本尾部剪掉，不承担任何判断真假的职责——UI 状态（引用/
// 计算工具用没用）一律读结构化字段（AskResponse/ChatTurnRecord 的
// used_calculate/attempted_retrieve），不从这份裁剪结果反推。
export function stripAnswerTags(answer: string): string {
  const lines = answer.split("\n");
  while (
    lines.length > 0 &&
    (lines[lines.length - 1] === NO_CITATION_TAG ||
      lines[lines.length - 1] === USED_CALCULATE_TAG ||
      lines[lines.length - 1].startsWith(CITATION_TAG_PREFIX))
  ) {
    lines.pop();
  }
  return lines.join("\n");
}
