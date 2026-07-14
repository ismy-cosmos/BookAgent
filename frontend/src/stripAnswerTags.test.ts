import { describe, expect, it } from "vitest";
import { stripAnswerTags } from "./stripAnswerTags";

describe("stripAnswerTags", () => {
  it("剪掉未找到参考资料标记", () => {
    expect(stripAnswerTags("答案正文\n[未找到参考资料]")).toBe("答案正文");
  });

  it("剪掉引用来源标记", () => {
    expect(stripAnswerTags("答案正文\n[引用来源：f.pdf p.1]")).toBe("答案正文");
  });

  it("剪掉引用来源+已使用计算工具两行", () => {
    expect(stripAnswerTags("答案正文\n[引用来源：f.pdf p.1]\n[已使用计算工具]")).toBe("答案正文");
  });

  it("正文本身不含任何标记时原样返回", () => {
    expect(stripAnswerTags("普通回答，没有任何标记")).toBe("普通回答，没有任何标记");
  });

  it("正文中间提到方括号内容不受影响，只剪尾部", () => {
    expect(stripAnswerTags("正文提到了[某个引用]这个词\n[未找到参考资料]"))
      .toBe("正文提到了[某个引用]这个词");
  });
});
