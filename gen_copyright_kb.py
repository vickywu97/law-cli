#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_copyright_kb.py — 将 law-cli 本地库中的《著作权法》10 条（2010+2020 各 5 条）
增量写入真实 KB：verified-chinese-law-kb。

仅做「增量新增」，绝不修改 M1–M8 任何既有数据：
  - 新建 modules/M9_copyright_law/{statutes.jsonl, verifications.json, README.md, CHANGELOG.md}
  - 新建 knowledge_base/SEED/copyright_law.json
  - laws_index.json 仅追加 COPYRIGHT_LAW 键（若存在则跳过）
  - catalog.json 仅追加 M9 条目（若存在则跳过）

合规：法条原文属公共领域（著作权法第五条），来源均为官方
（2010=国家新闻出版署 nppa.gov.cn；2020=国家法律法规数据库 flk.npc.gov.cn，
B3 决议用裸首页而非搜索页）。零商业库污染。

用法：
  python3 gen_copyright_kb.py            # 执行写入
  python3 gen_copyright_kb.py --dry-run  # 仅打印将写入的内容，不落盘
"""

import json
import os
import sys

LOCAL_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "law_db.json")
KB_ROOT = "/Users/vickywu/WorkBuddy/2026-08-07-00-27-56/verified-chinese-law-kb"
LAW_CODE = "COPYRIGHT_LAW"
VERIFIED_BY = "Vicky Wu (律师/税务师/专利代理师)"
VERIFIED_AT = "2026-08-18"          # 实际核验/写入日
SOURCE_ACCESSED_AT = "2026-08-14"   # 本地库记录的源访问日
FLK_2020_URL = "https://flk.npc.gov.cn/"  # B3 决议：裸首页，非 search 页

STATUTE_FIELDS = [
    "id", "law_code", "article_number", "article_sort_key", "content",
    "effective_date", "revision_of", "verification_status", "verified_at",
    "verified_by", "source_url", "source_accessed_at", "notes",
]
SEED_FIELDS = [
    "law_code", "article_number", "article_sort_key", "content",
    "effective_date", "revision_of", "source_url", "source_accessed_at",
    "verified", "notes",
]


def load_local():
    db = json.load(open(LOCAL_DB, encoding="utf-8"))
    recs = [r for r in db["records"] if "著作权法" in r["law"]]
    if len(recs) != 10:
        raise SystemExit(f"[ERR] 期望 10 条著作权法记录，实得 {len(recs)}")
    out_2010, out_2020 = [], []
    for r in recs:
        tag = (r.get("source") or {}).get("version_tag", "")
        if "2010" in tag:
            out_2010.append(r)
        elif "2020" in tag:
            out_2020.append(r)
        else:
            raise SystemExit(f"[ERR] 无法识别版本: {tag!r} (article={r['article']})")
    if len(out_2010) != 5 or len(out_2020) != 5:
        raise SystemExit(f"[ERR] 版本分组异常: 2010={len(out_2010)} 2020={len(out_2020)}")
    return out_2010, out_2020


def build(version_recs, version_label):
    """version_label: 'v2010' / 'v2020'；返回 statutes / seed / verifications 三份数据。"""
    statutes, seeds, ledger = [], [], {}
    for r in version_recs:
        n = int(r["article"])
        src = r["source"]
        if version_label == "v2010":
            eff = src["effective_date"]            # 2010-04-01
            url = src["url"]                        # nppa.gov.cn 官方
            revision_of = None
            src_name = "国家新闻出版署（nppa.gov.cn）"
        else:
            eff = src["effective_date"]            # 2021-06-01
            url = FLK_2020_URL                      # B3：裸首页
            revision_of = f"{LAW_CODE}_{n}_v2010"
            src_name = "国家法律法规数据库（flk.npc.gov.cn）"
        rid = f"{LAW_CODE}_{n}_{version_label}"
        art_num = f"第{n}条"

        st = {
            "id": rid,
            "law_code": LAW_CODE,
            "article_number": art_num,
            "article_sort_key": n,
            "content": r["text"],
            "effective_date": eff,
            "revision_of": revision_of,
            "verification_status": "verified",
            "verified_at": VERIFIED_AT,
            "verified_by": VERIFIED_BY,
            "source_url": url,
            "source_accessed_at": SOURCE_ACCESSED_AT,
            "notes": "",
        }
        statutes.append(st)
        seeds.append({
            "law_code": LAW_CODE,
            "article_number": art_num,
            "article_sort_key": n,
            "content": r["text"],
            "effective_date": eff,
            "revision_of": revision_of,
            "source_url": url,
            "source_accessed_at": SOURCE_ACCESSED_AT,
            "verified": True,
            "notes": "",
        })
        ledger[rid] = {
            "status": "verified",
            "verified_at": VERIFIED_AT,
            "source": src_name,
            "notes": "",
            "verified_by": VERIFIED_BY,
        }
    return statutes, seeds, ledger


def module_readme():
    return f"""# M9 · 中华人民共和国著作权法

> 模块化法条知识库子模块。**每一条条文均为已核验原文**，来源为官方公报 / 官方数据库。
> 本模块遵循「自 M3 起新模块不具名签署」约定之外的例外：因用户（执业律师）为核验人，
> 保留具名签署字段 `verified_by`（与 M1 首发特例不同，本模块为著作权法专题、经用户显式要求署名）。

## 法律基本信息

| 项目 | 内容 |
|------|------|
| 法律名称 | 中华人民共和国著作权法 |
| 2020 修正 | 2020-11-11 通过（主席令第六十二号），2021-06-01 施行（第三次修正） |
| 2010 修正 | 2010-02-26 通过（主席令第二十六号），2010-04-01 施行（第二次修正） |
| 本模块已核验 | 10 条（2010 版 5 条 + 2020 版 5 条，均 complete / verified） |
| law_code | `{LAW_CODE}` |

## 条文统计

本模块仅收录**总则第 1–5 条**的两版对照（2010 修正 + 2020 修正），非完整法典。
条文连续编号第 1 条至第 5 条，两版各 5 条，`verification_status` 均为 `verified`。

## 数据格式

`statutes.jsonl` 每行一个 JSON 对象，字段顺序见仓库核心 schema（13 字段）。
配套 `verifications.json` 以条文 ID 为键，记录 `status / verified_at / source / verified_by / notes`。

## 核验说明

- 法条原文逐条比对官方来源：2010 版来自国家新闻出版署（nppa.gov.cn）；2020 版来自国家法律法规数据库（flk.npc.gov.cn）。
- 本法第五条明确「法律、法规…」不适用著作权法保护，故法条原文本身属公共领域，可合法整理使用；
  但任何商业库（北大法宝 / 威科等）的加工内容（编注、效力标注、案例关联）受版权保护，本模块不含。

## 已知局限

- 本模块为**内部自用**状态：仅含总则第 1–5 条，未发布、未计入公开 release。
- 如后续要扩至全文，须逐条比对官方重新公布文本并在 `CHANGELOG.md` 与 `catalog.json` 版本轴标注。
"""


def module_changelog():
    return f"""# M9_copyright_law 变更日志

## internal (2026-08-18)
- 初始内部新增：收录《中华人民共和国著作权法》总则第 1–5 条，含 2010 修正 + 2020 修正两版，共 10 条已核验条文。
- 来源：2010 版 = 国家新闻出版署（nppa.gov.cn）；2020 版 = 国家法律法规数据库（flk.npc.gov.cn，B3 决议用裸首页）。
- 保留具名签署 `verified_by`（用户即核验律师，显式要求署名）。
- 状态：`internal`（未发布、未计入公开 release）。
"""


def laws_index_entry():
    return {
        "name": "中华人民共和国著作权法",
        "aliases": ["著作权法"],
        "type": "法律",
        "order": 9,
        "issuing_authority": "全国人民代表大会常务委员会",
        "jurisdiction": "全国",
        "status": "effective",
        "promulgation_date": "2020-11-11",
        "effective_date": "2021-06-01",
        "source_url": FLK_2020_URL,
        "source_accessed_at": VERIFIED_AT,
    }


def catalog_entry():
    return {
        "id": "M9",
        "name": "著作权法（2021-06-01 施行，含2010/2020两版总则第1–5条）",
        "name_en": "Copyright Law of the PRC",
        "law_code": LAW_CODE,
        "total_articles": 10,
        "verified_articles": 10,
        "status": "internal",
        "versions": ["2021-06-01", "2010-04-01"],
        "download_url": None,
        "price_tier": "free",
        "note": "内部自用，未发布；仅含总则第1–5条（2010修正+2020修正）",
    }


def main():
    dry = "--dry-run" in sys.argv
    r2010, r2020 = load_local()
    s2010, seed2010, l2010 = build(r2010, "v2010")
    s2020, seed2020, l2020 = build(r2020, "v2020")
    statutes = s2010 + s2020
    seeds = seed2010 + seed2020
    ledger = {**l2010, **l2020}

    mod_dir = os.path.join(KB_ROOT, "modules", "M9_copyright_law")
    seed_path = os.path.join(KB_ROOT, "knowledge_base", "SEED", "copyright_law.json")
    idx_path = os.path.join(KB_ROOT, "knowledge_base", "laws_index.json")
    cat_path = os.path.join(KB_ROOT, "catalog.json")

    # 防覆盖：若 M9 已存在 statutes.jsonl，中止以免误写
    existing_stat = os.path.join(mod_dir, "statutes.jsonl")
    if os.path.isfile(existing_stat):
        raise SystemExit(f"[ABORT] 已存在 {existing_stat}，放弃写入以防覆盖。如需重建请先删除 M9 目录。")

    if dry:
        print(f"[DRY-RUN] 将写入 {len(statutes)} 条 statutes / {len(seeds)} 条 seed / {len(ledger)} 条 ledger")
        print("laws_index 将追加 COPYRIGHT_LAW；catalog 将追加 M9")
        for st in statutes:
            print("  ", st["id"], st["effective_date"], "rev_of=", st["revision_of"])
        return

    # 落盘
    os.makedirs(mod_dir, exist_ok=True)
    with open(os.path.join(mod_dir, "statutes.jsonl"), "w", encoding="utf-8") as f:
        for st in statutes:
            f.write(json.dumps(st, ensure_ascii=False, sort_keys=False) + "\n")
    with open(os.path.join(mod_dir, "verifications.json"), "w", encoding="utf-8") as f:
        json.dump(ledger, f, ensure_ascii=False, indent=2)
        f.write("\n")
    with open(os.path.join(mod_dir, "README.md"), "w", encoding="utf-8") as f:
        f.write(module_readme())
    with open(os.path.join(mod_dir, "CHANGELOG.md"), "w", encoding="utf-8") as f:
        f.write(module_changelog())

    with open(seed_path, "w", encoding="utf-8") as f:
        json.dump(seeds, f, ensure_ascii=False, indent=2)
        f.write("\n")

    idx = json.load(open(idx_path, encoding="utf-8"))
    if LAW_CODE not in idx:
        idx[LAW_CODE] = laws_index_entry()
    with open(idx_path, "w", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False, indent=2)
        f.write("\n")

    cat = json.load(open(cat_path, encoding="utf-8"))
    if not any(m.get("id") == "M9" for m in cat["modules"]):
        cat["modules"].append(catalog_entry())
        cat["last_updated"] = VERIFIED_AT
    with open(cat_path, "w", encoding="utf-8") as f:
        json.dump(cat, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"[OK] 已写入 M9_copyright_law：statutes={len(statutes)} seed={len(seeds)} ledger={len(ledger)}")
    print(f"[OK] laws_index 现有 {len(idx)} 部法；catalog 现有 {len(cat['modules'])} 个模块")


if __name__ == "__main__":
    main()
