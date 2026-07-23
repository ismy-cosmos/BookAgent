#!/usr/bin/env python3
"""WhisperX transcription wrapper — must run inside whisperx.venv.

Usage:
    whisperx.venv/bin/python pipeline/parse/whisperx_transcribe.py <audio_path> [--model MODEL] [--language LANG] [--diarize]
"""
from __future__ import annotations
import argparse
import contextlib
import json
import logging
import sys

# whisperx 的具名 logger 会给 sys.stdout 直接加 StreamHandler，basicConfig 管不到，
# 必须靠下面 main() 里的 redirect_stdout 整体重定向来防污染（不是靠这一行）。
logging.basicConfig(stream=sys.stderr, level=logging.WARNING)


def transcribe(audio_path: str, model_name: str, language: str | None, diarize: bool = False) -> dict:
    import torch
    import whisperx

    device = "cuda" if torch.cuda.is_available() else "cpu"
    compute_type = "float16" if device == "cuda" else "int8"

    model = whisperx.load_model(model_name, device=device, compute_type=compute_type)
    audio = whisperx.load_audio(audio_path)
    result = model.transcribe(audio, batch_size=16, language=language)

    align_model, align_metadata = whisperx.load_align_model(
        language_code=result["language"], device=device
    )
    aligned = whisperx.align(result["segments"], align_model, align_metadata, audio, device)

    if diarize:
        # 懒加载：只有真正启用diarize才导入，import whisperx.diarize 会连带
        # 加载 pyannote.audio，实测约2秒开销，默认路径不能背这个成本。
        from whisperx.diarize import DiarizationPipeline, assign_word_speakers

        diarize_model = DiarizationPipeline(device=device)
        diarize_df = diarize_model(audio_path)
        aligned = assign_word_speakers(diarize_df, aligned, fill_nearest=True)

    segments = []
    for seg in aligned["segments"]:
        words = [
            {"word": w.get("word", ""), "score": float(w["score"])}
            for w in seg.get("words", [])
            if "score" in w
        ]
        entry = {
            "start": float(seg["start"]),
            "end": float(seg["end"]),
            "text": seg["text"],
            "words": words,
        }
        if diarize:
            entry["speaker"] = seg.get("speaker", "SPEAKER_00")
        segments.append(entry)
    return {"segments": segments}


def main() -> None:
    parser = argparse.ArgumentParser(description="WhisperX transcription wrapper")
    parser.add_argument("audio_path")
    parser.add_argument("--model", default="small")
    parser.add_argument("--language", default=None)
    parser.add_argument("--diarize", action="store_true", default=False)
    args = parser.parse_args()

    try:
        with contextlib.redirect_stdout(sys.stderr):
            result = transcribe(args.audio_path, args.model, args.language, diarize=args.diarize)
        print(json.dumps(result, ensure_ascii=False))
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()