"""_anchor_hash.py -- shared logic for the curated-fact/prose drift check (D1): a
curated structured-layer fact's `confirmed_against` is a hash of the prose paragraph its
`from.anchor` points to, at the time the fact was last hand-confirmed against that prose.
If the paragraph's text changes (a prose correction), the hash no longer matches, and
the fact must be re-confirmed -- this is how a prose fix is made to force re-checking
every curated fact that cites it, rather than silently going stale (see the incident
that motivated this: switches.yaml/interface.yaml kept an old, corrected urban
statement after processes.md was fixed, still citing the corrected anchor).

Used by evals/check_knowledge.py (to verify) and tools/refresh_confirmed_against.py (to
recompute after a legitimate prose change).
"""
import hashlib
import re

HEADING_RE = re.compile(r"^(#+)[ \t]+(.+?)[ \t]*$", re.M)


def _slug(heading_text):
    return re.sub(r"[^\w\- ]", "", heading_text.lower()).replace(" ", "-")


def anchor_paragraph(text, anchor):
    """Return the raw text of the section following the heading whose slug is `anchor`,
    up to (not including) the next heading of any level, or None if no heading in `text`
    slugs to `anchor`."""
    headings = [(m.start(), m.end(), _slug(m.group(2))) for m in HEADING_RE.finditer(text)]
    for i, (start, end, slug) in enumerate(headings):
        if slug != anchor:
            continue
        body_start = end
        body_end = headings[i + 1][0] if i + 1 < len(headings) else len(text)
        return text[body_start:body_end].strip()
    return None


def anchor_paragraph_hash(text, anchor):
    """sha256 hex digest of the anchor paragraph's text (whitespace-normalized: runs of
    whitespace collapsed to one space, so a pure line-wrap/reflow does not itself count
    as a change), or None if the anchor does not exist in `text`."""
    body = anchor_paragraph(text, anchor)
    if body is None:
        return None
    normalized = re.sub(r"\s+", " ", body).strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
