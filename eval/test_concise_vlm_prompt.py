"""Compare original vs concise VLM description prompt on real images:
latency, token count, and description completeness (eyeball).

Usage: python eval/test_concise_vlm_prompt.py
"""
from __future__ import annotations
import base64
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from openai import OpenAI
from pipeline.parse.image import describe_image, _resize_to_limit, _load_as_png_bytes

_IMAGES = [
    "eval/testset/cs/raw/pic/cs_p1.png",
    "eval/testset/cs/raw/pic/cs_p2.png",
    "eval/testset/cs/raw/pic/cs_p3.png",
]

_ORIGINAL_PROMPT = (
    "Describe all content visible in this image in detail. "
    "Include any text, formulas, diagrams, tables, and figures. "
    "Respond in the same language as the text in the image."
)

_CONCISE_PROMPT = (
    "Briefly describe the key content visible in this image (text, formulas, "
    "diagrams, tables, figures). Cover every distinct element without "
    "omission, but do not elaborate beyond what's necessary to convey it — "
    "no decorative or illustrative detail. Let the length follow naturally "
    "from how much content the image actually contains. "
    "Respond in the same language as the text in the image."
)


def _run(client, model, img_path, prompt, label):
    raw = _load_as_png_bytes(img_path)
    resized = _resize_to_limit(raw)
    b64 = base64.b64encode(resized).decode()

    usage_holder = {}
    t0 = time.perf_counter()
    # temperature=0：描述任务要的是忠实提取，不是创意多样性；qwen3:q4km
    # 这个模型tag的Modelfile默认温度=1是给对话/工具调用鲁棒性测试用的，
    # 用同一个值跑图片描述会引入不必要的run间波动。这里按次请求覆盖，
    # 不改共享Modelfile，不影响对话链路。
    desc = describe_image(client, model, b64, prompt=prompt,
                           options={"temperature": 0},
                           on_usage=lambda u: usage_holder.update(
                               prompt_tokens=u.prompt_tokens,
                               completion_tokens=u.completion_tokens,
                               total_tokens=u.total_tokens))
    latency = time.perf_counter() - t0
    print(f"[{label}] {Path(img_path).name}  latency={latency:.1f}s  "
          f"completion_tokens={usage_holder.get('completion_tokens')}  "
          f"total_tokens={usage_holder.get('total_tokens')}")
    print(f"  描述: {desc}")
    print()
    return latency, usage_holder.get("completion_tokens", 0)


def main():
    client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
    model = "qwen3:q4km"

    orig_lat, orig_tok = [], []
    concise_lat, concise_tok = [], []

    for img in _IMAGES:
        l, t = _run(client, model, img, _ORIGINAL_PROMPT, "原prompt")
        orig_lat.append(l); orig_tok.append(t)
    for img in _IMAGES:
        l, t = _run(client, model, img, _CONCISE_PROMPT, "简洁prompt")
        concise_lat.append(l); concise_tok.append(t)

    print("── 对比汇总 ────────────────────")
    print(f"原prompt:   avg latency={sum(orig_lat)/len(orig_lat):.1f}s  avg completion_tokens={sum(orig_tok)/len(orig_tok):.0f}")
    print(f"简洁prompt: avg latency={sum(concise_lat)/len(concise_lat):.1f}s  avg completion_tokens={sum(concise_tok)/len(concise_tok):.0f}")
    speedup = (1 - sum(concise_lat)/len(concise_lat) / (sum(orig_lat)/len(orig_lat))) * 100
    print(f"延迟降低: {speedup:.0f}%")


if __name__ == "__main__":
    main()
