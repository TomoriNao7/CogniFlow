"""评估集静态校验（P2 锚点版）。

只做一件事：不跑检索、不连数据库，逐条验证 queries.jsonl 里的每个锚点
是否作为**整行**真实存在于对应文档中。

为什么需要：锚点是整行精确匹配，写错一个层级（比如把 `## 保价期限` 写成
`### 保价期限`）就会让该条标注解析不到 chunk，跑分时被静默剔除——
表现是「分数莫名变低」，极难定位。上次跑分就因此剔除过 2 条。
"""

import json
import os
import sys
from collections import Counter, defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EVAL_DIR = os.path.join(BASE, "backend", "eval")
DATA_DIR = os.path.join(BASE, "data")


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
    """doc 字段形如 'pre_sales / 商品目录'（显示用分隔符带空格），不带扩展名。

    注意：这里的 " / " 是给人看的，不是路径分隔符，必须先还原成真实目录分隔符。
    """
    rel = doc_key.replace(" / ", "/")
    for ext in (".md", ".faq"):
        p = os.path.join(DATA_DIR, rel + ext)
        if os.path.isfile(p):
            return p
    return None


def main():
    queries = parse_queries(os.path.join(EVAL_DIR, "queries.jsonl"))
    no_answer = parse_queries(os.path.join(EVAL_DIR, "queries_no_answer.jsonl"))

    print(f"queries.jsonl 有效条数: {len(queries)}")
    print(f"queries_no_answer.jsonl 有效条数: {len(no_answer)}")
    print()

    # 结构完整性
    missing_fields = [q.get("query", "<无 query>") for q in queries
                      if not q.get("query") or not q.get("bucket") or not q.get("difficulty") or "relevant" not in q]
    if missing_fields:
        print(f"[✗] 字段缺失 {len(missing_fields)} 条: {missing_fields}")
    else:
        print("[✓] 字段完整性：query / bucket / difficulty / relevant 全部齐备")

    # 分桶与难度分布
    bc = Counter(q["bucket"] for q in queries)
    dc = Counter(q["difficulty"] for q in queries)
    print(f"\n分桶分布: {dict(bc)}")
    print(f"难度分布: {dict(dc)}")
    multi = sum(1 for q in queries if len(q["relevant"]) >= 2)
    print(f"多跳（relevant ≥ 2）: {multi} 条")

    # 唯一性
    qs = [q["query"] for q in queries]
    dup = [k for k, v in Counter(qs).items() if v > 1]
    if dup:
        print(f"\n[✗] 重复 query {len(dup)} 条: {dup}")
    else:
        print("\n[✓] query 无重复")

    # 锚点逐条校验
    doc_lines = {}
    problems = []
    checked = 0
    for i, q in enumerate(queries, 1):
        for r in q["relevant"]:
            doc_key = r["doc"]
            anchor = r["anchor"]
            if doc_key not in doc_lines:
                path = find_doc(doc_key)
                if path is None:
                    problems.append((i, q["query"], doc_key, anchor, "文档不存在"))
                    doc_lines[doc_key] = set()
                else:
                    doc_lines[doc_key] = set(ln.strip() for ln in load_lines(path))
            lines = doc_lines[doc_key]
            if anchor not in lines:
                problems.append((i, q["query"], doc_key, anchor, "锚点未命中"))
            checked += 1

    print(f"\n锚点校验：共 {checked} 个锚点")
    if problems:
        print(f"[✗] {len(problems)} 个问题：")
        for i, q, d, a, reason in problems:
            print(f"  第{i}条 「{q}」  doc={d}  anchor={a!r}  → {reason}")
    else:
        print("[✓] 全部锚点都能在对应文档中整行命中")

    # 无答案集字段
    na_bad = [q["query"] for q in no_answer
              if not q.get("query") or not q.get("expect") or not q.get("why")]
    print(f"\n无答案集字段校验: {'[✗] ' + str(na_bad) if na_bad else '[✓] query / expect / why 齐备'}")
    expects = Counter(q.get("expect") for q in no_answer)
    print(f"无答案集 expect 分布: {dict(expects)}")

    return 1 if (problems or missing_fields or dup or na_bad) else 0


if __name__ == "__main__":
    sys.exit(main())
