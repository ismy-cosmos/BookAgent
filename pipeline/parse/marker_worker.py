#!/usr/bin/env python3
"""Marker PDF parsing worker — runs in a subprocess for pdfium crash isolation.

Usage:
    python -m pipeline.parse.marker_worker

Protocol (NDJSON, one JSON object per line on stdin/stdout):
    ← {"ready": true, "page_sep": "<resolved separator>"}

    → {"job": <int>, "pdf": "<path>"}
    ← {"job": <int>, "ok": true, "elements": [...], "section_count": <int>}
    ← {"job": <int>, "ok": false, "error": "<traceback summary>"}

    → {"cmd": "shutdown"}  (or stdin EOF)
    (process exits 0)

All library output (model loading, marker/pdftext/transformers logging)
is redirected to stderr so stdout stays a clean NDJSON stream.
"""
from __future__ import annotations
import contextlib
import json
import sys
import traceback


def main() -> None:
    # ── Redirect ALL library output during startup ──────────────────
    with contextlib.redirect_stdout(sys.stderr):
        from marker.converters.pdf import PdfConverter
        from marker.models import create_model_dict
        from pipeline.parse.marker import _PAGE_SEP, _rendered_to_elements
        from pipeline.parse.parse_cache import _encode_element

        converter = PdfConverter(
            artifact_dict=create_model_dict(),
            config={
                "paginate_output": True,
                "page_separator": _PAGE_SEP,
                "pdftext_workers": 1,
            },
        )
        # Resolve actual separator, matching MarkerParser._get_converter
        resolved_renderer = converter.resolve_dependencies(converter.renderer)
        page_sep = resolved_renderer.page_separator

    # ── Ready handshake ─────────────────────────────────────────────
    print(json.dumps({"ready": True, "page_sep": page_sep}), flush=True)

    # ── Main loop ───────────────────────────────────────────────────
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue

        if msg.get("cmd") == "shutdown":
            break

        job = msg.get("job")
        pdf_path = msg.get("pdf")
        if job is None or pdf_path is None:
            continue

        try:
            with contextlib.redirect_stdout(sys.stderr):
                rendered = converter(pdf_path)
            elements = _rendered_to_elements(rendered, page_sep=page_sep)
            section_count = len(rendered.markdown.split(page_sep)) - 1 if getattr(rendered, 'markdown', '') else 0
            encoded = [_encode_element(e) for e in elements]
            print(json.dumps({
                "job": job, "ok": True,
                "elements": encoded,
                "section_count": section_count,
            }), flush=True)
        except Exception as exc:
            print(json.dumps({
                "job": job,
                "ok": False,
                "error": f"{type(exc).__name__}: {exc}",
            }), flush=True)
            traceback.print_exc(file=sys.stderr)


if __name__ == "__main__":
    main()
