#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ingest_baseline_shanghai_2019.py — 将 2019 基线作为独立 lineage 版本入库（本地，不 commit）

背景（诊断文档 §7 + 本轮核实）：
  上海生活垃圾条例的 lineage 目前只有「2026 修正版」（65 条）。修订谱系需要一个
  明确的**基点**才完整：没有 2019 基线，版本轴无法表达"2026 版由 2019 版经某决定修正"。
  本脚本把《上海市生活垃圾管理条例》2019 原版（57 章 10 章，2019-07-01 施行）作为
  独立版本录入，与现有 2026 版构成完整 lineage：

      2019 基线 (baseline) --(2026修正决定)--> 2026 修正版

关键诚实结论（本轮已核实，非假设）：
  用 law_cli.split_articles 解析 2019 备份种子，得 65 条、零章标题残留；
  2026 DB vs 2019 基线 仅 4 处差异（第1条全局术语替换 + 第21/37/57条特定修订）
  = 修正决定的**全部**效果。故 2019 基线本身内容即官方原文，可直接作为对照基准。

做法（只新增、不改既有 2026 版条文/元数据；不碰任何 textual correctness）：
  - 解析 seed/上海市生活垃圾管理条例_2019通过_全文_官方原文_备份2019版.txt
  - 逐条生成记录：version_tag=2019年通过（2019-07-01施行），source 指向官方嘉定 PDF
  - lineage：
      baseline_version_tag = 自身（基点，无前驱）
      baseline_source_url  = 官方嘉定 PDF（公共领域，合法）
      amended_by           = 2026 修正决定（向后指向 2026 版，构成完整谱系）
      amended_by_source    = 注明用户提供为 wkinfo 导出件、§十一为官方修正案文、非 canonical
      reorganized_full_text_url = ""（基线是原版，无"重新公布"概念；该字段仅 2026 版用）
      effective_date       = 2019-07-01
      reconciliation       = partial（内容系官方嘉定PDF转录，未经逐字核对/律师签署，归为 partial）
  - review_status = pending（发布闸门仍闭；须律师签署 + law verify --gate）

合规：不 commit/push；运行后请 git diff 复核，由用户 Mac 端 commit + 律师签署。

用法：
  python3 ingest_baseline_shanghai_2019.py            # 执行入库
  python3 ingest_baseline_shanghai_2019.py --dry-run  # 仅报告计数，不写回
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import law_cli  # noqa: E402

DB_PATH = law_cli.DB_PATH
SEED_PATH = (
    Path(__file__).resolve().parent
    / "seed"
    / "上海市生活垃圾管理条例_2019通过_全文_官方原文_备份2019版.txt"
)

LAW = "上海市生活垃圾管理条例"
VERSION_TAG_2019 = "2019年通过（2019-07-01施行）"
BASELINE_URL = (
    "https://www.jiading.gov.cn/upload/lvrong/infopublicity/"
    "publicinformation/file/201910111009042259.pdf"
)
PUBLISHER = "上海市人民代表大会常务委员会"
PUBLISHED_DATE = "2019-01-31"
EFFECTIVE_DATE = "2019-07-01"

AMENDMENT_NAME = (
    "上海市人民代表大会常务委员会关于修改"
    "《上海市环境保护条例》等12件地方性法规的决定"
    "（2026-07-29 通过，2026-08-15 施行）"
)


def ingest(db: dict, dry: bool) -> int:
    if not SEED_PATH.exists():
        print(f"[ingest] 种子缺失：{SEED_PATH}", file=sys.stderr)
        sys.exit(2)
    text = SEED_PATH.read_text(encoding="utf-8")
    arts = law_cli.split_articles(text)
    print(f"[ingest] split_articles 解析 2019 基线得 {len(arts)} 条。")

    existing = {
        (r["law"], r["article"], r["source"].get("version_tag", ""))
        for r in db["records"]
    }
    added = skipped = 0
    for art, body in sorted(arts.items(), key=lambda x: int(x[0])):
        if (LAW, art, VERSION_TAG_2019) in existing:
            skipped += 1
            continue
        if dry:
            added += 1
            continue
        rec = {
            "law": LAW,
            "article": art,
            "text": body,
            "source": {
                "url": BASELINE_URL,
                "publisher": PUBLISHER,
                "published_date": PUBLISHED_DATE,
                "effective_date": EFFECTIVE_DATE,
                "version_tag": VERSION_TAG_2019,
                "retrieved_date": law_cli.datetime.date.today().isoformat(),
            },
            "lineage": {
                "baseline_version_tag": VERSION_TAG_2019,  # 基点：自身无前驱
                "baseline_source_url": BASELINE_URL,
                "amended_by": AMENDMENT_NAME,  # 向后指向 2026 版，构成完整谱系
                "amended_by_source": (
                    "用户提供 2026 修正决定官方原文（wkinfo 导出件）；"
                    "其 §十一 为官方修正案文，diff 可信，但非 canonical URL"
                ),
                "reorganized_full_text_url": "",  # 基线是原版，无"重新公布"概念
                "effective_date": EFFECTIVE_DATE,
                "reconciliation": {
                    "official_text_sha256": "",
                    "status": "partial",  # 内容系官方嘉定PDF转录，未经逐字核对/律师签署
                    "verified_by": "",
                    "verified_at": "",
                    "note": "2019原版基线，源自官方嘉定PDF；2026版由其经修正决定产生",
                },
            },
            "review_status": "pending",  # 发布闸门仍闭
            "reviewed_by": "",
            "review_date": "",
            "sha256": law_cli.sha256(body),
            "disclaimer": law_cli.DISCLAIMER,
        }
        db["records"].append(rec)
        added += 1
    return added, skipped


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="仅报告计数，不写回")
    args = ap.parse_args()

    db = law_cli.migrate_db(law_cli.json.loads(DB_PATH.read_text(encoding="utf-8")))
    added, skipped = ingest(db, dry=args.dry_run)
    print(f"[ingest] 拟新增 {added} 条（已存在跳过 {skipped} 条）。")
    if args.dry_run:
        print("[ingest] dry-run 完成，未写回。")
        return
    law_cli.save_db(db)
    print(f"[ingest] 已写回 {DB_PATH}（schema_version={db.get('schema_version')}）。")
    print("[ingest] 下一步：git diff data/law_db.json 复核 → 律师签署 → 用户 commit → law verify --gate。")


if __name__ == "__main__":
    main()
