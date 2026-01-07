"""Citation utilities for web search API responses."""

from collections import OrderedDict
from dataclasses import dataclass
from typing import Iterable, Optional, List


@dataclass(frozen=True)
class Citation:
    """Represents a citation with position and URL."""
    end_index: int  # marker insertion position (0-based)
    url: str
    title: Optional[str] = None


def render_markdown_with_footnotes(text: str, citations: Iterable[Citation]) -> str:
    """
    Convert citations to markdown footnotes.

    - Same URL reuses the same footnote number (deduplication).
    - Inserts markers in descending order of end_index to avoid index shift.

    Args:
        text: Original text content
        citations: Iterable of Citation objects

    Returns:
        Text with [^n] markers and footnote definitions appended
    """
    # Filter valid citations
    citations_list: List[Citation] = [
        c for c in citations
        if isinstance(c.end_index, int) and 0 <= c.end_index <= len(text) and c.url
    ]

    if not citations_list:
        return text

    # Assign footnote numbers per unique URL (preserving order)
    url_to_n: "OrderedDict[str, int]" = OrderedDict()
    footnotes: List[str] = []

    def get_footnote_number(url: str, title: Optional[str]) -> int:
        if url in url_to_n:
            return url_to_n[url]
        n = len(url_to_n) + 1
        url_to_n[url] = n
        label = title.strip() if title else url
        # Include link in footnote definition
        footnotes.append(f"[^{n}]: {label} — {url}")
        return n

    # Insert markers from end to start (to avoid index shift)
    out = text
    for c in sorted(citations_list, key=lambda x: x.end_index, reverse=True):
        n = get_footnote_number(c.url, c.title)
        out = out[:c.end_index] + f"[^{n}]" + out[c.end_index:]

    return out.rstrip() + "\n\n" + "\n".join(footnotes) + "\n"
