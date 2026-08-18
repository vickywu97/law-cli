#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
law-cli — 法条速查器 · 数据合规 MVP

设计红线（详见 README 与 新项目构思_合规与IP保护框架.md）：
1. 法条原文取自官方公开渠道，依《著作权法》第五条属公共领域，可合法使用。
2. 只提取条文原文，不复制任何第三方汇编结构 / 注释 / 效力说明。
3. 每条记录固定证据链：原文 + 来源URL + 公布/施行日期 + 检索日期 + SHA-256。
4. 不碰北大法宝 / 威科 / 无讼等任何第三方增值内容（商业库导出件即便含公共领域
   法条原文，其超链接/时效性标注等增值内容亦禁止复制）。
5. 所有输出附"不构成法律意见"横幅。
6. 关联查询仅对接用户本地自建、已核验来源的 verified-chinese-law-kb；绝不自动
   抓取第三方库。

命令：
  law fetch  --law <法名> --file <官方原文.txt> --source-url <官方URL> [--publisher ...] [--published-date ...] [--effective-date ...] [--version-tag ...] [--articles 1-5]
  law show     [<法名>.<条号>]         # 无参数则列出全部
  law verify                          # 校验本地数据是否被篡改
  law versions <法名.条号>             # 版本轴与差异对比
  law validity [法律名]                # 效力状态红黄绿
  law check   <法律名第X条>            # 最小引用校验
  law check-batch <文件>               # 批量校验文件中的法条引用（每行一条）
  law relate  <法名.条号> [--kb-path]  # 查询本地 verified-chinese-law-kb 关联线索

零依赖：仅用 Python 标准库。
"""
import argparse
import datetime
import difflib
import hashlib
import json
import re
import sys
import urllib.request
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "data" / "law_db.json"

DISCLAIMER = (
    "【法律免责】本工具仅整理公开法条原文，效力状态提示以官方发布为准，"
    "不构成法律意见，使用者须自行核实。"
)

CN_NUM = {
    "零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
    "六": 6, "七": 7, "八": 8, "九": 9,
}


def cn_to_int(s: str):
    """支持阿拉伯数字与中文数字（一~九十九）。"""
    if s.isdigit():
        return int(s)
    if s in CN_NUM:
        return CN_NUM[s]
    if "十" in s:
        parts = s.split("十")
        tens = parts[0]
        ones = parts[1] if len(parts) > 1 else ""
        t = CN_NUM.get(tens, 1) if tens else 1
        o = CN_NUM.get(ones, 0) if ones else 0
        return t * 10 + o
    return None


ART_RE = re.compile(r"第([一二三四五六七八九十百零0-9]+)条")

CHECK_RE = re.compile(r"^(?P<law>.+?)第(?P<art>\d+)条$")

# 批量校验用：容忍法律名与"第"之间的空白，且允许引用出现在行内任意位置
BATCH_RE = re.compile(r"(?P<law>.+?)\s*第\s*(?P<art>\d+)\s*条")


def segment(text: str):
    """将条文拆为可比对片段：优先按（一）（二）…分项，否则按中文句号分句。"""
    parts = re.split(r"(?=（[一二三四五六七八九十百]+）)", text)
    parts = [p for p in parts if p.strip()]
    if len(parts) <= 1:
        parts = [s + "。" for s in text.split("。") if s.strip()]
    return parts


def split_articles(text: str) -> dict:
    """按'第X条'切分官方原文，返回 {条号(阿拉伯): 条文全文}。

    健壮性（地方性法规试点暴露的问题）：条文内部常引用其他条文（如
    '依照本条例第五十二条规定'），naive 全量切分会产生伪条文。改进策略：
    1) 从首个'第1条'起算正文（跳过修订决定等前置引用，因其不出现'第1条'）；
    2) 仅接受与上一接受条文*连续*（prev+1）的'第X条'为边界，跳跃引用被跳过；
    3) 极少数"条文内恰引用下一序号"会先被临时接受、随后被真实条文覆盖
       （dict 后写胜出），不影响最终正确性。
    说明：本函数不依赖"引用前缀跳过"，以免误删真实条文而中断连续链。
    """
    matches = list(ART_RE.finditer(text))
    # 从首个'第1条'起算正文（跳过修订决定等前置引用，因其不出现'第1条'）
    start_idx = 0
    for i, m in enumerate(matches):
        if cn_to_int(m.group(1)) == 1:
            start_idx = i
            break
    # 第一遍：仅保留与上一接受条文*连续*（prev+1）的'第X条'构成"正文脊"。
    # 条文内的交叉引用（如"违反本条例第三十四条第一项"）序号不连续 → 被剔除，
    # 因此绝不会充当下一处边界，从而杜绝截断真实条文（旧实现用 matches[i+1] 会截断）。
    spine = []
    prev = 0
    for m in matches[start_idx:]:
        val = cn_to_int(m.group(1))
        if val is None:
            continue
        if val == prev + 1:
            spine.append((val, m.start()))
            prev = val
        # 不连续者跳过但继续向后扫描，使后续真实条文仍能接上连续链
    out = {}
    for j, (val, start) in enumerate(spine):
        end = spine[j + 1][1] if j + 1 < len(spine) else len(text)
        body = text[start:end].strip()
        # 去掉因边界落在下一章标题前而残留在条文尾部的"第X章/第X节"标题行
        lines = body.split("\n")
        while lines and re.match(r"^\s*第[一二三四五六七八九十百]+[章节]", lines[-1]):
            lines.pop()
        out[str(val)] = "\n".join(lines).strip()
    return out


def sha256(text: str) -> str:
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


def load_db() -> dict:
    if not DB_PATH.exists():
        return {"schema_version": 1, "records": []}
    return json.loads(DB_PATH.read_text(encoding="utf-8"))


def save_db(db: dict) -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    DB_PATH.write_text(
        json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def parse_range(spec: str):
    """'1-5' 或 '1,3,5' -> set of str。"""
    wanted = set()
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-")
            for n in range(int(a), int(b) + 1):
                wanted.add(str(n))
        else:
            wanted.add(str(int(part)))
    return wanted


def cmd_fetch(args: argparse.Namespace) -> None:
    text = Path(args.file).read_text(encoding="utf-8") if args.file else None

    # 合规 fetch：若启用 --try-online，仅对"用户提供的确切官方URL"做单次 GET，
    # 存为原始文件供人工核对，绝不自动解析第三方结构。
    if args.try_online and args.source_url and text is None:
        try:
            raw = urllib.request.urlopen(args.source_url, timeout=15).read()
        except Exception as e:  # noqa: BLE001
            print(f"[fetch] 在线获取失败（{e}）。请人工保存官方原文后改用 --file。", file=sys.stderr)
            sys.exit(2)
        tmp = Path(args.file or "official_raw.txt")
        tmp.write_bytes(raw)
        print(f"[fetch] 已下载官方原文至 {tmp}；请人工核对后重新运行 fetch --file {tmp}")
        return

    if text is None:
        print("[fetch] 错误：须提供 --file <官方原文>，或 --try-online 先下载。", file=sys.stderr)
        sys.exit(2)

    arts = split_articles(text)
    if args.articles:
        want = parse_range(args.articles)
        arts = {k: v for k, v in arts.items() if k in want}

    if not arts:
        print("[fetch] 未在原文中解析到任何'第X条'，请检查文件。", file=sys.stderr)
        sys.exit(2)

    db = load_db()
    existing = {(r["law"], r["article"], r["source"].get("version_tag", "")) for r in db["records"]}
    added = 0
    for art, body in sorted(arts.items(), key=lambda x: int(x[0])):
        if (args.law, art, args.version_tag or "") in existing:
            continue
        rec = {
            "law": args.law,
            "article": art,
            "text": body,
            "source": {
                "url": args.source_url or "",
                "publisher": args.publisher or "",
                "published_date": args.published_date or "",
                "effective_date": args.effective_date or "",
                "version_tag": args.version_tag or "",
                "retrieved_date": datetime.date.today().isoformat(),
            },
            "sha256": sha256(body),
            "disclaimer": DISCLAIMER,
        }
        db["records"].append(rec)
        added += 1

    save_db(db)
    print(f"[fetch] 成功写入 {added} 条；当前库共 {len(db['records'])} 条。")


def cmd_show(args: argparse.Namespace) -> None:
    db = load_db()
    if not db["records"]:
        print("[show] 本地库为空，请先运行 law fetch。")
        return

    if not args.query:
        for r in db["records"]:
            print(f"{r['law']}.{r['article']}  {r['text'][:28]}…")
        return

    law_part, _, art_part = args.query.partition(".")
    matches = [
        r
        for r in db["records"]
        if (art_part == "" or r["article"] == art_part) and (law_part in r["law"])
    ]
    if not matches:
        print("[show] 未找到匹配记录。", file=sys.stderr)
        sys.exit(3)

    for r in matches:
        s = r["source"]
        print(f"法条：{r['law']} 第{r['article']}条")
        print(f"版本：{s.get('version_tag', '')}")
        print(f"原文：{r['text']}")
        print(f"来源：{s.get('url', '')}")
        print(f"发布机关：{s.get('publisher', '')}  公布：{s.get('published_date', '')}  施行：{s.get('effective_date', '')}")
        print(f"检索日期：{s.get('retrieved_date', '')}")
        print(f"SHA-256：{r['sha256']}")
        print(r["disclaimer"])
        print("-" * 40)


def cmd_verify(args: argparse.Namespace) -> None:
    db = load_db()
    ok = bad = 0
    for r in db["records"]:
        if sha256(r["text"]) == r["sha256"]:
            ok += 1
        else:
            bad += 1
            print(f"[篡改] {r['law']}.{r['article']} 哈希不符（记录 {r['sha256'][:12]}…）")
    print(f"[verify] 完好 {ok} 条，被篡改 {bad} 条。")
    if bad:
        sys.exit(1)


def cmd_versions(args: argparse.Namespace) -> None:
    """版本轴：同一法条在各版本中的原文 + 差异对比（仅文本比对，不引第三方结论）。"""
    db = load_db()
    if not db["records"]:
        print("[versions] 本地库为空，请先运行 law fetch。")
        return
    law_part, _, art_part = args.query.partition(".")
    recs = [
        r
        for r in db["records"]
        if (art_part == "" or r["article"] == art_part) and (law_part in r["law"])
    ]
    if not recs:
        print("[versions] 未找到匹配记录。", file=sys.stderr)
        sys.exit(3)
    by_art: dict = {}
    for r in recs:
        by_art.setdefault(r["article"], []).append(r)
    for art, rs in sorted(by_art.items(), key=lambda x: int(x[0])):
        rs_sorted = sorted(rs, key=lambda r: r["source"].get("effective_date") or "")
        print(f"【{rs_sorted[0]['law']}】第{art}条 版本轴")
        print("-" * 40)
        prev = None
        for r in rs_sorted:
            s = r["source"]
            print(f"[{s.get('version_tag', '')}] (生效 {s.get('effective_date', '')})")
            print(r["text"])
            print()
            if prev is not None:
                diff = difflib.unified_diff(
                    segment(prev["text"]),
                    segment(r["text"]),
                    fromfile=prev["source"].get("version_tag", ""),
                    tofile=r["source"].get("version_tag", ""),
                    lineterm="",
                )
                lines = list(diff)
                if lines:
                    print("差异标注（仅文本比对，不引用任何第三方结论）:")
                    for ln in lines:
                        print(ln)
            prev = r
        print("=" * 40)


def cmd_validity(args: argparse.Namespace) -> None:
    """效力红黄绿：按 effective_date 与当前日期自行判断，非第三方标注。"""
    db = load_db()
    today = datetime.date.today()
    by_law: dict = {}
    seen_versions: set = set()
    for r in db["records"]:
        if args.law and args.law not in r["law"]:
            continue
        vkey = (r["law"], r["source"].get("version_tag", ""))
        if vkey in seen_versions:
            continue
        seen_versions.add(vkey)
        by_law.setdefault(r["law"], []).append(r)
    if not by_law:
        print("[validity] 未找到匹配记录。", file=sys.stderr)
        sys.exit(3)
    for law, rs in by_law.items():
        rs_sorted = sorted(rs, key=lambda r: r["source"].get("effective_date") or "0000-00-00")
        latest = rs_sorted[-1]
        print(f"【{law}】效力状态（自行基于官方原文比对，非第三方标注）")
        print("-" * 40)
        print(f"{'版本':<26}{'生效日期':<14}状态")
        for r in rs_sorted:
            s = r["source"]
            eff = s.get("effective_date", "")
            try:
                eff_d = datetime.date.fromisoformat(eff)
            except Exception:  # noqa: BLE001
                eff_d = None
            if eff_d and eff_d > today:
                status = "尚未施行（红）"
            elif r is latest:
                status = "现行有效（绿）"
            else:
                status = "已修订/已废止（黄）"
            print(f"{s.get('version_tag', ''):<26}{eff:<14}{status}")
        print("注：仅依据修订一般规则判断旧法被新法取代；特殊过渡条款需逐条核对官方公告。")
        print("=" * 40)


def cmd_check(args: argparse.Namespace) -> None:
    """最小引用校验：解析 '法律名第X条'，返回最新有效版本原文与状态。"""
    db = load_db()
    m = CHECK_RE.match(args.ref.strip())
    if not m:
        print("[check] 无法解析引用，格式应为 '法律名第X条'。", file=sys.stderr)
        sys.exit(3)
    law_q, art = m.group("law"), m.group("art")
    recs = [r for r in db["records"] if law_q in r["law"] and r["article"] == art]
    if not recs:
        print(f"[check] 引用不存在：{args.ref}（本地库未收录）", file=sys.stderr)
        sys.exit(3)
    latest = sorted(recs, key=lambda r: r["source"].get("effective_date") or "")[-1]
    s = latest["source"]
    print(f"【引用校验】{law_q}第{art}条")
    print("-" * 40)
    print(f"✓ 引用存在，当前有效版本为 {s.get('version_tag', '')}")
    print(latest["text"])
    print("-" * 40)
    print(f"来源：{s.get('url', '')} | 检索日期：{s.get('retrieved_date', '')} | SHA-256: {latest['sha256'][:12]}…")
    print(latest["disclaimer"])


def cmd_check_batch(args: argparse.Namespace) -> None:
    """批量校验：逐行扫描 '法律名第X条'（阿拉伯数字条号），复用 check 的匹配逻辑。
    可选 --kb-path 指向本地 verified-chinese-law-kb，匹配时一并提示关联线索。
    不访问任何外部源，仅基于本地 data/law_db.json（+ 可选本地 KB）。"""
    path = Path(args.file)
    if not path.exists():
        print(f"文件不存在: {args.file}", file=sys.stderr)
        sys.exit(2)
    text = path.read_text(encoding="utf-8")
    records = load_db()["records"]
    kb_items, kb_index = ([], {})
    if args.kb_path:
        kb_items, kb_index = load_kb(args.kb_path)
    total = matched = unmatched = parse_failed = 0
    print("【批量引用校验】")
    print("=" * 60)
    for line_no, line in enumerate(text.splitlines(), 1):
        m = BATCH_RE.search(line)
        if not m:
            # 仅当行"看起来像引用"（含 第/条/数字）但无法解析时才计入解析失败
            if ("第" in line) and ("条" in line) and any(c.isdigit() for c in line):
                parse_failed += 1
                print(f"行{line_no}: ✗ 解析失败（无法识别为「法律名第X条」）: {line.strip()[:40]}")
            continue
        total += 1
        law_q, art = m.group("law").strip(), m.group("art")
        # 法律名缺失（如行首直接"第5条…"）视为解析失败，避免 "" in r["law"] 误匹配全部
        if not law_q:
            total -= 1
            parse_failed += 1
            print(f"行{line_no}: ✗ 解析失败（法律名缺失）: {line.strip()[:40]}")
            continue
        # 必须同时匹配法律名与条号
        recs = [r for r in records if (law_q in r["law"]) and r["article"] == art]
        if not recs:
            unmatched += 1
            print(f"行{line_no}: ✗ 未匹配 {law_q}第{art}条")
            # 合规友好的交叉提示：本地库未收录，但本地 KB 含本条
            if kb_items:
                kb_code = _kb_resolve_law_code(law_q, kb_index)
                if kb_code is not None and any(_kb_record_law_code(it, kb_index) == kb_code
                       and _kb_record_article(it) == art for it in kb_items):
                    print(f"  （提示）本地库未收录，但本地 verified-chinese-law-kb 含本条，可运行: law relate {_kb_law_name(law_q)}.{art}")
            continue
        latest = sorted(recs, key=lambda r: r["source"].get("effective_date") or "")[-1]
        matched += 1
        print(f"行{line_no}: ✓ {law_q}第{art}条 → {latest['source'].get('version_tag', '')}")
        print(f"  {latest['text']}")
        print(f"  来源: {latest['source'].get('url', '')} | SHA-256: {latest['sha256'][:12]}…")
        # 可选：本地 KB 关联线索（仅展示已核验公开线索，不构成法律意见）
        if kb_items:
            kb_code = _kb_resolve_law_code(law_q, kb_index)
            kb_hit = None
            if kb_code is not None:
                for it in kb_items:
                    if _kb_record_law_code(it, kb_index) == kb_code and _kb_record_article(it) == art:
                        kb_hit = it
                        break
            if kb_hit:
                v = kb_hit.get("verified")
                v_str = "是" if v is True else ("否" if v is False else "未标注")
                print(f"  关联KB：verified-chinese-law-kb 含本条已核验原文（verified={v_str}，"
                      f"生效 {kb_hit.get('effective_date', '')}，来源 {kb_hit.get('source_url', '')}）")
            else:
                print("  关联KB：未在本法模块中找到对应条目")
        print("  [免责] 不构成法律意见")
        print("-" * 40)
    print("=" * 40)
    print(f"汇总: 引用 {total} 条 | 匹配 {matched} | 未匹配 {unmatched} | 解析失败 {parse_failed}")


# ---------- verified-chinese-law-kb 关联查询（适配真实仓库结构） ----------
# 真实仓库 layout：
#   knowledge_base/laws_index.json -> { law_code: {name, aliases:[...], source_url, ...} }
#   modules/<M>_<law>/statutes.jsonl -> 每行 { law_code, article_number:"第1条",
#       article_sort_key:int, content, effective_date, source_url,
#       source_accessed_at, verified, notes }
#   knowledge_base/SEED/*.json       -> 同结构 JSON 数组
# 兼容假设的 {items:[...]} 索引与单 jsonl。
def _kb_law_name(raw):
    """归一化法律名：去掉'中华人民共和国'前缀，便于匹配。"""
    if not raw:
        return ""
    return re.sub(r"^中华人民共和国", "", str(raw).strip())


def load_kb(kb_path_str: str):
    """加载本地 verified-chinese-law-kb。返回 (items, law_index)。
    不存在或无法解析则返回 ([], {})，不抛异常（保持合规边界：绝不自动抓取第三方库）。"""
    kb_path = Path(kb_path_str)
    items: list = []
    law_index: dict = {}
    try:
        if kb_path.is_dir():
            # laws_index.json 可能在仓库根或 knowledge_base/ 下
            for cand in (kb_path / "laws_index.json", kb_path / "knowledge_base" / "laws_index.json"):
                if cand.exists():
                    law_index = json.loads(cand.read_text(encoding="utf-8"))
                    break
            alt = kb_path / "index.json"  # 假设的索引结构
            if alt.exists():
                data = json.loads(alt.read_text(encoding="utf-8"))
                extra = data.get("items", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
                items.extend(extra)
            # SEED 数组（knowledge_base/SEED/*.json）—— 优先加载，使带 verified 标记的副本在去重中胜出
            for jf in sorted(kb_path.rglob("*/SEED/*.json")):
                try:
                    data = json.loads(jf.read_text(encoding="utf-8"))
                    if isinstance(data, list):
                        items.extend(data)
                    elif isinstance(data, dict):
                        items.extend(v for v in data.values() if isinstance(v, dict))
                except Exception:  # noqa: BLE001
                    continue
            # 精确按文件名扫描真实模块 statutes，避开 law-citation-bench/preds 等噪声
            for jf in sorted(kb_path.rglob("statutes.jsonl")):
                try:
                    for line in jf.read_text(encoding="utf-8").splitlines():
                        line = line.strip()
                        if line:
                            o = json.loads(line)
                            if isinstance(o, dict):
                                items.append(o)
                except Exception:  # noqa: BLE001
                    continue
        elif kb_path.exists():
            raw = kb_path.read_text(encoding="utf-8")
            if kb_path.suffix == ".jsonl":
                for line in raw.splitlines():
                    line = line.strip()
                    if line:
                        try:
                            items.append(json.loads(line))
                        except Exception:  # noqa: BLE001
                            continue
            else:
                data = json.loads(raw)
                items = data if isinstance(data, list) else data.get("items", [])
    except Exception:  # noqa: BLE001
        return [], {}
    return items, law_index


def _kb_record_law_code(item: dict, law_index: dict) -> str:
    """从单条记录解析 law_code；缺失时尝试用 name/alias 反查 laws_index。"""
    lc = item.get("law_code") or item.get("law") or item.get("law_code_name")
    if lc:
        return str(lc)
    nm = item.get("law_name") or item.get("name") or item.get("title") or ""
    if nm and law_index:
        nm_n = _kb_law_name(nm)
        for code, meta in law_index.items():
            if nm_n == _kb_law_name(meta.get("name", "")) or nm_n in [_kb_law_name(a) for a in (meta.get("aliases") or [])]:
                return code
    return ""


def _kb_record_article(item: dict) -> str:
    """从单条记录解析条号（阿拉伯数字）；优先 article_sort_key，否则剥离 article_number 非数字。"""
    if item.get("article_sort_key") is not None:
        return str(item["article_sort_key"])
    an = item.get("article_number") or item.get("article") or item.get("article_no") or ""
    return re.sub(r"\D", "", str(an)) if an else ""


def _kb_resolve_law_code(query_law: str, law_index: dict):
    """将用户查询的法律名（已归一化）解析为 law_code；无法解析返回 None。"""
    q = _kb_law_name(query_law)
    for code, meta in law_index.items():
        name_n = _kb_law_name(meta.get("name", ""))
        aliases_n = [_kb_law_name(a) for a in (meta.get("aliases") or [])]
        if q == name_n or q in aliases_n or q == code:
            return code
    return None


def cmd_relate(args: argparse.Namespace) -> None:
    """查询本地 KB 中与目标法条关联的线索；KB 不存在则给出合规提示。"""
    items, law_index = load_kb(args.kb_path)
    if not items:
        print("未找到本地 verified-chinese-law-kb，跳过关联查询。")
        print("（合规提示：本工具不自动抓取第三方库；请将官方来源数据置于 --kb-path 后再试。）")
        return 1
    if args.citation.count(".") != 1:
        print("格式错误，应为「法律名.条号」，如 公司法.1", file=sys.stderr)
        sys.exit(3)
    law_q, art = args.citation.split(".")
    code = _kb_resolve_law_code(law_q, law_index)
    same_law, hits, seen = 0, [], set()
    for it in items:
        lc = _kb_record_law_code(it, law_index)
        if not lc or (code is None or lc != code):
            continue
        same_law += 1
        if _kb_record_article(it) == art:
            key = (lc, it.get("article_number"))
            if key in seen:
                continue
            seen.add(key)
            hits.append(it)
    if not hits:
        scope = f"（同法记录 {same_law} 条）" if same_law else ""
        print(f"本地 KB 中未找到与 {_kb_law_name(law_q)}第{art}条 精确匹配的线索{scope}。")
        return 0
    print(f"【关联线索】{_kb_law_name(law_q)}第{art}条（来源：本地 verified-chinese-law-kb）")
    print("-" * 40)
    for h in hits:
        lc = _kb_record_law_code(h, law_index)
        meta = law_index.get(lc, {})
        content = (h.get("content") or "").replace("\n", " ")
        snippet = content[:48] + ("…" if len(content) > 48 else "")
        v = h.get("verified")
        v_str = "是" if v is True else ("否" if v is False else "未标注")
        print(f"- [{meta.get('name', lc)}] 条文 {h.get('article_number', '')}（verified={v_str}, 生效 {h.get('effective_date', '')}）")
        print(f"  原文摘要：{snippet}")
        if h.get("source_url"):
            print(f"  来源：{h['source_url']}（访问 {h.get('source_accessed_at', '')}）")
    print("=" * 40)
    print("【法律免责】以上仅为本地 KB 的公开线索索引，不构成法律意见，请核实原始来源。")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="law",
        description="法条速查器 · 数据合规 MVP（不构成法律意见）",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    f = sub.add_parser("fetch", help="记录官方原文并生成证据链")
    f.add_argument("--law", required=True, help="法律全称，如 中华人民共和国著作权法")
    f.add_argument("--file", help="官方原文文本文件路径（手动保存的官方版本）")
    f.add_argument("--source-url", help="官方来源 URL（建议国家法律法规数据库深链）")
    f.add_argument("--publisher", help="发布机关，如 全国人民代表大会常务委员会")
    f.add_argument("--published-date", help="公布日期 YYYY-MM-DD")
    f.add_argument("--effective-date", help="施行日期 YYYY-MM-DD")
    f.add_argument("--version-tag", help="版本标记，如 2020修正（第三次修正）")
    f.add_argument("--articles", help="仅导入指定条号，如 1-5 或 1,3,5")
    f.add_argument("--try-online", action="store_true", help="对用户提供的确切URL做单次GET并存为原始文件")
    f.set_defaults(func=cmd_fetch)

    s = sub.add_parser("show", help="显示条文 + 来源 + 哈希")
    s.add_argument("query", nargs="?", help="法名.条号，如 著作权法.1；留空列出全部")
    s.set_defaults(func=cmd_show)

    v = sub.add_parser("verify", help="校验本地数据完整性（防篡改）")
    v.set_defaults(func=cmd_verify)

    vs = sub.add_parser("versions", help="版本轴与差异对比（法名.条号）")
    vs.add_argument("query", help="法名.条号，如 著作权法.3")
    vs.set_defaults(func=cmd_versions)

    va = sub.add_parser("validity", help="效力状态红黄绿（按法律名）")
    va.add_argument("law", nargs="?", default="", help="法律名，留空匹配全部")
    va.set_defaults(func=cmd_validity)

    ck = sub.add_parser("check", help="最小引用校验（如 著作权法第5条）")
    ck.add_argument("ref", help="引用，如 著作权法第5条")
    ck.set_defaults(func=cmd_check)

    cb = sub.add_parser("check-batch", help="批量校验文件中的法条引用（每行一条）")
    cb.add_argument("file", help="包含引用的 UTF-8 文本文件路径")
    cb.add_argument("--kb-path", default=None,
                    help="可选：指向本地 verified-chinese-law-kb，批量校验时一并提示关联线索")
    cb.set_defaults(func=cmd_check_batch)

    rl = sub.add_parser("relate", help="查询本地 verified-chinese-law-kb 的关联线索")
    rl.add_argument("citation", help="法条编号，如 公司法.1")
    rl.add_argument("--kb-path", default="../verified-chinese-law-kb",
                    help="本地 KB 路径（目录或 json/jsonl；默认 ../verified-chinese-law-kb）")
    rl.set_defaults(func=cmd_relate)

    return p


def main(argv=None) -> None:
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
