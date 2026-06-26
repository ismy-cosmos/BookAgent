#!/usr/bin/env python3
"""Quick viewer: python view_result.py cs-01 [--parser unstructured|marker|both]"""
import argparse
import json
import textwrap
from pathlib import Path

RESULTS = Path(__file__).parent.parent / "results"
PAGES_CFG = Path(__file__).parent / "pages.json"
WIDTH = 100


def hr(char="─"):
    print(char * WIDTH)


def show_unstructured(page_id: str):
    p = RESULTS / "unstructured" / f"{page_id}.json"
    d = json.loads(p.read_text())
    print(f"  elapsed: {d['elapsed_sec']}s   chars: {d['char_count']}")
    hr("·")
    for e in d["elements"]:
        tag = f"[{e['type']}]"
        body = e["content"].replace("\n", " ").strip()
        wrapped = textwrap.fill(body, width=WIDTH - 14, subsequent_indent=" " * 14)
        print(f"  {tag:<12}{wrapped}")
    hr("·")


def show_marker(page_id: str):
    p = RESULTS / "marker" / f"{page_id}.json"
    d = json.loads(p.read_text())
    print(f"  elapsed: {d['elapsed_sec']}s   chars: {d['char_count']}")
    hr("·")
    content = d["elements"][0]["content"] if d["elements"] else "(empty)"
    # print line by line, wrapping long lines
    for line in content.split("\n"):
        if len(line) <= WIDTH:
            print(line)
        else:
            print(textwrap.fill(line, width=WIDTH))
    hr("·")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("page_id", help="e.g. cs-01")
    ap.add_argument("--parser", choices=["unstructured", "marker", "both"], default="both")
    args = ap.parse_args()

    pages = {p["id"]: p for p in json.loads(PAGES_CFG.read_text())}
    meta = pages.get(args.page_id)
    if not meta:
        print(f"Unknown id: {args.page_id}. Valid: {list(pages)}")
        return

    hr("═")
    print(f"  {args.page_id}  |  {meta['element_type']}  |  {meta['note']}")
    print(f"  source: {meta['source']}  page {meta['page']}")
    hr("═")

    if args.parser in ("unstructured", "both"):
        print("\n▶ UNSTRUCTURED")
        show_unstructured(args.page_id)

    if args.parser in ("marker", "both"):
        print("\n▶ MARKER")
        show_marker(args.page_id)


if __name__ == "__main__":
    main()
