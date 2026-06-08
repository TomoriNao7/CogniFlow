from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class Chunk:
    """A chunk unit returned by any splitter pipeline."""

    content: str
    chunk_index: int
    metadata: dict[str, str] = field(default_factory=dict)


class MarkdownSplitter:
    """Split Markdown by H1/H2/H3 structure."""

    def split(self, text: str) -> list[Chunk]:
        chunks: list[Chunk] = []
        # Split on headings while keeping the heading with its content
        sections = re.split(r"(?=^#{1,3}\s)", text, flags=re.MULTILINE)
        idx = 0
        for section in sections:
            section = section.strip()
            if not section:
                continue
            heading_match = re.match(r"^(#{1,3})\s+(.+)", section)
            heading = heading_match.group(2) if heading_match else ""
            chunks.append(
                Chunk(content=section, chunk_index=idx, metadata={"heading": heading})
            )
            idx += 1
        return chunks


class FAQSplitter:
    """Split by Q&A natural boundaries."""

    def split(self, text: str) -> list[Chunk]:
        # Split on Q: or 问： patterns
        pairs = re.split(r"(?=^(?:Q|问)[：:])", text, flags=re.MULTILINE)
        chunks: list[Chunk] = []
        idx = 0
        for pair in pairs:
            pair = pair.strip()
            if not pair:
                continue
            chunks.append(Chunk(content=pair, chunk_index=idx))
            idx += 1
        return chunks


class FixedSizeSplitter:
    """Fixed-size sliding window splitter for plain text."""

    def __init__(self, chunk_size: int = 512, overlap: int = 64) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap

    def split(self, text: str) -> list[Chunk]:
        chunks: list[Chunk] = []
        idx = 0
        start = 0
        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            chunks.append(Chunk(content=text[start:end], chunk_index=idx))
            idx += 1
            if end >= len(text):
                break
            start = end - self.overlap
        return chunks


def auto_split(text: str, file_type: str) -> list[Chunk]:
    """Route to the correct splitter based on file type."""
    if file_type == "md":
        return MarkdownSplitter().split(text)
    if file_type == "faq":
        return FAQSplitter().split(text)
    return FixedSizeSplitter().split(text)
