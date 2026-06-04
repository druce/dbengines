#!/usr/bin/env python3
"""Convert Obsidian-style [[wikilinks]] to GitHub-friendly relative markdown links.

Deterministic and idempotent. Builds a slug -> file map from the wiki, then rewrites
[[slug]] and [[slug|display]] to [display-or-slug](relative/path.md). Links with no matching
file degrade to plain text (never a broken link). Fenced code blocks and inline `code` spans
are left untouched so example markup isn't mangled.

CLAUDE.md is intentionally NOT rewritten here (its cross-linking section is maintained by hand).

Usage:  python3 tools/wikilinks_to_md.py [--dry-run]
"""
import os, re, sys, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRY = "--dry-run" in sys.argv

# --- build slug -> path-relative-to-ROOT map (case-insensitive keys) ---
targets = {}
for d in ("engines", "concepts"):
    for fp in glob.glob(os.path.join(ROOT, d, "*.md")):
        slug = os.path.basename(fp)[:-3]
        targets[slug.lower()] = os.path.join(d, slug + ".md")
for root_doc in ("index.md", "decision-guide.md", "log.md", "ranking.md", "CLAUDE.md"):
    if os.path.exists(os.path.join(ROOT, root_doc)):
        targets[root_doc[:-3].lower()] = root_doc

LINK = re.compile(r"\[\[([A-Za-z0-9][A-Za-z0-9\- ]*?)(?:\|([^\]]+))?\]\]")

def convert_text(text, src_dir):
    def repl(m):
        slug = m.group(1).strip()
        disp = (m.group(2) or slug).strip()
        tgt = targets.get(slug.lower())
        if tgt:
            rel = os.path.relpath(os.path.join(ROOT, tgt), os.path.join(ROOT, src_dir))
            return f"[{disp}]({rel})"
        return disp  # dangling -> plain text, never a broken link
    return LINK.sub(repl, text)

def convert_file(fp):
    src_dir = os.path.relpath(os.path.dirname(fp), ROOT)
    out, in_fence, converted = [], False, 0
    for line in open(fp, encoding="utf-8").read().split("\n"):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            out.append(line); continue
        if in_fence:
            out.append(line); continue
        # protect inline code spans: only convert outside backtick segments
        parts = line.split("`")
        for i in range(0, len(parts), 2):
            new = convert_text(parts[i], src_dir)
            converted += len(LINK.findall(parts[i]))
            parts[i] = new
        out.append("`".join(parts))
    return "\n".join(out), converted

def main():
    sources = (glob.glob(os.path.join(ROOT, "engines", "*.md"))
               + glob.glob(os.path.join(ROOT, "concepts", "*.md"))
               + [os.path.join(ROOT, f) for f in ("index.md", "decision-guide.md", "log.md", "ranking.md")])
    total_links, total_files = 0, 0
    for fp in sorted(sources):
        if not os.path.exists(fp):
            continue
        new, n = convert_file(fp)
        if n:
            total_files += 1; total_links += n
            if not DRY:
                open(fp, "w", encoding="utf-8").write(new)
    print(f"{'[dry-run] ' if DRY else ''}converted {total_links} wikilinks across {total_files} files "
          f"({len(targets)} known slugs)")

if __name__ == "__main__":
    main()
