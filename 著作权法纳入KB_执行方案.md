# 著作权法纳入 verified-chinese-law-kb · 执行方案（待确认）

> 状态：**已执行（2026-08-18）**。用户确认结论=仅自用/内部 + B3/D4 已按本方案落地；生成脚本 `gen_copyright_kb.py` 已运行，真实 KB 新增 M9_copyright_law（10 条，内部状态、未发布）。
> 关联：真实态合规备忘录_初稿.md §6、核验自审清单_律师自用.md §4、著作权法纳入KB_只读草案.md（本文件取代之）。

## 0. 前置确认（来自 §4 填答 + 本次核查）

| 项 | 结论 | 说明 |
|---|---|---|
| 结论 | **仅自用/内部** | A1/B2/C1 未做，按用户判断不阻塞内部使用；不对外发布 |
| D4 模块空号 | **M9_copyright_law** | KB 实为 M1–M8，order 顺至 8 → 新法 order=9（草案"04"已更正） |
| B3 2020 flk URL | **替换为 `https://flk.npc.gov.cn/`** | 原 law_db 用 search.html?keyword= 搜索页；改为 bare 首页，与 M4–M8 四部法完全一致，稳定非搜索页 |
| A3 著作权法文本 | 已核（官方源 nppa/flk，两版第1条 SHA 相同） | 可置 verified=true 并附律师签名 |
| D1/D2 商业库 | 0 命中已确认 | 干净 |

## 1. 真实 KB schema（本次核查所得，非假设）

**modules/M*/statutes.jsonl（新版，M1 范本，1260 行）字段顺序**：
`id, law_code, article_number, article_sort_key, content, effective_date, revision_of, verification_status, verified_at, verified_by, source_url, source_accessed_at, notes`

**knowledge_base/SEED/*.json（旧版，list，1260 项）字段**：
`law_code, article_number, article_sort_key, content, effective_date, revision_of, source_url, source_accessed_at, verified, notes`
（无 id / verification_status / verified_by —— 旧式）

**knowledge_base/laws_index.json**：每法一条，`{name, aliases[], type, order, issuing_authority, jurisdiction, status, promulgation_date, effective_date, source_url, source_accessed_at}`。

→ 著作权法需**三处落子**：① 新建 `modules/M9_copyright_law/statutes.jsonl`（新版 13 字段）；② 新建 `knowledge_base/SEED/copyright_law.json`（旧版 10 字段）；③ laws_index 增 `COPYRIGHT_LAW` 条目。

## 2. 字段映射（10 条 = 2010 版 5 条 + 2020 版 5 条）

生成脚本从 `law-cli/data/law_db.json` 抽取著作权法 10 条（`law` 含"著作权法"），逐条映射：

| 目标字段 | 来源 |
|---|---|
| law_code | 固定 `COPYRIGHT_LAW` |
| article_number | law_db `article`（已是"第1条"格式） |
| article_sort_key | 由 article 转 int（1–5） |
| content | law_db `text`（官方源 nppa/flk 提取，已 SHA 存证） |
| effective_date | 2010 版 → `2010-04-01`；2020 版 → `2021-06-01` |
| revision_of | 2020 版各条 → 对应 `COPYRIGHT_LAW_{n}_v2010`；2010 版 → `null` |
| verification_status | `verified`（A3 已核） |
| verified_at | 生成日 `2026-08-17` |
| verified_by | `Vicky Wu (律师/税务师/专利代理师)`（用户即核验律师，自带签名） |
| source_url | 2010 版 → `https://www.nppa.gov.cn/xxgk/fdzdgknr/zcfg_210/fl_211/201604/t20160429_4556.html`（原 law_db 官方 URL）；2020 版 → `https://flk.npc.gov.cn/`（B3 决议） |
| source_accessed_at | `2026-08-14` |
| notes | 空（或留"本法第五条见公有领域边界说明"） |
| id | `COPYRIGHT_LAW_{n}_v2010` / `COPYRIGHT_LAW_{n}_v2020` |

SEED 版（旧式）同源映射，仅 `verified: true` 替代 `verification_status/verified_at/verified_by` 三字段，无 `id`。

laws_index 新增：
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
  "source_url": "https://flk.npc.gov.cn/",
  "source_accessed_at": "2026-08-17"
}
```

## 3. 生成脚本（`law-cli/` 内，运行前需确认）

`gen_copyright_kb.py`：读 law_db.json → 生成上述两文件 → 增量合并进 laws_index.json（不改既有 8 条）。运行后：
- `law-cli` 的 `relate` / `check-batch` 将支持著作权法引用（O4 闭合，仅限内部）。
- 不做 `git` 推送、不发布；KB 仍处本地只读参考状态。

## 4. 执行门禁（确认清单）

- [x] 用户确认结论=仅自用/内部
- [x] 用户确认 B3 用 `https://flk.npc.gov.cn/`（与 M4–M8 一致，非 search 页）
- [x] 用户确认 D4=`M9_copyright_law`、order=9
- [x] 生成后 `verify` 两库（law_db 154/154 不变；KB 增量 10 条，KB 测试套件 8/8 通过）
- [x] 生成后人工抽看 statutes/SEED/ledger 对齐（id 一致、revision_of 合法、版本差异正确）

## 5. 不阻塞项（对外发布前再补，内部用可暂缓）

- A1 上海 PDF 逐字核、B2 北京 canonical SHA、C1 jiading robots —— 不影响本次著作权法入库。
- 2020 版若日后要逐条 detail URL，由用户在 flk 浏览器取得 `detail2.html?ZmY4…` 后回填（约 5 分钟）。
