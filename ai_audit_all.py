#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ai_audit_all.py — 用官方源逐字对账，将全库记录标记为「AI 审核通过」(ai_verified)

口径（用户明确 2026-08-28）：律师无需人工签署；AI 审核即终核。
本工具全部记录均有可对账的官方源（用户提供 / 本地官方全文种子）。

官方源映射（按 law + version_tag 关键字选择）：
  - 上海市生活垃圾管理条例
        2019 基线(tag 含 2019 不含2026) → B=上海市生活垃圾管理条例_2019通过_全文_官方原文_备份2019版.txt（真·2019 原文）
        2026 修正版(tag 含 2026)         → A=上海市生活垃圾管理条例_2019通过_全文_官方原文.txt（实为 2026 修正全文，含§十一4处修订）
  - 北京市生活垃圾管理条例（2020 修正）→ 北京市生活垃圾管理条例_2020修正_全文_官方原文.txt
  - 中华人民共和国著作权法
        2020 修正 → 著作权法_总则_第1-5条_官方原文.txt
        2010 修正 → 著作权法_2010修正_第1-5条_官方原文.txt

对账与标记（只改 review_status/lineage.reconciliation，必要时以官方源补全被截断文本并重算 sha256）：
  - DB 文本 whitespace-normalize 后与官方源逐条一致 → ai_verified + reconciliation=verified。
  - DB 文本是官方源文本的严格前缀（截断） → 以官方源补全文本、重算 sha256，标 ai_verified + 注明「AI审核修复截断」。
  - 其余内容不一致 → 保留 pending 并打印清单，绝不静默放行。

红线变化：不再要求律师签署；ai_verified 即视为已审核通过（verify --gate 已相应调整）。

用法：
  python3 ai_audit_all.py --dry-run   # 仅报告，不写回
  python3 ai_audit_all.py             # 执行标记/修复并写回
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import law_cli  # noqa: E402

DB_PATH = law_cli.DB_PATH
SEED = Path(__file__).resolve().parent / "seed"


def norm(s: str) -> str:
    return re.sub(r"\s+", "", s)


def load_official(path: Path) -> dict:
    return law_cli.split_articles(path.read_text(encoding="utf-8"))


def official_path_for(law: str, tag: str) -> Path:
    if law == "上海市生活垃圾管理条例":
        if "2026" in tag:
            return SEED / "上海市生活垃圾管理条例_2019通过_全文_官方原文.txt"  # A=修正全文
        return SEED / "上海市生活垃圾管理条例_2019通过_全文_官方原文_备份2019版.txt"  # B=真2019
    if law == "北京市生活垃圾管理条例":
        return SEED / "北京市生活垃圾管理条例_2020修正_全文_官方原文.txt"
    if law == "中华人民共和国著作权法":
        if "2020" in tag:
            return SEED / "著作权法_总则_第1-5条_官方原文.txt"
        return SEED / "著作权法_2010修正_第1-5条_官方原文.txt"
    return None


def audit(db: dict, dry: bool):
    today = law_cli.datetime.date.today().isoformat()
    stats = {}
    total_match = total_repaired = total_flag = 0
    for law in {r["law"] for r in db["records"]}:
        m = rep = f = 0
        recs = [r for r in db["records"] if r["law"] == law]
        # 按 version 分组取官方源（同一 law 可能多版本）
        for r in recs:
            tag = r["source"].get("version_tag", "")
            opath = official_path_for(law, tag)
            if opath is None or not opath.exists():
                f += 1
                print(f"  [FLAG] {law}.{r['article']} 无可用官方源 {opath}")
                continue
            off = load_official(opath)
            key = r["article"]
            off_body = off.get(key)
            if off_body is None:
                f += 1
                print(f"  [FLAG] {law}.{r['article']} 官方源无此条号（DB有官方缺）")
                continue
            dbn = norm(r["text"])
            on = norm(off_body)
            if dbn == on:
                if not dry:
                    _mark(r, today, "AI审核(逐字对账官方源)",
                          f"DB文本与官方源逐字一致(忽略空白);源={opath.name}")
                m += 1
            elif dbn and on.startswith(dbn) and len(dbn) < len(on):
                # DB 是被截断的前缀 → 以官方源补全（安全：官方为权威完整版）
                if not dry:
                    r["text"] = off_body
                    r["sha256"] = law_cli.sha256(off_body)
                    _mark(r, today, "AI审核(逐字对账官方源+修复截断)",
                          f"DB文本为官方源前缀被截断，已补全;源={opath.name}")
                rep += 1
            else:
                f += 1
                print(f"  [FLAG] {law}.{r['article']}({tag}) 内容不一致 "
                      f"DB前15={r['text'][:15]!r} 官方前15={off_body[:15]!r}")
        stats[law] = (m, rep, f)
        total_match += m
        total_repaired += rep
        total_flag += f
    return total_match, total_repaired, total_flag, stats


def _mark(r: dict, today: str, by: str, note: str) -> None:
    r["review_status"] = "ai_verified"
    r["reviewed_by"] = by
    r["review_date"] = today
    ln = r.setdefault("lineage", {})
    ln["reconciliation"] = {
        "official_text_sha256": "",
        "status": "verified",
        "verified_by": by,
        "verified_at": today,
        "note": note,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="仅报告，不写回")
    args = ap.parse_args()

    db = law_cli.migrate_db(law_cli.json.loads(DB_PATH.read_text(encoding="utf-8")))
    m, rep, f, stats = audit(db, dry=args.dry_run)
    print("=== 逐法结果（一致 / 修复截断 / 不一致）===")
    for law, (mm, rr, ff) in stats.items():
        print(f"  {law}: 一致 {mm} | 修复截断 {rr} | 不一致 {ff}")
    print(f"汇总: 一致 {m} | 修复截断 {rep} | 不一致 {f}")
    if args.dry_run:
        print("[audit] dry-run 完成，未写回。")
        return
    law_cli.save_db(db)
    print(f"[audit] 已写回 {DB_PATH}（schema_version={db.get('schema_version')}）。")
    if f:
        print(f"[audit] 仍有 {f} 条内容不一致（保留 pending），需人工核查。")


if __name__ == "__main__":
    main()
