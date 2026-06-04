#!/usr/bin/env python3
"""Check that every relative markdown link to a local .md file resolves to a real file,
and report any leftover Obsidian [[wikilinks]]. Reusable lint for the wiki.

Usage:  python3 tools/check_links.py
Exit code 0 if clean, 1 if any broken links or stray wikilinks are found.
"""
import os, re, sys, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MDLINK = re.compile(r"\[[^\]]*\]\(([^)]+\.md)(?:#[^)]*)?\)")
WIKILINK = re.compile(r"\[\[[^\]]+\]\]")

def main():
    files = (glob.glob(os.path.join(ROOT, "*.md"))
             + glob.glob(os.path.join(ROOT, "engines", "*.md"))
             + glob.glob(os.path.join(ROOT, "concepts", "*.md")))
    broken, wikis = [], []
    for fp in sorted(files):
        # strip fenced code blocks and inline `code` spans (illustrative markup, not real links)
        lines, in_fence = [], False
        for line in open(fp, encoding="utf-8").read().split("\n"):
            if line.lstrip().startswith("```"):
                in_fence = not in_fence; lines.append(""); continue
            if in_fence:
                lines.append(""); continue
            parts = line.split("`")
            lines.append("".join(parts[i] for i in range(0, len(parts), 2)))
        text = "\n".join(lines)
        d = os.path.dirname(fp)
        for m in MDLINK.finditer(text):
            link = m.group(1)
            if link.startswith(("http://", "https://")):
                continue
            if not os.path.exists(os.path.normpath(os.path.join(d, link))):
                broken.append((os.path.relpath(fp, ROOT), link))
        for m in WIKILINK.finditer(text):
            wikis.append((os.path.relpath(fp, ROOT), m.group(0)))
    if broken:
        print(f"BROKEN local .md links ({len(broken)}):")
        for f, l in broken:
            print(f"  {f} -> {l}")
    if wikis:
        print(f"\nLeftover [[wikilinks]] ({len(wikis)}):")
        for f, l in wikis[:50]:
            print(f"  {f}: {l}")
    if not broken and not wikis:
        print("OK: all local .md links resolve; no leftover wikilinks.")
        return 0
    return 1

if __name__ == "__main__":
    sys.exit(main())
