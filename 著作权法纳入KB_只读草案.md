# 著作权法纳入 verified-chinese-law-kb · 只读实施方案草案

> **状态**：只读分析草案。**未写入** `verified-chinese-law-kb/`，未新增任何 KB 数据，未发布。
> **执行门禁**：须 (1) 执业律师签署《真实态合规备忘录》复核结论；(2) 用户明确确认后，方可运行生成脚本写入真实 KB。
> **依据**：KB 实际 schema 读取自 `/Users/vickywu/WorkBuddy/2026-08-07-00-27-56/verified-chinese-law-kb`（laws_index.json / knowledge_base/SEED/*.json / modules/*/statutes.jsonl）。

---

## 1. 源记录（来自 law-cli `data/law_db.json`）

著作权法共 **10 条记录**：2010 修正版 5 条（第1–5条）+ 2020 修正版 5 条（第1–5条）。
- 2010 版 source_url：`https://www.nppa.gov.cn/xxgk/fdzdgknr/zcfg_210/fl_211/201604/t20160429_4556.html`（国家版权局官网，官方）
- 2020 版 source_url：`https://flk.npc.gov.cn/search.html?keyword=著作权法`（国家法律法规数据库，**search 页**，非稳定 detail 页 → 见 §5 设计点 D2）
- publisher：均为"全国人民代表大会常务委员会"
- 完整性校验：2010 第1条 与 2020 第1条 SHA-256 同为 `ce8c8f327d72e7d3fa85da3c` → 第1条两版文本逐字一致，印证数据可信。

## 2. 目标 KB schema（实测字段）

**laws_index.json 条目**：
`law_code` / `name` / `aliases[]` / `type` / `order` / `issuing_authority` / `jurisdiction` / `status` / `promulgation_date` / `effective_date` / `source_url` / `source_accessed_at`

**knowledge_base/SEED/*.json 单条**：
`law_code` / `article_number`("第1条") / `article_sort_key`(int) / `content` / `effective_date` / `revision_of`(null) / `source_url` / `source_accessed_at` / `verified`(bool) / `notes`

**modules/M*/statutes.jsonl 单条**：
`id`("PATENT_LAW_1_v1") / `law_code` / `article_number` / `article_sort_key` / `content` / `effective_date` / `revision_of` / `verification_status`("verified") / `verified_at` / `source_url` / `source_accessed_at` / `notes`

## 3. 字段映射表（law_db.json → KB）

| KB 字段 | 来源（law_db.json） | 说明 |
|---------|---------------------|------|
| `law_code` | 固定 `COPYRIGHT_LAW` | 新增 code（见 §4） |
| `article_number` | `"第" + r["article"] + "条"` | 已是"第1条"格式 |
| `article_sort_key` | `int(r["article"])` | 1–5 |
| `content` | `r["text"]` | 直接复用 |
| `effective_date` | `r["source"]["effective_date"]` | 2010→2010-04-01；2020→2021-06-01 |
| `revision_of` | 见 §5 D1 | 2010=null；2020→2010 对应条 id |
| `source_url` | `r["source"]["url"]` | 均为官方域 |
| `source_accessed_at` | `r["source"]["retrieved_date"]` | 2026-08-14 |
| `verified` / `verification_status` | **`false` / `"pending"`** | 律师复核前不标 true（用户指示） |
| `verified_at` | 留空 | 复核后填 |
| `notes` | 版本标记，如"2020修正·第三次修正·主席令第六十二号" | 便于追溯 |

## 4. 拟新增 laws_index 条目

```json
"COPYRIGHT_LAW": {
  "name": "中华人民共和国著作权法",
  "aliases": ["著作权法"],
  "type": "法律",
  "order": 9,
  "issuing_authority": "全国人民代表大会常务委员会",
  "jurisdiction": "全国",
  "status": "effective",
  "promulgation_date": "2020-11-11",
  "effective_date": "2021-06-01",
  "source_url": "https://flk.npc.gov.cn/detail2.html?<稳定detail页，待从flk获取>",
  "source_accessed_at": "2026-08-14"
}
```
> 注：当前 2020 版记录用的是 flk **search** URL，写入 KB 前应替换为稳定的 `detail2.html?...` 页面（D2）。

## 5. 设计决策 / 开放点

- **D1 两版同 code**：KB 单 `law_code` 承载多版本，靠 `id` 后缀 `v1`(2010)/`v2`(2020) + `revision_of` 关联。建议 2010=`COPYRIGHT_LAW_{n}_v1`(revision_of=null)，2020=`COPYRIGHT_LAW_{n}_v2`(revision_of=v1 id)。
- **D2 2020 源 URL**：现 search 页不稳定，真实写入前需换成 flk detail 页（可经 `law-cli --try-online` 对确切 detail URL 单次 GET 落盘核对）。
- **D3 核验状态**：`verification_status="pending"`，`verified=false`，待律师在备忘录 §6 签署后改 `verified`/`verified`。
- **D4 模块目录**：沿用 `modules/M{n}_*/` 命名，下个空号推测为 `M9_copyright_law`（须先 `ls modules/` 确认最大号）。SEED 侧新增 `knowledge_base/SEED/copyright_law.json`。
- **D5 relate 兼容**：`law_cli.py` 的 `relate`/`check-batch --kb-path` loader 已是通用 schema（读 laws_index + statutes.jsonl），KB 一旦含 `COPYRIGHT_LAW` 数据即自动可用，无需改代码。

## 6. 生成脚本伪代码（DO NOT RUN until gated）

```python
# gen_copyright_kb.py  —— 仅草案，门禁未过不得执行
import json, hashlib
SRC = "data/law_db.json"
KB  = "/Users/vickywu/WorkBuddy/2026-08-07-00-27-56/verified-chinese-law-kb"
db = json.load(open(SRC))["records"]
COPY = [r for r in db if "著作权法" in r["law"]]
seed, stat = [], []
for r in COPY:
    ver = r["source"]["version_tag"]
    v_suffix = "v1" if "2010" in ver else "v2"
    art = int(r["article"])
    base = f"COPYRIGHT_LAW_{art}_{v_suffix}"
    rec = {
        "law_code": "COPYRIGHT_LAW",
        "article_number": f"第{art}条",
        "article_sort_key": art,
        "content": r["text"],
        "effective_date": r["source"]["effective_date"],
        "revision_of": None if v_suffix=="v1" else f"COPYRIGHT_LAW_{art}_v1",
        "source_url": r["source"]["url"],
        "source_accessed_at": r["source"]["retrieved_date"],
        "verified": False,                 # D3 门禁
        "notes": ver,
    }
    seed.append(rec)
    stat.append({**rec,
        "id": base,
        "verification_status": "pending",  # D3
        "verified_at": None,
    })
# 写出到 KB（门禁未过：注释掉）
# json.dump(seed, open(f"{KB}/knowledge_base/SEED/copyright_law.json","w"), ensure_ascii=False, indent=2)
# with open(f"{KB}/modules/M9_copyright_law/statutes.jsonl","w") as f:
#     for s in stat: f.write(json.dumps(s, ensure_ascii=False)+"\n")
```

## 7. 执行门禁清单（写入真实 KB 前必须全过）

- [ ] 律师签署《真实态合规备忘录》§6（尤其 O1–O3 对上海/北京证据强度的结论）
- [ ] 用户明确确认"可以写入"
- [ ] D2：2020 版 source_url 替换为 flk 稳定 detail 页
- [ ] D4：`ls modules/` 确认空号，避免覆盖现有模块
- [ ] 运行后 `verify` + KB 自带校验脚本回跑，确认 10 条入库、零篡改
