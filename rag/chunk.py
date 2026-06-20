"""Split a briefing into retrievable chunks.

A briefing is small (a structured summary plus a few paragraphs of
commentary), so chunking is light: the summary input is kept whole and the
commentary is broken on blank lines, with very short fragments merged into
the previous chunk. Keeping the summary and commentary as separate sources
lets a question about raw numbers and a question about narrative tone each
land on the right kind of text.
"""

MIN_CHARS = 80


def _split_paragraphs(text):
    blocks = [b.strip() for b in text.split("\n\n")]
    return [b for b in blocks if b]


def _merge_short(blocks):
    merged = []
    for block in blocks:
        if merged and len(block) < MIN_CHARS:
            merged[-1] = merged[-1] + "\n\n" + block
        else:
            merged.append(block)
    return merged


def chunk_briefing(summary_input, commentary):
    """Return a list of (source, text) chunks for one briefing.

    source is "summary" or "commentary" so retrieval results can say which
    part of the briefing they came from.
    """
    chunks = []

    summary = (summary_input or "").strip()
    if summary:
        chunks.append(("summary", summary))

    for block in _merge_short(_split_paragraphs(commentary or "")):
        chunks.append(("commentary", block))

    return chunks
