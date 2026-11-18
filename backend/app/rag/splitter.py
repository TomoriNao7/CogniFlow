"""多格式文档切分器：Markdown、FAQ、PDF、Word、Excel、纯文本。"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class Chunk:
    """切分器产出的 chunk 单元。"""
    content: str
    chunk_index: int
    metadata: dict[str, str] = field(default_factory=dict)


# ── 文本切分器 ────────────────────────────────────────────────────────────

class MarkdownSplitter:
    """按「H2 分节 + H3 聚合」切分 Markdown。

    旧实现按 `#{1,3}` 每个标题一刀，导致两种病：
      ① 纯标题行单独成一个 chunk（无内容，纯噪声）；
      ② 一个商品/一个政策主题的属性被切成多个碎片（价格、颜色、规格各自一个），
         而「商品名/主题名」这个词又会在多个碎片里重复出现，检索时互相干扰。

    新规则：
      1. H1 视为文档标题，记入 metadata，不单独成 chunk；
      2. H2 是 chunk 的天然边界（一个商品、一个政策主题 = 一节）；
      3. H2 下的 H3 聚合进父节，不再单独成 chunk；
      4. 聚合后超过 max_chunk_size 时才回退到按 H3 拆分，
         避免 chunk 过大稀释向量（如「智能手机」大类下有 18 个商品）。
    """

    def __init__(self, max_chunk_size: int = 1500) -> None:
        self.max_chunk_size = max_chunk_size

    def split(self, text: str) -> list[Chunk]:
        chunks: list[Chunk] = []
        idx = 0

        # 1) 抽出 H1 文档标题（作为 metadata，不单独成 chunk）
        doc_title = ""
        title_match = re.search(r"^#\s+(.+)$", text, flags=re.MULTILINE)
        if title_match:
            doc_title = title_match.group(1).strip()

        # 2) 按 H2 切大节（只认 `## `，不再对 H3 切）
        sections = re.split(r"(?=^##\s)", text, flags=re.MULTILINE)

        for section in sections:
            section = section.strip()
            if not section:
                continue

            # 跳过只有 H1 标题的部分（已提取为 doc_title）
            if re.fullmatch(r"#\s+.*", section):
                continue

            h2_match = re.match(r"^##\s+(.+)", section)
            if not h2_match:
                # 不属于任何 H2 的前置文本（少见），整段作为一个 chunk
                if not section.startswith("#"):
                    chunks.append(Chunk(
                        content=section,
                        chunk_index=idx,
                        metadata={"heading": "", "doc_title": doc_title},
                    ))
                    idx += 1
                continue

            h2_heading = h2_match.group(1).strip()

            # 3) 整节不超过阈值 → 一节一个 chunk（商品/主题完整信息聚合）
            if len(section) <= self.max_chunk_size:
                chunks.append(Chunk(
                    content=section,
                    chunk_index=idx,
                    metadata={"heading": h2_heading, "doc_title": doc_title},
                ))
                idx += 1
                continue

            # 4) 超长 → 按 H3 拆分，相邻小块再合并，控制每个 chunk 不超阈值
            for content, heading in self._split_by_h3(section, h2_heading):
                chunks.append(Chunk(
                    content=content,
                    chunk_index=idx,
                    metadata={"heading": heading, "doc_title": doc_title},
                ))
                idx += 1

        # 兜底：整篇没有 H2（只有 H1/H3 或纯文本）时不能让文档丢空
        if not chunks and text.strip():
            for content, heading in self._split_by_h3(text, doc_title):
                chunks.append(Chunk(
                    content=content,
                    chunk_index=idx,
                    metadata={"heading": heading, "doc_title": doc_title},
                ))
                idx += 1

        return chunks

    def _split_by_h3(self, section: str, h2_heading: str) -> list[tuple[str, str]]:
        """把超长的 H2 节按 H3 拆开，返回 [(chunk 内容, 标题)]。

        每个 H3 独立成一个 chunk，**不做跨 H3 合并**。原因：目录型文档里
        一个 H3 就是一件商品（或一条规则），跨 H3 合并会把多个实体塞进同一个
        chunk —— 向量被稀释，而且「问其中任意一件都能命中」会让评估分数虚高。
        只有单个 H3 自身超过阈值时，才退化用定长切分继续拆。
        """
        parts = re.split(r"(?=^###\s)", section, flags=re.MULTILINE)

        # 首段是 H2 标题到第一个 H3 之间的前言（通常只有大类名），
        # 并入第一个 H3 chunk，避免产生一个只含标题的碎片
        preamble = ""
        if parts and not re.match(r"^###\s", parts[0].strip()):
            preamble = parts[0].strip()
            parts = parts[1:]

        if not parts:
            # 整节没有 H3 且本身超长 → 退化为定长切分
            fixed = FixedSizeSplitter(chunk_size=self.max_chunk_size, overlap=0)
            return [(c.content, h2_heading) for c in fixed.split(preamble or section)]

        out: list[tuple[str, str]] = []
        for part in parts:
            part = part.strip()
            if not part:
                continue

            # 标题要在并入前言之前取，否则前缀的 `##` 会让正则失配
            h3_match = re.match(r"^###\s+(.+)", part)
            heading = h3_match.group(1).strip() if h3_match else h2_heading

            if preamble:
                # 前言（如「## 智能手机」）留在第一个 H3 里，
                # 后面靠它判断商品属于哪个大类的跨实体问题才有依据
                part = f"{preamble}\n\n{part}"
                preamble = ""

            if len(part) > self.max_chunk_size:
                fixed = FixedSizeSplitter(chunk_size=self.max_chunk_size, overlap=0)
                out.extend((c.content, heading) for c in fixed.split(part))
            else:
                out.append((part, heading))

        return out


class FAQSplitter:
    """按 Q&A 自然边界切分。"""

    def split(self, text: str) -> list[Chunk]:
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
    """纯文本定长滑窗切分。"""

    def __init__(self, chunk_size: int = 512, overlap: int = 64) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap

    def split(self, text: str) -> list[Chunk]:
        chunks: list[Chunk] = []
        idx, start = 0, 0
        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            chunks.append(Chunk(content=text[start:end], chunk_index=idx))
            idx += 1
            if end >= len(text):
                break
            start = end - self.overlap
        return chunks


class SemanticSplitter:
    """按段落/小节边界切分有结构的文档。"""

    def __init__(self, max_chunk_size: int = 800, min_chunk_size: int = 200) -> None:
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size

    def split(self, text: str) -> list[Chunk]:
        # 先按空行切成段落
        paras = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]

        chunks: list[Chunk] = []
        idx = 0
        current = ""
        for para in paras:
            if len(current) + len(para) < self.max_chunk_size:
                current = (current + "\n\n" + para).strip()
            else:
                if len(current) >= self.min_chunk_size:
                    chunks.append(Chunk(content=current, chunk_index=idx))
                    idx += 1
                    current = para
                else:
                    current = (current + "\n\n" + para).strip()

        if current.strip():
            chunks.append(Chunk(content=current, chunk_index=idx))

        return chunks


class ExcelSplitter:
    """Excel 按行切分，每个 chunk 都带上表头。"""

    def __init__(self, rows_per_chunk: int = 10) -> None:
        self.rows_per_chunk = rows_per_chunk

    def split(self, rows: list[list[str]], headers: list[str] | None = None) -> list[Chunk]:
        if not rows:
            return []

        header_line = "\t".join(headers) if headers else ""
        chunks: list[Chunk] = []
        idx = 0
        for i in range(0, len(rows), self.rows_per_chunk):
            batch = rows[i:i + self.rows_per_chunk]
            lines = [header_line] if header_line else []
            for row in batch:
                lines.append("\t".join(str(c) for c in row))
            chunks.append(Chunk(
                content="\n".join(lines),
                chunk_index=idx,
                metadata={"rows": f"{i}-{i + len(batch)}", "format": "table"},
            ))
            idx += 1
        return chunks


# ── 文本抽取 ───────────────────────────────────────────────────────────

def extract_text(file_path: str, file_type: str) -> str:
    """从 PDF、Word、Excel 抽取纯文本。"""
    if file_type == "pdf":
        return _extract_pdf(file_path)
    elif file_type == "docx":
        return _extract_docx(file_path)
    elif file_type == "xlsx":
        return _extract_xlsx(file_path)
    return ""


def _extract_pdf(path: str) -> str:
    """用 pdfplumber 或 PyPDF2 抽取 PDF 文本。"""
    try:
        import pdfplumber
        texts: list[str] = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    texts.append(t)
        return "\n\n".join(texts)
    except ImportError:
        pass

    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(path)
        return "\n\n".join(page.extract_text() or "" for page in reader.pages)
    except ImportError:
        raise ImportError("需要安装 pdfplumber 或 PyPDF2: pip install pdfplumber")


def _extract_docx(path: str) -> str:
    """用 python-docx 抽取 Word 文本。"""
    try:
        from docx import Document
        doc = Document(path)
        paras: list[str] = []
        for para in doc.paragraphs:
            if para.style.name.startswith("Heading"):
                level = para.style.name.split()[-1]
                try:
                    lv = int(level)
                except ValueError:
                    lv = 1
                paras.append(f"{'#' * min(lv, 3)} {para.text}")
            elif para.text.strip():
                paras.append(para.text)
        return "\n\n".join(paras)
    except ImportError:
        raise ImportError("需要安装 python-docx: pip install python-docx")


def _extract_xlsx(path: str) -> str:
    """抽取 Excel 文本，按 tab 分隔行。"""
    try:
        from openpyxl import load_workbook
        wb = load_workbook(path, read_only=True, data_only=True)
        all_lines: list[str] = []
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            all_lines.append(f"## {sheet_name}")
            for row in ws.iter_rows(values_only=True):
                values = [str(c) if c is not None else "" for c in row]
                all_lines.append("\t".join(values))
        wb.close()
        return "\n".join(all_lines)
    except ImportError:
        raise ImportError("需要安装 openpyxl: pip install openpyxl")


# ── 路由分发 ───────────────────────────────────────────────────────────────────

def auto_split(text: str, file_type: str, file_path: str = "") -> list[Chunk]:
    """按文件类型路由到对应切分器。"""
    if file_type == "md":
        return MarkdownSplitter().split(text)
    if file_type == "faq":
        return FAQSplitter().split(text)
    if file_type in ("pdf", "docx"):
        return SemanticSplitter().split(text)
    if file_type == "xlsx":
        # 把 tab 分隔文本还原成行，交给 ExcelSplitter
        lines = text.strip().split("\n")
        rows: list[list[str]] = []
        headers: list[str] = []
        for i, line in enumerate(lines):
            if line.startswith("## "):
                continue  # 跳过 sheet 名标记行
            cells = line.split("\t")
            if i == 0:
                headers = cells
            else:
                rows.append(cells)
        return ExcelSplitter(rows_per_chunk=10).split(rows, headers)
    return FixedSizeSplitter().split(text)
