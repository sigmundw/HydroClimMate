#!/usr/bin/env python3
"""format_markdown.py -- reflows every Markdown file in the product repository to one
line per paragraph (soft wrap): the continuation lines of a paragraph, of a list item
(including a nested item and its own indented continuation lines), and of a blockquote
are joined into a single line each, with the join collapsed to one space.

Left untouched: fenced code blocks, indented code blocks, table rows, headings, raw HTML
lines, link-reference definitions, thematic breaks, and a line ending in an intentional
hard break (two trailing spaces or a trailing backslash) -- a hard break ends the current
line without joining the next one into it.

Output: no trailing whitespace on any line, at most one blank line between blocks (blank
runs are collapsed, never inserted where none existed), and the file ends with exactly
one newline. YAML front matter (a file's first line is exactly "---", up to the next
line that is exactly "---") is copied through byte-for-byte.

This is a line-based reflow, not a full CommonMark parser; it is written to be exactly
right for the Markdown conventions this repository actually uses (verified by the
word-sequence-preservation check --check itself is not) rather than for arbitrary
Markdown input.

Usage:
  python3 evals/format_markdown.py [--check] [FILE ...]

With no FILE arguments, formats (or, under --check, checks) every *.md file in the repo
root, hydroclimmate/, and evals/. --check reports files that are not already formatted
and exits non-zero without writing anything; with no --check, files are rewritten in
place (idempotent -- a second run changes nothing).
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FENCE_RE = re.compile(r"^(\s*)(`{3,}|~{3,})")
LIST_MARKER_RE = re.compile(r"^(\s*)([-*+]|\d+[.)])(\s+)(.*)$")
BLOCKQUOTE_RE = re.compile(r"^(\s*)(>+)(\s?)(.*)$")
HEADING_RE = re.compile(r"^(\s{0,3})#{1,6}(\s|$)")
# A GFM table row/delimiter row in this repo's own Markdown always starts with a leading
# "|" (after up to 3 spaces of indent) -- a line that merely contains a "|" somewhere
# (e.g. inline code listing a pipe-separated enum, `a|b|c`) is prose, not a table row.
TABLE_ROW_RE = re.compile(r"^\s{0,3}\|")
THEMATIC_BREAK_RE = re.compile(r"^\s{0,3}([-*_])(\s*\1){2,}\s*$")
LINK_REF_DEF_RE = re.compile(r"^\s{0,3}\[[^\]]+\]:\s")
HTML_LINE_RE = re.compile(r"^\s{0,3}<")
HARD_BREAK_RE = re.compile(r"(  |\\)$")


def _is_indented_code(line):
    return bool(re.match(r"^(?: {4,}|\t)", line)) and not LIST_MARKER_RE.match(line)


def _in_open_code_span(lines_so_far):
    """True if the inline backtick count across `lines_so_far` (joined) is odd, i.e. an
    inline code span (`` `...` ``) opened on an earlier line has not yet closed. A line
    inside such a span must always be joined to the paragraph/item/quote it belongs to,
    never treated as the start of a new block -- its content (e.g. `<NAME>`, `- x`, `# y`)
    is code, not markdown structure."""
    return ("\n".join(lines_so_far).count("`")) % 2 == 1


def _join(lines):
    """Join a paragraph's raw lines into one, stripping each line's own leading/trailing
    whitespace before joining with a single space -- except a line ending in an
    intentional hard break, which must not be joined to what follows (the caller never
    hands such a line anything to join after it; this only strips its own edges)."""
    parts = [ln.rstrip() for ln in lines]
    return " ".join(p.strip() for p in parts)


def format_text(text):
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()  # split on the final trailing newline

    out = []
    i = 0
    n = len(lines)

    # YAML front matter: only at the very start of the file.
    if i < n and lines[i] == "---":
        out.append(lines[i])
        i += 1
        while i < n and lines[i] != "---":
            out.append(lines[i])
            i += 1
        if i < n:
            out.append(lines[i])
            i += 1

    def blank_run_collapsed():
        if out and out[-1] != "":
            out.append("")

    while i < n:
        line = lines[i]

        if line.strip() == "":
            blank_run_collapsed()
            i += 1
            continue

        fence_m = FENCE_RE.match(line)
        if fence_m:
            fence_char = fence_m.group(2)[0]
            fence_indent = fence_m.group(1)
            out.append(line.rstrip())
            i += 1
            while i < n:
                out.append(lines[i])
                closing = re.match(r"^\s*(`{3,}|~{3,})\s*$", lines[i])
                is_close = (closing and closing.group(1)[0] == fence_char
                            and len(closing.group(1)) >= len(fence_m.group(2)))
                i += 1
                if is_close:
                    break
            continue

        if HEADING_RE.match(line) or THEMATIC_BREAK_RE.match(line) or \
                LINK_REF_DEF_RE.match(line) or HTML_LINE_RE.match(line):
            out.append(line.rstrip())
            i += 1
            continue

        if TABLE_ROW_RE.match(line) and "|" in line:
            out.append(line.rstrip())
            i += 1
            continue

        if _is_indented_code(line):
            out.append(line.rstrip())
            i += 1
            continue

        bq_m = BLOCKQUOTE_RE.match(line)
        if bq_m:
            buf = [bq_m.group(4)]
            hard_break = bool(HARD_BREAK_RE.search(line))
            i += 1
            while i < n and not hard_break:
                nxt = lines[i]
                if nxt.strip() == "" and not _in_open_code_span(buf):
                    break
                if _in_open_code_span(buf):
                    buf.append(nxt)
                    hard_break = bool(HARD_BREAK_RE.search(nxt))
                    i += 1
                    continue
                nxt_bq = BLOCKQUOTE_RE.match(nxt)
                if nxt_bq:
                    buf.append(nxt_bq.group(4))
                    hard_break = bool(HARD_BREAK_RE.search(nxt))
                    i += 1
                    continue
                if LIST_MARKER_RE.match(nxt) or HEADING_RE.match(nxt) or \
                        FENCE_RE.match(nxt) or (TABLE_ROW_RE.match(nxt) and "|" in nxt):
                    break
                buf.append(nxt)
                hard_break = bool(HARD_BREAK_RE.search(nxt))
                i += 1
            out.append("> " + _join(buf))
            continue

        list_m = LIST_MARKER_RE.match(line)
        if list_m:
            prefix = list_m.group(1) + list_m.group(2) + list_m.group(3)
            content_indent = len(prefix)
            buf = [list_m.group(4)]
            hard_break = bool(HARD_BREAK_RE.search(line))
            i += 1
            while i < n and not hard_break:
                nxt = lines[i]
                if nxt.strip() == "" and not _in_open_code_span(buf):
                    break
                if _in_open_code_span(buf):
                    buf.append(nxt)
                    hard_break = bool(HARD_BREAK_RE.search(nxt))
                    i += 1
                    continue
                if LIST_MARKER_RE.match(nxt) or HEADING_RE.match(nxt) or \
                        FENCE_RE.match(nxt) or BLOCKQUOTE_RE.match(nxt) or \
                        (TABLE_ROW_RE.match(nxt) and "|" in nxt) or \
                        THEMATIC_BREAK_RE.match(nxt):
                    break
                leading = len(nxt) - len(nxt.lstrip(" "))
                if leading < content_indent and nxt.strip() and leading >= 4 and \
                        _is_indented_code(nxt):
                    break
                buf.append(nxt)
                hard_break = bool(HARD_BREAK_RE.search(nxt))
                i += 1
            out.append(prefix + _join(buf))
            continue

        # Plain paragraph.
        buf = [line]
        hard_break = bool(HARD_BREAK_RE.search(line))
        i += 1
        while i < n and not hard_break:
            nxt = lines[i]
            if nxt.strip() == "" and not _in_open_code_span(buf):
                break
            if _in_open_code_span(buf):
                buf.append(nxt)
                hard_break = bool(HARD_BREAK_RE.search(nxt))
                i += 1
                continue
            if LIST_MARKER_RE.match(nxt) or HEADING_RE.match(nxt) or FENCE_RE.match(nxt) or \
                    BLOCKQUOTE_RE.match(nxt) or (TABLE_ROW_RE.match(nxt) and "|" in nxt) or \
                    THEMATIC_BREAK_RE.match(nxt) or LINK_REF_DEF_RE.match(nxt) or \
                    HTML_LINE_RE.match(nxt) or _is_indented_code(nxt):
                break
            buf.append(nxt)
            hard_break = bool(HARD_BREAK_RE.search(nxt))
            i += 1
        out.append(_join(buf))

    while out and out[-1] == "":
        out.pop()
    return "\n".join(out) + "\n"


CODE_FENCE_SPLIT_RE = re.compile(r"^(\s*)(`{3,}|~{3,})")


def _code_spans(text):
    """(start, end) character offsets of every fenced-code-block body (fence lines
    included), so the word-sequence check can skip them."""
    spans = []
    lines = text.split("\n")
    offset = 0
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        m = CODE_FENCE_SPLIT_RE.match(line)
        if m:
            start = offset
            fence_char = m.group(2)[0]
            fence_len = len(m.group(2))
            offset += len(line) + 1
            i += 1
            while i < n:
                closing = re.match(r"^\s*(`{3,}|~{3,})\s*$", lines[i])
                is_close = closing and closing.group(1)[0] == fence_char and \
                    len(closing.group(1)) >= fence_len
                offset += len(lines[i]) + 1
                i += 1
                if is_close:
                    break
            spans.append((start, offset))
            continue
        offset += len(line) + 1
        i += 1
    return spans


def words_outside_code(text):
    spans = _code_spans(text)
    out_chars = []
    pos = 0
    for start, end in spans:
        out_chars.append(text[pos:start])
        pos = end
    out_chars.append(text[pos:])
    stripped = "".join(out_chars)
    return re.findall(r"\S+", stripped)


def count_blocks(text):
    spans = _code_spans(text)
    kept = []
    pos = 0
    for start, end in spans:
        kept.append(text[pos:start])
        pos = end
    kept.append(text[pos:])
    stripped = "".join(kept)
    n_headings = len(re.findall(r"^\s{0,3}#{1,6}\s", stripped, re.M))
    n_list_items = len(re.findall(r"^\s*(?:[-*+]|\d+[.)])\s+", stripped, re.M))
    n_table_rows = len(re.findall(r"^\s{0,3}\|.*$", stripped, re.M))
    n_fences = len(re.findall(r"^\s*(?:`{3,}|~{3,})", text, re.M))
    return n_headings, n_list_items, n_table_rows, n_fences


def verify(original, formatted):
    """Return a list of problems (empty if `formatted` is a pure whitespace reflow of
    `original`): identical word sequence outside code blocks, identical block counts."""
    problems = []
    w1, w2 = words_outside_code(original), words_outside_code(formatted)
    if w1 != w2:
        problems.append(f"word sequence outside code blocks changed ({len(w1)} -> {len(w2)} words)")
    b1, b2 = count_blocks(original), count_blocks(formatted)
    if b1 != b2:
        problems.append(f"block counts (headings, list items, table rows, fences) changed: {b1} -> {b2}")
    return problems


def default_files():
    files = []
    for root_dir in (ROOT, ROOT / "hydroclimmate", ROOT / "evals"):
        files.extend(sorted(root_dir.rglob("*.md")))
    return sorted(set(files))


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    check = "--check" in argv
    files = [Path(a) for a in argv if a != "--check"]
    if not files:
        files = default_files()

    def _label(path):
        try:
            return str(path.relative_to(ROOT))
        except ValueError:
            return str(path)

    changed = []
    problems_by_file = {}
    for path in files:
        original = path.read_text(encoding="utf-8")
        formatted = format_text(original)
        problems = verify(original, formatted)
        if problems:
            problems_by_file[_label(path)] = problems
            continue
        if formatted != original:
            changed.append(path)
            if not check:
                path.write_text(formatted, encoding="utf-8")

    if problems_by_file:
        for rel, problems in problems_by_file.items():
            print(f"UNSAFE: {rel}: " + "; ".join(problems))
        sys.exit(f"ERROR: {len(problems_by_file)} file(s) would not be a pure whitespace "
                  "reflow; left unchanged. Fix format_markdown.py or the file's Markdown "
                  "shape, not by forcing the join.")

    if check:
        if changed:
            for path in changed:
                print(f"NOT FORMATTED: {_label(path)}")
            sys.exit(f"ERROR: {len(changed)} file(s) need `python3 evals/format_markdown.py`")
        print(f"PASS: {len(files)} Markdown files already one-line-per-paragraph formatted")
        return 0

    print(f"Reformatted {len(changed)} of {len(files)} Markdown files "
          f"({len(files) - len(changed)} already formatted)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
