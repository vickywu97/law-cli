#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mark_ai_verified_shanghai2026.py
将《上海市生活垃圾管理条例》2026 修正版（65 条）标记 review_status = ai_verified。

合规红线：
- 仅做 AI 机械核对标记；绝不写 review_status = verified（那是律师签署后的状态）。
- 仅改 review_status / reviewed_by / review_date 三个字段；不触碰 text / sha256 / 证据链 / lineage（除保留 reconciliation=partial）。
- 仅作用于 source.version_tag 含「2026年修正」的 65 条；2019 基线（65 条）不动。

运行前务必已备份 data/law_db.json。
"""
import json
import datetime

DB_PATH = "data/law_db.json"
TODAY = datetime.date.today().isoformat()  # 实际核对完成日
REVIEW_BY = "AI核对(law-cli verify --reconcile 逐字对账 + 决定§十一逐项比对)"
TARGET_VERSION = "2019年通过，2026年修正（2026年8月15日施行）"


def main():
    db = json.load(open(DB_PATH, encoding="utf-8"))
    recs = db["records"]
    marked = 0
    for r in recs:
        if r.get("law") == "上海市生活垃圾管理条例" and r.get("source", {}).get("version_tag") == TARGET_VERSION:
            assert r.get("review_status") in (None, "", "pending"), \
                f"非预期状态 {r.get('review_status')} @ {r.get('law')}.{r.get('article')}"
            r["review_status"] = "ai_verified"
            r["reviewed_by"] = REVIEW_BY
            r["review_date"] = TODAY
            # 保留 lineage.reconciliation.status = partial（O1 官方重新公布全文尚未取得）
            marked += 1
    db["records"] = recs
    json.dump(db, open(DB_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"已标记 ai_verified 条数: {marked}")
    print(f"review_date = {TODAY}")
    print("注意：2019 基线 65 条未改动；reconciliation 仍为 partial（O1 残余）。")


if __name__ == "__main__":
    main()
