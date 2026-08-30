#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""关闭 O1：用官方重新公布全文对账《上海市生活垃圾管理条例》2026 修正版。

用法：
  # 先放好官方重新公布全文（推荐来自 国家法律法规数据库 flk.npc.gov.cn 或
  # 上海市人民代表大会常务委员会公报 PDF），然后：
  python3 close_O1_shanghai_2026.py \
      --official seed/上海市生活垃圾管理条例_2026修正_重新公布全文.txt \
      --url https://flk.npc.gov.cn/... \
      --dry-run            # 仅报告，不写库
  python3 close_O1_shanghai_2026.py \
      --official seed/上海市生活垃圾管理条例_2026修正_重新公布全文.txt \
      --url https://flk.npc.gov.cn/...

行为：
  - 对 2026 修正版逐条与官方全文对账（逐字忽略空白）+ 条序校验。
  - 若「实质性差异」全部落在已知修正点 {1, 21, 37, 57}（即 amended_by 已覆盖），
    则视为对账通过：
      * 在 2026 版每条记录的 lineage 写入 reorganized_full_text_url 与
        reconciliation = {status:"full", official, checked, method}；
      * review_status 仍保持 pending（对账通过 ≠ 律师签署，发布闸门不变）。
  - 若有超出已知修正点的差异或条序不一致，则中止写入并提示人工复核（不污染 DB）。
  - 全程本地写盘，不 commit（合规闸门由用户+律师在 Mac 端执行）。

合规说明：
  - spcsc.sh.cn 实测已被体育直播站占用，不再是上海人大官方源，已从白名单移除；
    官方重新公布全文应取 flk.npc.gov.cn 或上海市人大公报（纸质/PDF）。
"""
import argparse
import datetime
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import law_cli  # noqa: E402

DB_PATH = law_cli.DB_PATH
LAW = "上海市生活垃圾管理条例"
KNOWN_AMEND_ARTS = {"1", "21", "37", "57"}  # 修正决定§十一 的全部效果


def main() -> None:
    ap = argparse.ArgumentParser(description="关闭 O1：上海生活垃圾条例 2026 版官方全文对账")
    ap.add_argument("--official", required=True, help="官方重新公布全文路径（单一法全文）")
    ap.add_argument("--url", help="官方重新公布全文的 canonical URL（写入 lineage.reorganized_full_text_url）")
    ap.add_argument("--dry-run", action="store_true", help="仅报告，不写库")
    args = ap.parse_args()

    if not Path(args.official).exists():
        print(f"[close_O1] 官方全文未就位：{args.official}", file=sys.stderr)
        sys.exit(2)

    db = law_cli.load_db()
    off = law_cli._split_official(args.official)
    recs = [r for r in db["records"] if r["law"] == LAW]
    if not recs:
        print(f"[close_O1] DB 中无 {LAW} 记录", file=sys.stderr)
        sys.exit(2)

    vtags = {r["source"].get("version_tag", "") for r in recs}
    print(f"[close_O1] DB 中 {LAW} 版本：{sorted(vtags)}")
    print(f"[close_O1] 官方全文条数：{len(off)}")

    # 仅对 2026 修正版做对账（基线版对应 2019 原文，不在本次 O1 范围）
    v2026 = next((v for v in vtags if "2026" in v), None)
    if not v2026:
        print("[close_O1] 未找到 2026 修正版记录", file=sys.stderr)
        sys.exit(2)

    recs26 = [r for r in recs if r["source"].get("version_tag", "") == v2026]
    unexpected = []
    for r in recs26:
        art = r["article"]
        off_body = off.get(art)
        if off_body is None:
            unexpected.append(f"第{art}条 官方缺")
            continue
        db_norm = re.sub(r"\s+", "", r["text"])
        off_norm = re.sub(r"\s+", "", off_body)
        if db_norm != off_norm and art not in KNOWN_AMEND_ARTS:
            unexpected.append(f"第{art}条 超出已知修正点")

    # 条序校验（仅当条号集合一致）
    off_order = list(off.keys())
    db_order = [r["article"] for r in recs26]
    order_bad = (set(db_order) == set(off_order)) and (db_order != off_order)

    print(f"[close_O1] 超出已知修正点的差异：{unexpected if unexpected else '无'}")
    print(f"[close_O1] 条序不一致：{order_bad}")

    if unexpected or order_bad:
        print("[close_O1] ❌ 存在无法由修正决定解释的差异/条序变化，中止写入。"
              "请人工复核官方源是否确为 2026 重新公布全文，或将新增差异补入 KNOWN_AMEND_ARTS 并说明理由。")
        sys.exit(3)

    # 对账通过（差异全部落在已知修正点内）
    if args.dry_run:
        print(f"[close_O1] --dry-run：将对 {len(recs26)} 条 2026 版记录写入 "
              f"reorganized_full_text_url{'（' + args.url + '）' if args.url else ''} 与 reconciliation=full。"
              "（不写库）")
        return

    today = datetime.date.today().isoformat()
    for r in recs26:
        ln = r.setdefault("lineage", {})
        if args.url:
            ln["reorganized_full_text_url"] = args.url
        ln["reconciliation"] = {
            "status": "full",
            "official": args.url or args.official,
            "checked": today,
            "method": "逐字对账(忽略空白) + 条序校验；差异均落在修正决定§十一已知修正点",
        }
    DB_PATH.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[close_O1] ✅ 已对 {len(recs26)} 条 2026 版记录写入 lineage "
          f"(reorganized_full_text_url + reconciliation=full)。review_status 仍 pending，待律师签署。")
    print("[close_O1] 本地写盘完成，未 commit。发布前仍须律师复核 → 用户 Mac 端 commit → law verify --gate。")


if __name__ == "__main__":
    main()
