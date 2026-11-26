"""多轮评估集静态校验（C-2）—— 不连库，只校验结构与锚点。

与 `check_eval_set.py` 同源的校验思路，额外校验多轮特有的约束：
分组轮次连续、`depends_on` 指向同组真实的前序轮、`history` 与前面轮次逐句一致。
锚点仍然按「整行精确匹配」校验，避免层级写错时静默剔除标注。
"""

from __future__ import annotations

import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EVAL_DIR = os.path.join(BASE, "backend", "eval")
DATA_DIR = os.path.join(BASE, "data")

BUCKETS = {"单品属性", "促销与券", "政策条款", "售后流程", "跨实体规则"}


def parse_rows(path: str) -> list[dict]:
    rows: list[dict] = []
    with open(path, encoding="utf-8") as fh:
        for ln, line in enumerate(fh, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                print(f"[ERR] 第 {ln} 行不是合法 JSON：{exc}")
                return []
    return rows


def find_doc(doc_key: str) -> str | None:
    """把显示分隔符还原成相对路径，逐个试 .md / .faq 后缀。"""
    rel = doc_key.replace(" / ", "/")
    for suffix in (".md", ".faq"):
        candidate = os.path.join(DATA_DIR, rel + suffix)
        if os.path.isfile(candidate):
            return candidate
    return None


def check_anchor(doc_key: str, anchor: str) -> tuple[bool, str]:
    """锚点必须在对应文档里整行命中。"""
    path = find_doc(doc_key)
    if path is None:
        return False, f"找不到文档：{doc_key}"
    with open(path, encoding="utf-8") as fh:
        lines = [ln.rstrip("\n") for ln in fh]
    if anchor in lines:
        return True, ""
    near = [ln for ln in lines if ln.strip() and anchor.strip() in ln]
    hint = ""
    if near:
        hint = f"（有近似行但层级/措辞不一致：{near[0]!r}）"
    return False, f"锚点未整行命中：{doc_key} -> {anchor!r}{hint}"


def main() -> int:
    path = os.path.join(EVAL_DIR, "queries_multiturn.jsonl")
    rows = parse_rows(path)
    if not rows:
        print("[ERR] 未读到任何有效记录")
        return 1

    errors: list[str] = []
    queries: set[str] = set()
    groups: dict[str, list[dict]] = {}
    required = ("group", "turn", "history", "query", "bucket", "difficulty",
                "answer_scope", "depends_on", "relevant")

    for i, row in enumerate(rows, 1):
        missing = [k for k in required if k not in row]
        if missing:
            errors.append(f"记录 {i} 缺字段：{missing}")
            continue

        g, turn = row["group"], row["turn"]
        if not isinstance(g, str) or not g:
            errors.append(f"记录 {i}：group 非法")
            continue
        if not isinstance(turn, int) or turn < 1:
            errors.append(f"记录 {i}：turn 非法：{turn!r}")
            continue

        # query 唯一且非空
        q = str(row["query"]).strip()
        if not q:
            errors.append(f"记录 {i}：query 为空")
        elif q in queries:
            errors.append(f"记录 {i}：query 重复：{q}")
        queries.add(q)

        if row["bucket"] not in BUCKETS:
            errors.append(f"记录 {i}：bucket 非法：{row['bucket']!r}")
        if row["difficulty"] not in ("easy", "hard"):
            errors.append(f"记录 {i}：difficulty 非法：{row['difficulty']!r}")

        scope = row["answer_scope"]
        if scope not in ("self", "dep_turn"):
            errors.append(f"记录 {i}：answer_scope 非法：{scope!r}")

        # 分组轮次连续
        groups.setdefault(g, []).append(row)
        group_turns = [r["turn"] for r in groups[g]]
        if group_turns != list(range(1, len(group_turns) + 1)):
            errors.append(f"组 {g} 轮次不连续：{group_turns}")

        # depends_on / history 约束
        if scope == "self":
            if row["depends_on"] is not None:
                errors.append(f"记录 {i}：self 轮不应有 depends_on")
        else:
            dep = row["depends_on"]
            if not isinstance(dep, int) or dep < 1 or dep >= turn:
                errors.append(f"记录 {i}：depends_on 非法（须指向同组 1~{turn - 1} 轮）：{dep!r}")
            else:
                prior = {r["turn"]: r for r in groups[g]}
                if dep not in prior:
                    errors.append(f"记录 {i}：depends_on 指向的 {dep} 轮不存在")

        # history 必须等于前面各轮的 query，按顺序
        expected = [str(r["query"]).strip() for r in groups[g] if r["turn"] < turn]
        actual = row["history"]
        if actual != expected:
            errors.append(
                f"记录 {i}（组 {g} 第 {turn} 轮）：history 与前序轮次不一致\n"
                f"       期望：{expected}\n       实际：{actual}"
            )

        # 锚点
        rel = row["relevant"]
        if not rel or not isinstance(rel, list):
            errors.append(f"记录 {i}：relevant 为空或非列表")
            continue
        for r in rel:
            if not isinstance(r, dict) or "doc" not in r or "anchor" not in r:
                errors.append(f"记录 {i}：relevant 条目缺 doc/anchor：{r!r}")
                continue
            ok, msg = check_anchor(r["doc"], r["anchor"])
            if not ok:
                errors.append(f"记录 {i}（{g} t{turn}）：{msg}")

    print(f"[eval] 多轮评估集：{len(rows)} 条，{len(groups)} 组")
    for g, rs in sorted(groups.items()):
        turns = [r["turn"] for r in rs]
        print(f"  {g}: {turns}  （{len(rs)} 轮）")

    if errors:
        print(f"\n[FAIL] 发现 {len(errors)} 个问题：")
        for e in errors:
            print(f"  - {e}")
        return 1

    print("\n[OK] 全部校验通过：字段完整、分组轮次连续、depends_on/history 一致、锚点全部整行命中")
    return 0


if __name__ == "__main__":
    sys.exit(main())
