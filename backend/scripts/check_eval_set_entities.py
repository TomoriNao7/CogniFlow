"""评估集实体对齐体检（P4 前置质检）。

只做一件事：不跑检索、不连数据库，检查「单品属性」桶里 query 提到的产品型号
与该条 relevant 锚点所在章节的型号**是否对得上**。

为什么需要：自标评估集最危险处是 query 与 anchor 的实体错配——query 问
iPhone 15 Pro，anchor 却指向 iPhone 15 Pro Max，评测立刻失真。锚点校验脚本
（check_eval_set.py）只验证锚点整行存在，验证不了实体对齐。

判定规则（刻意保守，避免误报）：
- 只检查 bucket == 单品属性 的条目；促销与券 / 政策条款等桶的锚点是规则章节，
  query 里的产品只是语境，不做产品实体对齐。
- 引入「型号注册表」：从语料标题里抽出所有带数字的产品型号（如 iphone 15 pro、
  iphone 15 pro max）。归一化时剥掉品牌前缀（sony / samsung 等）与容量后缀
  （256gb / 512gb）。
- 两者实体集合都不为空且无交集才判错配；交集判定用「集合 + 前缀包含」，
  并要求前缀包含的较短一方**不是注册表里的完整型号**——这样
  "iphone 15 pro"（是完整型号）对 "iphone 15 pro max"（另一型号）会判错配，
  而 "ipad pro"（非完整型号，是家族泛称）对 "ipad pro m4" 会判通过。
"""

import json
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EVAL_DIR = os.path.join(BASE, "backend", "eval")
DATA_DIR = os.path.join(BASE, "data")

# 拉丁字母开头的连续片段，可跨空格拼接（如 "iPhone 15 Pro Max"）
_LATIN_SPAN_RE = re.compile(r"[A-Za-z][A-Za-z0-9]*(?:\s[A-Za-z0-9]+)*")

# 无数字但仍需作为产品实体的家族词（iPad / MacBook / AirPods 等系列名）
_BRAND_FAMILY = {
    "iphone", "ipad", "macbook", "airpods", "apple", "watch", "mac",
    "sony", "bose", "samsung", "xiaomi", "redmi", "oneplus", "huawei",
    "honor", "thinkpad", "dell", "asus", "steam", "playstation", "xbox",
    "switch", "dualsense", "keyboard", "monitor", "quietcomfort",
}

# 品牌前缀（归一化时剥掉，如 "Sony PlayStation 5 Slim" -> "playstation 5 slim"）
_BRANDS = (
    "sony", "apple", "samsung", "xiaomi", "redmi", "huawei", "honor",
    "oneplus", "dell", "asus", "bose", "lenovo", "nintendo", "microsoft",
)

# 容量/规格后缀（归一化时剥掉，如 "iPhone 15 Pro Max 256GB" -> "iphone 15 pro max"）
_SPEC_SUFFIX_RE = re.compile(r"\s+\d+(?:\.\d+)?\s*(?:gb|tb|t|g|mb)$", re.I)

# 促销代码类噪声实体，不参与对齐
_PROMO_NOISE_RE = re.compile(r"(618|double11|double11|new\d+|phone\d+|audio\d+)", re.I)


def normalize(span: str) -> str:
    """实体归一化：小写、去标点、压掉多余空格。"""
    s = span.lower()
    s = re.sub(r"[()\"“”‘’/\\|、，。，:：]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _strip_spec(s: str) -> str:
    """剥掉尾部容量/规格后缀。"""
    new = _SPEC_SUFFIX_RE.sub("", s)
    return new if new else s


def _strip_brand(s: str) -> str:
    """剥掉品牌前缀，仅当剩余部分仍含数字时才剥（避免 "apple watch" 被剥成泛称）。"""
    parts = s.split()
    while parts and parts[0] in _BRANDS:
        parts.pop(0)
    rest = " ".join(parts)
    return rest if any(ch.isdigit() for ch in rest) else s


def extract_entities(text: str) -> set[str]:
    """从一段文本里抽出产品型号实体集合（已归一化、剥品牌、剥容量后缀）。"""
    entities: set[str] = set()
    for span in _LATIN_SPAN_RE.findall(text):
        norm = _strip_spec(normalize(span))
        if not norm:
            continue
        if _PROMO_NOISE_RE.search(norm):
            continue
        if any(ch.isdigit() for ch in norm) or norm in _BRAND_FAMILY:
            entities.add(_strip_brand(norm))
    return entities


def load_lines(path):
    with open(path, encoding="utf-8") as f:
        return f.read().splitlines()


def parse_queries(path):
    """解析 JSONL，跳过注释行（以 # 开头）。"""
    out = []
    for ln in load_lines(path):
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        out.append(json.loads(ln))
    return out


def find_doc(doc_key):
    """doc 字段形如 'pre_sales / 商品目录'，' / ' 是显示分隔符，还原成真实路径。"""
    rel = doc_key.replace(" / ", "/")
    for ext in (".md", ".faq"):
        p = os.path.join(DATA_DIR, rel + ext)
        if os.path.isfile(p):
            return p
    return None


def build_model_registry(data_dir):
    """从语料标题里抽出所有带数字的产品型号，作为「完整型号」判定基准。

    标题行形如 `### iPhone 15 Pro Max`。归一化后入表。
    """
    registry: set[str] = set()
    for root, _dirs, files in os.walk(data_dir):
        for fn in files:
            if not fn.endswith((".md", ".faq")):
                continue
            for ln in load_lines(os.path.join(root, fn)):
                if not ln.lstrip().startswith("#"):
                    continue
                ents = extract_entities(ln)
                for e in ents:
                    if any(ch.isdigit() for ch in e):
                        registry.add(e)
    return registry


def entities_match(q_ent: str, a_ent: str, registry: set[str]) -> bool:
    """判断两个实体是否指向同一产品。"""
    if q_ent == a_ent:
        return True
    shorter, longer = sorted([q_ent, a_ent], key=len)
    if longer.startswith(shorter):
        # 较短一方若是注册表里的完整型号，则较长是另一个型号（如 pro vs pro max）→ 错配
        if shorter in registry:
            return False
        return True
    return False


def section_text(lines, anchor):
    """取锚点所在章节的正文，用于抽实体。

    - 标题锚点（## / ###）：标题行 + 其下内容，直到下一个同级或更高级标题。
    - FAQ 锚点（Q: 开头）：该行 + 其下内容，直到下一个 Q: 行。
    锚点不存在时返回空串。
    """
    idx = None
    for i, ln in enumerate(lines):
        if ln.strip() == anchor.strip():
            idx = i
            break
    if idx is None:
        return ""

    is_heading = anchor.strip().startswith("#")
    out = [lines[idx]]
    if is_heading:
        start_level = len(anchor.strip()) - len(anchor.strip().lstrip("#"))
        for ln in lines[idx + 1:]:
            stripped = ln.strip()
            if stripped.startswith("#"):
                level = len(stripped) - len(stripped.lstrip("#"))
                if level <= start_level:
                    break
            out.append(ln)
    else:
        for ln in lines[idx + 1:]:
            if ln.strip().startswith("Q:") or ln.strip().startswith("Q："):
                break
            out.append(ln)
    return "\n".join(out)


def main():
    registry = build_model_registry(DATA_DIR)
    print(f"[registry] 从语料标题提取完整型号 {len(registry)} 个")

    sets = [
        ("queries.jsonl", os.path.join(EVAL_DIR, "queries.jsonl")),
        ("queries_multiturn.jsonl", os.path.join(EVAL_DIR, "queries_multiturn.jsonl")),
    ]

    doc_lines_cache: dict[str, list[str]] = {}
    problems = []
    checked = 0
    skipped_other_bucket = 0
    skipped_no_anchor_entity = 0

    for name, path in sets:
        if not os.path.isfile(path):
            print(f"[跳过] {name} 不存在")
            continue
        queries = parse_queries(path)
        print(f"\n=== {name}：{len(queries)} 条 ===")
        for i, q in enumerate(queries, 1):
            bucket = q.get("bucket", "")
            query = q.get("query", "")
            if bucket != "单品属性":
                skipped_other_bucket += 1
                continue
            q_entities = extract_entities(query)
            if not q_entities:
                continue
            for r in q.get("relevant", []):
                doc_key = r["doc"]
                anchor = r["anchor"]
                if doc_key not in doc_lines_cache:
                    p = find_doc(doc_key)
                    doc_lines_cache[doc_key] = load_lines(p) if p else []
                lines = doc_lines_cache[doc_key]
                sec = section_text(lines, anchor)
                if not sec:
                    problems.append((name, i, bucket, query, doc_key, anchor, "锚点不存在"))
                    continue
                sec_entities = extract_entities(sec)
                if not sec_entities:
                    skipped_no_anchor_entity += 1
                    continue
                checked += 1
                # 任一对实体能匹配即视为对齐
                matched = any(
                    entities_match(qe, ae, registry)
                    for qe in q_entities for ae in sec_entities
                )
                if not matched:
                    problems.append(
                        (name, i, bucket, query, doc_key, anchor,
                         f"query 实体 {sorted(q_entities)} 与锚点章节实体 {sorted(sec_entities)} 无交集")
                    )

    print(f"\n实体对齐检查：单品属性桶比对 {checked} 个锚点；"
          f"跳过非单品属性 {skipped_other_bucket} 条、锚点无产品实体 {skipped_no_anchor_entity} 个")
    if problems:
        print(f"[✗] {len(problems)} 处实体错配：")
        for name, i, bucket, query, doc_key, anchor, reason in problems:
            print(f"  [{name} 第{i}条/{bucket}] 「{query}」 doc={doc_key} anchor={anchor!r} → {reason}")
        return 1
    print("[✓] 全部产品实体对齐通过，无错配")
    return 0


if __name__ == "__main__":
    sys.exit(main())
