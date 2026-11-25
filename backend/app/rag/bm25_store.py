"""内存 BM25 关键词索引，pickle 落盘。

分词器可切换（char / jieba / bigram）。索引只持久化原文，语料在加载时
按当前分词器重建 —— 换分词器不必重新入库，也不会出现「索引按旧分词器
建好、查询按新分词器切」的静默失配。
"""

from __future__ import annotations

import logging
import os
import pickle
import re
from collections.abc import Iterator
from dataclasses import dataclass

from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)

# 中文连串 或 英文数字连串；标点与空白都当作分隔符丢弃
_TOKEN_RE = re.compile(r"[\u4e00-\u9fff]+|[A-Za-z0-9]+")

# 电商业务术语，避免 jieba 切碎（如「以旧/换新」「保价/期」）
_USER_DICT = (
    "以旧换新", "运费险", "保价期", "价格保护", "无理由退货", "三包", "退换货",
    "优惠券", "满减", "叠加", "限购", "预售", "定金", "尾款", "秒杀",
    "发票", "专票", "抬头", "冲红", "退款", "换货", "维修", "延保",
    "上门安装", "上楼费", "门店自提", "次日达", "当日达", "准时达",
    "实名认证", "异地登录", "账号注销", "花呗", "分期", "货到付款",
)

_jieba_ready = False
_current = "char"


@dataclass
class Bm25Doc:
    chunk_id: str
    content: str
    source_document: str
    heading: str
    chunk_index: int
    db_chunk_id: int = 0  # 权威主键 = knowledge_chunks.id（0 = 尚未入库）
    document_id: int = 0  # 所属文档 id，trace 落库时充外键


def _ensure_jieba() -> bool:
    """懒加载 jieba 并注入业务词典。"""
    global _jieba_ready
    if _jieba_ready:
        return True
    try:
        import jieba
    except ImportError:
        logger.warning("jieba 未安装，分词回退为单字切分")
        return False
    for term in _USER_DICT:
        jieba.add_word(term)
    _jieba_ready = True
    return True


def _spans(text: str) -> Iterator[tuple[str, bool]]:
    """产出 (片段, 是否中文)。"""
    for m in _TOKEN_RE.finditer(text):
        s = m.group()
        yield s, "\u4e00" <= s[0] <= "\u9fff"


def _tokenize_char(text: str) -> list[str]:
    """中文逐字切分（旧行为）。"""
    out: list[str] = []
    for s, cjk in _spans(text):
        if cjk:
            out.extend(s)
        else:
            out.append(s.lower())
    return out


def _tokenize_bigram(text: str) -> list[str]:
    """中文切字符二元组，免词典，对未登录词更稳。"""
    out: list[str] = []
    for s, cjk in _spans(text):
        if cjk:
            if len(s) == 1:
                out.append(s)
            else:
                out.extend(s[i : i + 2] for i in range(len(s) - 1))
        else:
            out.append(s.lower())
    return out


def _tokenize_jieba(text: str) -> list[str]:
    """按词典分词。"""
    if not _ensure_jieba():
        return _tokenize_char(text)
    import jieba

    out: list[str] = []
    for s, cjk in _spans(text):
        if cjk:
            out.extend(t.strip() for t in jieba.cut(s) if t.strip())
        else:
            out.append(s.lower())
    return out


_TOKENIZERS = {
    "char": _tokenize_char,
    "jieba": _tokenize_jieba,
    "bigram": _tokenize_bigram,
}


def _tokenize(text: str) -> list[str]:
    """按当前分词器切分。"""
    return _TOKENIZERS.get(_current, _tokenize_char)(text)


def available_tokenizers() -> list[str]:
    return list(_TOKENIZERS)


class Bm25Store:
    """内存 BM25 关键词索引。"""

    def __init__(self) -> None:
        self._docs: list[Bm25Doc] = []
        self._index: BM25Okapi | None = None
        self._corpus: list[list[str]] = []
        # 分词器由配置决定；此刻语料为空，set_tokenizer 只是记下选择
        try:
            from app.config import settings

            self.set_tokenizer(settings.bm25_tokenizer)
        except Exception as exc:  # 配置不可用时退回默认
            logger.debug("分词器初始化失败，沿用 %s：%s", _current, exc)

    @property
    def tokenizer(self) -> str:
        return _current

    def set_tokenizer(self, name: str) -> None:
        """切换分词器并重建语料与索引（不动原文，无需重新入库）。"""
        global _current
        key = (name or "char").lower()
        if key not in _TOKENIZERS:
            raise ValueError(f"未知分词器：{name}，可选 {list(_TOKENIZERS)}")
        if key == "jieba" and not _ensure_jieba():
            key = "char"
        _current = key
        self._reindex()
        logger.info("BM25 分词器切换为 %s（%d 条语料）", key, len(self._corpus))

    def _reindex(self) -> None:
        self._corpus = [_tokenize(d.content) for d in self._docs]
        self._index = BM25Okapi(self._corpus) if self._corpus else None

    def build(self, docs: list[Bm25Doc]) -> None:
        """用文档列表构建索引。"""
        self._docs = docs
        self._reindex()

    def search(self, query: str, top_k: int = 10) -> list[tuple[Bm25Doc, float]]:
        """检索 top_k，分数按本次最大值归一化。"""
        if not self._index or not self._docs:
            return []

        scores = self._index.get_scores(_tokenize(query))

        indexed = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        top = indexed[:top_k]

        max_score = max(scores) if len(scores) > 0 and max(scores) > 0 else 1.0

        return [(self._docs[i], score / max_score) for i, score in top if score > 0]

    def save(self, path: str) -> None:
        """索引落盘（只存原文，分词结果在 load 时重建）。"""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump({"docs": self._docs, "tokenizer": _current}, f)

    def load(self, path: str) -> None:
        """从磁盘加载索引，并按当前分词器重建语料。"""
        if not os.path.exists(path):
            raise FileNotFoundError(f"BM25 index not found: {path}")
        with open(path, "rb") as f:
            data = pickle.load(f)
        self._docs = data["docs"]
        self._reindex()

    @property
    def is_ready(self) -> bool:
        return self._index is not None and len(self._docs) > 0

    def __len__(self) -> int:
        return len(self._docs)


# 单例
bm25_store = Bm25Store()
