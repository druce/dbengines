#!/usr/bin/env python3
"""Unwrap hard-wrapped markdown: join continuation lines into one logical line per
paragraph / list item / blockquote. GitHub treats single newlines inside a paragraph as
soft, but Obsidian renders them as real line breaks — so wrapped source looks broken there.

Leaves untouched: YAML frontmatter, fenced and indented code blocks, tables, headings,
horizontal rules, HTML blocks, and explicit hard breaks (trailing two spaces or <br>).
Also normalizes CRLF/CR to LF and strips trailing whitespace.

Usage:  python3 tools/unwrap_markdown.py [--dry-run] [file.md ...]
With no files, processes every .md in the repo root, engines/ and concepts/.
--dry-run prints a unified diff instead of rewriting. Exit code 0 always on success.
"""
import difflib, glob, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FENCE = re.compile(r"^\s*(```|~~~)")
HEADING = re.compile(r"^\s{0,3}#{1,6}\s")
LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d{1,9}[.)])\s")
TABLE_ROW = re.compile(r"^\s*\|")
HRULE = re.compile(r"^\s{0,3}([-*_])(\s*\1){2,}\s*$")
QUOTE = re.compile(r"^\s{0,3}>\s?")
HTML_BLOCK = re.compile(r"^\s*<")
INDENTED_CODE = re.compile(r"^(?: {4,}|\t)")


def hard_break(line):
    return line.endswith("  ") or line.rstrip().endswith(("<br>", "<br/>", "<br />"))


def clean(line):
    # strip trailing whitespace but preserve an intentional two-space hard break
    return line.rstrip() + "  " if hard_break(line) and line.strip() else line.rstrip()


def unwrap(text):
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out = []
    in_front = in_fence = in_code = False
    prev = None  # None (block boundary) | "text" (joinable paragraph/list) | "quote"
    for i, line in enumerate(lines):
        if i == 0 and line.strip() == "---":
            in_front = True
            out.append(line)
            continue
        if in_front:
            out.append(line)
            if line.strip() in ("---", "..."):
                in_front = False
            continue
        if FENCE.match(line):
            in_fence = not in_fence
            out.append(line)
            prev = None
            continue
        if in_fence:
            out.append(line)
            continue
        if not line.strip():
            out.append("")
            prev = None
            in_code = False
            continue
        # indented code block: starts at a 4-space/tab indent after a block boundary
        if in_code or (prev is None and INDENTED_CODE.match(line)):
            in_code = True
            out.append(line)
            prev = None
            continue
        if HRULE.match(line) or HEADING.match(line) or TABLE_ROW.match(line) or HTML_BLOCK.match(line):
            out.append(clean(line))
            prev = None
            continue
        if QUOTE.match(line):
            body = QUOTE.sub("", line, count=1)
            if prev == "quote" and body.strip() and not hard_break(out[-1]):
                out[-1] = out[-1].rstrip() + " " + body.strip()
            else:
                out.append(clean(line))
            prev = "quote" if body.strip() else None
            continue
        if LIST_ITEM.match(line):
            out.append(clean(line))
            prev = "text"
            continue
        # plain text: continuation of the previous paragraph/list/quote line, or new paragraph
        if prev in ("text", "quote") and not hard_break(out[-1]):
            out[-1] = out[-1].rstrip() + " " + line.strip()
        else:
            out.append(clean(line))
            prev = "text"
    return "\n".join(out)


def main():
    argv = sys.argv[1:]
    dry = "--dry-run" in argv
    files = [a for a in argv if a != "--dry-run"]
    if not files:
        files = sorted(glob.glob(os.path.join(ROOT, "*.md"))
                       + glob.glob(os.path.join(ROOT, "engines", "*.md"))
                       + glob.glob(os.path.join(ROOT, "concepts", "*.md")))
    changed = 0
    for fp in files:
        old = open(fp, encoding="utf-8").read()
        new = unwrap(old)
        if new == old:
            continue
        changed += 1
        rel = os.path.relpath(fp, ROOT)
        joined = len(old.split("\n")) - len(new.split("\n"))
        if dry:
            sys.stdout.writelines(difflib.unified_diff(
                old.splitlines(keepends=True), new.splitlines(keepends=True),
                fromfile=rel, tofile=rel + " (unwrapped)"))
        else:
            open(fp, "w", encoding="utf-8").write(new)
            print(f"unwrapped {rel}: {joined} line break(s) removed")
    if not changed:
        print("OK: nothing to unwrap.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
