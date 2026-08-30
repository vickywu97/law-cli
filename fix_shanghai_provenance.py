#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_shanghai_provenance.py — 修复 P0-2：上海 2026 修正版证据链元数据错误（本地，不 commit）

问题（诊断文档 P0-2）：
  law_db.json 中 65 条「上海市生活垃圾管理条例 | 2019年通过，2026年修正」的
  version_tag 标 2026，但 source.url 指向 2019 嘉定区 PDF、published_date=2019-01-31、
  effective_date=2019-07-01 —— 即把 2026 修正后的条文归因于 2019 来源+2019 日期。
  evidence chain 张冠李戴，对律师工具属证据链属性错误。

本脚本做的事（只改元数据 lineage + source 日期/url，不改条文文本）：
  1) 跑 migrate_db（schema v1->v2，确保 lineage/review 字段存在）；
  2) 对 65 条上海 2026 版：
       - source.effective_date  -> 2026-08-15（修正版施行日，不再沿用 2019）
       - source.published_date  -> 2026-07-29（修正决定通过日）
       - source.url             -> ""（修正版尚无独立 canonical URL，移入 lineage）
       - lineage.baseline_version_tag / baseline_source_url -> 2019 基线（嘉定官方 PDF，合法）
       - lineage.amended_by / amended_by_source -> 2026 修正决定（注明 wkinfo 导出件非 canonical）
       - lineage.reorganized_full_text_url -> 待补（上海人大公报 spcsc.sh.cn 深链，彻底关闭 O1）
       - lineage.effective_date -> 2026-08-15
       - lineage.reconciliation -> status=partial（4处已核，61条基线待官方全文）
       - review_status 保持 pending（须律师复核签署）

合规：本脚本只改元数据、不改条文，且**不 commit/push**。运行后请用
  git diff data/law_db.json
复核，确认无误后由用户在 Mac 端 commit；发布前须律师复核 + `law verify --gate` 通过。

用法：
  python3 fix_shanghai_provenance.py            # 执行修复并写回
  python3 fix_shanghai_provenance.py --dry-run  # 仅报告将要改什么，不写回
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import law_cli  # noqa: E402

DB_PATH = law_cli.DB_PATH

AMENDMENT_NAME = ("上海市人民代表大会常务委员会关于修改"
                  "《上海市环境保护条例》等12件地方性法规的决定"
                  "（2026-07-29 通过，2026-08-15 施行）")
BASELINE_URL = ("https://www.jiading.gov.cn/upload/lvrong/infopublicity/"
                "publicinformation/file/201910111009042259.pdf")


def fix(db: dict, dry: bool) -> int:
    n = 0
    for r in db["records"]:
        if r["law"] != "上海市生活垃圾管理条例":
            continue
        if "2026" not in r["source"].get("version_tag", ""):
            continue
        n += 1
        s = r["source"]
        ln = r.setdefault("lineage", {})
        if not dry:
            s["published_date"] = "2026-07-29"
            s["effective_date"] = "2026-08-15"
            s["url"] = ""
            ln["baseline_version_tag"] = "2019年通过（2019-07-01施行）"
            ln["baseline_source_url"] = BASELINE_URL
            ln["amended_by"] = AMENDMENT_NAME
            ln["amended_by_source"] = ("用户提供修正决定官方原文（wkinfo 导出件）；"
                                       "其 §十一 为官方修正案文，diff 可信，但非 canonical URL，"
                                       "禁止作为 source-url 写入")
            ln["reorganized_full_text_url"] = ("（待补：上海市人大公报 spcsc.sh.cn 重新公布全文深链，"
                                               "用于彻底关闭 O1）")
            ln["effective_date"] = "2026-08-15"
            ln["reconciliation"] = {
                "official_text_sha256": "",
                "status": "partial",
                "verified_by": "",
                "verified_at": "",
                "note": "4处修正案文已据修正决定核验；61条2019基线待官方重新公布全文复核（O1）",
            }
            r["review_status"] = "pending"
        else:
            print(f"[dry-run] {r['law']}.{r['article']}: "
                  f"published {s.get('published_date')}->2026-07-29, "
                  f"effective {s.get('effective_date')}->2026-08-15, "
                  f"url->''（移入 lineage.baseline_source_url）")
    return n


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="仅报告，不写回")
    args = ap.parse_args()

    db = law_cli.migrate_db(law_cli.json.loads(DB_PATH.read_text(encoding="utf-8")))
    count = fix(db, dry=args.dry_run)
    print(f"[fix] 命中上海 2026 版记录 {count} 条。")
    if args.dry_run:
        print("[fix] dry-run 完成，未写回。")
        return
    law_cli.save_db(db)
    print(f"[fix] 已写回 {DB_PATH}（schema_version={db.get('schema_version')}）。")
    print("[fix] 下一步：git diff data/law_db.json 复核 → 律师签署 → 用户 commit → law verify --gate。")


if __name__ == "__main__":
    main()
