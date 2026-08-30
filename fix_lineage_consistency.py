#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_lineage_consistency.py — 修复 lineage 一致性（本地，不 commit）

问题（本轮端到端审查发现，非假设）：
  A1. 上海 2026 修正版 65 条的 lineage.baseline_version_tag = "2019通过（公告第11号）"，
      但真实的 2019 基线记录 version_tag = "2019年通过（2019-07-01施行）"。
      指针对不上，谱系无法解析。修正为与基线真实 tag 完全一致。
  A2. 2019 基线 65 条 lineage.reconciliation.status = "verified"，属过度陈述
      （内容系官方嘉定 PDF 转录，未经逐字核对/律师签署）。改为 "partial"，与其他版本口径一致。

本脚本只动 lineage 字段，绝不碰 review_status / text / sha256。
不会覆盖 mark_ai_verified_shanghai2026.py 已标记的 ai_verified。

用法：
  python3 fix_lineage_consistency.py            # 执行并写回
  python3 fix_lineage_consistency.py --dry-run  # 仅报告，不写回
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import law_cli  # noqa: E402

DB_PATH = law_cli.DB_PATH
BASELINE_TAG = "2019年通过（2019-07-01施行）"


def fix(db: dict, dry: bool) -> tuple[int, int]:
    n_a1 = n_a2 = 0
    for r in db["records"]:
        if r["law"] != "上海市生活垃圾管理条例":
            continue
        ln = r.get("lineage") or {}
        tag = r["source"].get("version_tag", "")
        if "2026" in tag:
            # A1: 2026 版基线指针必须指向真实存在的基线 tag
            if ln.get("baseline_version_tag") != BASELINE_TAG:
                n_a1 += 1
                if not dry:
                    ln["baseline_version_tag"] = BASELINE_TAG
        else:
            # A2: 2019 基线 reconciliation 不许过度陈述
            rec = ln.get("reconciliation") or {}
            if rec.get("status") == "verified":
                n_a2 += 1
                if not dry:
                    ln["reconciliation"] = {
                        "official_text_sha256": "",
                        "status": "partial",
                        "verified_by": "",
                        "verified_at": "",
                        "note": "转录自官方嘉定PDF；未经逐字核对/律师签署，归为 partial",
                    }
    return n_a1, n_a2


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="仅报告，不写回")
    args = ap.parse_args()

    db = law_cli.migrate_db(law_cli.json.loads(DB_PATH.read_text(encoding="utf-8")))
    n_a1, n_a2 = fix(db, dry=args.dry_run)
    print(f"[fix] A1 2026基线指针待修正: {n_a1} 条 | A2 基线reconciliation待修正: {n_a2} 条")
    if args.dry_run:
        print("[fix] dry-run 完成，未写回。")
        return
    law_cli.save_db(db)
    print(f"[fix] 已写回 {DB_PATH}（schema_version={db.get('schema_version')}）。")


if __name__ == "__main__":
    main()
