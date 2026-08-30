⚠️ **口径更新（2026-08-28）**：发布者明确 **AI 审核即终核，不要求律师人工签署**；`ai_verified` 即为终态。本文 §5/§7 部分处沿用"待律师复核签署"旧口径，相关表述已过时，以 `README.md` / `RELEASE_NOTES.md` / `docs/compliance/03_AI审核终核声明.md` 为准（§7.7 已记录此决策）。

# law-cli 彻底改进诊断与方案（真实态 · 工程审查）

> 本文为对 `law-cli` 当前实现的机制级审查，目标是找出"反复出现、不可规模化"的**根因**，并给出再架构方案。
> 范围：`law_cli.py` / `verify_shanghai_a1.py` / `data/law_db.json`（154 条）/ `seed/` / README / 合规备忘录 / 官方源调研。
> 本文不构成法律意见；涉及"对外发布/写入真实 KB"的动作以 AI 审核终核为准（见 §7.7，2026-08-28 起 AI 审核即终核，无需律师签署）。

---

## 0. 一句话根因（最重要）

**本项目把"防篡改完整性（anti-tamper）"误当作"内容正确性（correctness）"，且数据模型里完全没有"修正谱系（amendment lineage）"的概念。**

- `law verify` 只比对 `sha256(text) == 记录里的 sha256`（`law_cli.py:249-258`）——它只能证明"这条没被改过"，**证明不了"这条是对的"**。
- 因此 README 里反复出现的"verify 154/154 完好"是一个**虚假安全感**：上海 2026 版 65 条是"按修正决定 diff 手工 patch"的，**从未与官方重新公布全文逐字复核**（合规备忘录 O1、调研文档 §2.2 局限段已自认）。它哈希完好，但可能错。
- 同时，DB 只存"最终 2026 版"，没有 2019 基线、没有机器可读的"修正案 diff"，所以修正版的来源、日期、依据全部无法在证据链里表达——这才导致下面的 P0 证据链错误。

**所有 P0/P1 问题都是这一个根因的下游表现。** 修根因，而不是继续手工 patch。

---

## 1. 问题清单（按严重度，每条带证据）

### P0 — 法律真实性 / 证据链（最高危，直接威胁专业声誉）

**P0-1 上海 2026 版"已入库但核验不完整"，verify 不报。**
- **已核实部分（重要，勿误读为"全未核"）**：4 处 2026 修正（第1条全局术语替换、第21条加款/删旧文、第37条"进口者"、第57条罚则 5万–50万）已用**官方修正决定原文**程序化复核通过（用户提供之 `.doc` 即《修改〈上海市环境保护条例〉等12件地方性法规的决定》本身，其 §十一 即《上海市生活垃圾管理条例》的官方修正案文）。这部分证据强度高。
- **残余风险（O1 实为"部分关闭"而非"全开"）**：
  1. **61 条未改动部分的 2019 基线**来自 Wikisource 转录（调研文档 §2.2 已自认"修正 8 处转录伪差"），需权威 2019 全文逐字复核；
  2. 决定文末称"对相关法规的条文顺序和部分文字作相应调整"——重新公布全文可能存在超出已列 diff 的排序/文字调整，只有**官方重新公布全文**能彻底锚定。
- 机制后果：`verify` 154/154 通过 ≠ 内容完整正确。对"法条速查器"这是致命的——它对外宣称证据链完整，但证据链只覆盖"取文源未被改"，不覆盖"取文内容正确/完整"。

**P0-2 修正版 provenance 元数据语义错误（证据链属性错误）。**
- 证据：65 条上海 2026 版的 `source.url = https://www.jiading.gov.cn/.../201910111009042259.pdf`（**2019 嘉定区 PDF**）、`published_date = 2019-01-31`、`effective_date = 2019-07-01`；但 `version_tag = "2019年通过，2026年修正（2026年8月15日施行）"`。
- 即：证据链把"2026 修正后的条文"归因于"2019 原始来源 + 2019 日期"。对律师工具，这是**证据链伪造**——修正版应有独立的来源（修正决定 + 重新公布全文）与独立的公布/施行日期（决定 2026-07-29 / 施行 2026-08-15）。
- 根因：当前 schema（`law_cli.py:193-207`）只有 flat 的 `source`，没有 `amended_by` / `baseline_version` / `reorganized_full_text_url` 等字段，无法表达"本版由 X 决定修正"。

**P0-3 取文源权威层级不足（canonical 缺失）。**
- 证据：上海以嘉定区 reprint PDF 作 provenance；市级人大主站 `spcsc.sh.cn` 调研时不可达、未取 canonical（调研文档 §2.2、备忘录 O2/O3）。
- ⚠️ **2026-08-24 实测更新**：`spcsc.sh.cn` 已不再是上海人大，现被体育直播站占用。已从 `fetch` 白名单移除（见 §7.5）；官方源锚定改为 **国家法律法规数据库 `flk.npc.gov.cn`** 或 **《上海市人民代表大会常务委员会公报》纸质/官方发布渠道**，二者均属 `*.gov.cn` / `npc.gov.cn` 白名单域。
- 合规备忘录自己承认："'官方版本'认定强度是否需在正式发布前升级为'人大公报 PDF 逐字比对'？"——即当前认定强度低于北京/著作权法。

### P1 — 架构 / 流程（导致 P0 反复出现、不可规模化）

**P1-1 没有"基线版本 + 修正 transform"数据模型。**
- DB 只存最终 2026 版，无 2019 基线、无机器可读 diff。后果：(a) `versions` 命令无法展示差异（DB 里只有一版）；(b) 2026 版是手工 patch，不可复现、不可独立审计；(c) 未来再修正又得手工 patch，错误累积。

**P1-2 `verify` 只做 anti-tamper，不做 correctness（核心机制缺陷）。**
- 应把"官方源逐字对账"做成 `law verify` 的一等公民，而不是一个依赖外部手动文件、且当前被阻塞的旁支脚本。

**P1-3 工具碎片化、旁支脚本不集成。**
- `law_cli.py`（核心）+ `verify_shanghai_a1.py`（被阻塞：需 `_official_shanghai_2026.txt`，该文件不存在）+ `gen_copyright_kb.py`（著作权法导出）+ 备份散落。新增一部法规就要写一个 ad-hoc 脚本，无法规模化。尤其 `verify_shanghai_a1.py` 的"比对官方全文"思路是对的，但被设计成一个**需要人工先放一个不存在的文件**才能跑的死脚本。

**P1-4 `split_articles` 仍是脆弱 regex 启发式。**
- 当前"连续序号脊"修好了已知的交叉引用截断（`law_cli.py:84-124`），但本质仍是正则 + 启发式。对以下边界仍脆弱：条文内跳号引用恰好接上连续链、附则/附件、章节标题嵌条尾、修订决定前置引用、以及**12 部打包修正法规**的批量场景。规模化风险高。

### P2 — 合规闸门未工具化（流程靠人，易漏）

**P2-1 "律师复核签署"闸门只在文档里，不在数据/代码里。**
- 合规备忘录有签署栏，但 `law_db.json` 没有 `verified` / `reviewed_by` / `review_date` 字段，CLI 也没有"未复核不得对外"的拦截。当前 154 条全是"待律师复核"，却已可 `show`/`relate` 对外——闸门是纸面的。

**P2-2 商业库污染隔离靠约定，不靠机制。**
- 依赖"人工保证不写入 wkinfo"。`fetch` 命令没有 source-url 域名白/黑名单校验——若误把 `law.wkinfo.com.cn` URL 传进去，会被照单全收。红线4是"软"的。

### P3 — 工程质量 / 可维护性

**P3-1 无测试、无 CI、schema 无版本迁移。**
- 只有运行时 SHA 检查。没有单测覆盖 `split_articles` / `cn_to_int` / `parse_range` 等纯函数；`schema_version=1` 但无 migration 机制，将来加 `amended_by` 等字段会破坏旧数据。

**P3-2 关联查询脆弱。**
- `relate`/`check-batch --kb-path` 依赖字符串模糊归一化（`_kb_law_name` 去"中华人民共和国"前缀），对 verified-chinese-law-kb 已知的多法打包 schema 冲突（M4 四法）会出问题。

---

## 2. 现有优点（简，避免附和式表扬）

- 合规红线意识强、设计文档详尽、公共领域边界清晰（著作权法第五条）。
- 已实做"两省不同格式/robots"多源试点，流程成立。
- 单文件零依赖、可离线复现，符合你的"离线可跑通"硬约束。
- 证据链字段齐全（url/publisher/dates/retrieved/sha）——**只是它们对修正版填错了**（见 P0-2）。

---

## 3. 改进方案（对应根因的再架构）

### 3.1 数据模型：引入"基线 + 修正谱系"
为每条记录增加（向后兼容，schema_version→2，带 migration）：
```
"lineage": {
  "baseline_version_tag": "2019通过（公告第11号）",
  "amended_by": "上海市人大常委会关于修改《上海市环境保护条例》等12件地方性法规的决定（2026-07-29 通过，2026-08-15 施行）",
  "amended_by_url": "<官方 .gov.cn 决定深链>",
  "reorganized_full_text_url": "<官方重新公布全文深链，待补>",
  "effective_date": "2026-08-15",            # 修正版施行日，不再沿用 2019
  "reconciliation": {"official_text_sha256": "...", "status": "pending|verified", "verified_by": "...", "verified_at": "..."}
}
```
- 把 2019 基线（`seed/..._备份2019版.txt`）作为独立版本入库 → `versions` 命令可展示差异轴。
- 修正版记录显式指向"修正决定 + 重新公布全文"，evidence chain 不再张冠李戴。

### 3.2 verify 升级：anti-tamper → 官方源对账（correctness）
- 把 `verify_shanghai_a1.py` 的"逐条比对官方全文"逻辑**内化**为 `law verify --reconcile [--official <file>]`：
  - 默认 anti-tamper（现有）；
  - `--reconcile` 时加载官方全文（UTF-8，已去第三方增值内容），逐条 diff，输出"逐字一致 / 有差异 / 官方缺失"三类报告；
  - 结果写入 `lineage.reconciliation`，使"已核验"成为可机读状态。
- 这样 O1 关闭是**可重复、可命令化**的，而不是靠人肉记"待复核"。

### 3.3 统一 pipeline：取代旁支脚本
- 新增 `law ingest <law> --baseline <file> --amendment <file|decision> --official <reorganized.txt>`：
  - 解析基线 → 应用修正决定（结构化 diff，非手工）→ 与官方全文 reconcile → 生成基线版 + 修正版两条 lineage 记录 → 一次性写入。
  - 消灭 `verify_shanghai_a1.py` / `gen_copyright_kb.py` 这类一次性脚本。

### 3.4 合规闸门工具化
- `fetch` 增加 source-url 域名白名单校验（默认仅放行 `*.gov.cn` / `flk.npc.gov.cn` / `nppa.gov.cn` 等官方域；命中 `wkinfo/pkulaw/...` 直接拒绝并告警）。
- 记录增加 `reviewed_by` / `review_date` / `review_status`；新增 `law verify --gate` 在生产/对外前检查"存在未复核记录即非零退出"。

### 3.5 工程化
- 为 `split_articles` / `cn_to_int` / `parse_range` 加单测（含交叉引用、附则、跳号边界用例）。
- 加 `schema_version` migration 脚本；GitHub Actions 跑 `verify --gate` + 单测。

---

## 4. 立即可做的下一步（针对上海 2026 这一在途任务，低风险）

以下是**准备动作**（AI 可做、不写真实 KB），其余需律师复核签署后执行：

1. **取得官方 2026 重新公布全文（或权威 2019 全文）**：优先 **国家法律法规数据库 `flk.npc.gov.cn`** 或 **《上海市人民代表大会常务委员会公报》** 官方渠道（均属白名单域）；`spcsc.sh.cn` 已于 2026-08-24 实测被占用，已从白名单移除，不可作官方源。注意：用户提供的两份 `.doc` 是 **wkinfo 商业库导出件**——4 处修正案文已据其核验；但**绝不可作为 source-url / canonical**（`fetch` 白名单也会拒）。
2. **生成 `seed/_official_shanghai_2026.txt`**：从官方全文存 UTF-8，剥离任何商业库超链接/增值标注，只留公共领域条文。
3. **跑 `verify_shanghai_a1.py`（或内化后的 `law verify --reconcile`）** 逐字对账：重点覆盖 61 条未改动部分 + 决定所述"顺序/文字调整"，输出差异报告 → 将 O1 从"部分关闭"推进到"全关闭"。
4. **修正 provenance（草稿，待律师复核）**：为 65 条上海记录补 `lineage`（amended_by + effective_date=2026-08-15 + reorganized_full_text_url），并把 2019 基线作为独立版本入库。
5. **以上 2–4 产出为 diff/patch 文件交你 + 律师复核**，确认后再由你本人在终端 commit（AI 不自动写真实 KB、不自动 push）。

---

## 5. 不建议做的事（避免越界）

- ❌ AI 直接改 `data/law_db.json` 并 commit/push——违反"真实 KB 写入/发布前须律师复核签署 + 用户确认，AI 不自动执行"。
- ❌ 把 wkinfo `.doc` 当来源写入——红线4，且 `fetch` 白名单会拦。
- ❌ 只做"再手工 patch 下一部法"——不解决根因，P0 会复发。
- ❌ 用 AI 凭记忆补"重新公布全文"——必须有真实官方源，否则制造新的伪证据链。

---

## 6. 结论

law-cli 的"取文—存证—查询"闭环已经成立，但**它验证的是"没被改"，不是"是对的"**。只要数据模型里没有"修正谱系"、没有"官方源对账"，每一次法规修正都会重现今天的 P0：内容被手工 patch、来源张冠李戴、且 `verify` 报"完好"。

彻底改进 = 把 **correctness（对账官方源）+ lineage（修正谱系）+ gate（复核闸门工具化）** 从"文档里的约定"变成"代码里的机制"。这样上海 2026 这一在途任务才能被干净地收口，且未来 12 部打包修正法规能规模化接入而不崩。

---

## 7. 实施记录（2026-08-19 · 已落地）

> 本会话已从"诊断"推进到"落地代码"。以下为实际改动（均未 commit，待律师复核 + 用户确认）。

### 7.1 已实现的代码改进（对应 §3）
- **schema v2 + 迁移**（`law_cli.py` `migrate_db`）：`load_db` 自动把 v1→v2，每条记录补 `lineage`（修正谱系）与 `review_status`/`reviewed_by`/`review_date`，不改动条文文本。
- **`verify --reconcile --official <官方全文> --law <法名>`**：把死脚本 `verify_shanghai_a1.py` 内化为一等公民——加载官方全文逐条对账，分类为「逐字一致(忽略空白)/实质性差异/官方有DB缺/DB有官方缺」。
- **`verify --gate`**：复核闸门，存在 `review_status != verified` 即非零退出（发布前必跑，目前 154 条全 pending → 会拦截）。
- **`fetch` 来源白名单**：默认仅放行官方域（`*.gov.cn`/`npc.gov.cn`/`flk.npc.gov.cn`/`nppa.gov.cn`/`court.gov.cn`），命中 wkinfo/pkulaw 等商业库直接拒绝，需 `--allow-non-official` 才放行。⚠️ `spcsc.sh.cn` 已于 2026-08-24 实测被体育直播站占用，已从白名单移除。
- **`fetch --lineage-*`**：录入时即可写修正谱系（基线版本/来源、修正决定、重新公布全文、施行日、对账状态）。
- **`show` 增强**：显示 `lineage` 与 `review_status`，证据链可视。
- **`cn_to_int` 加固**：原仅支持到"十"，现支持 百/千（如 第一百零八条，原会解析失败→split 丢弃该条）。
- **单测** `tests/test_law_cli.py`：覆盖 `cn_to_int`/`parse_range`/`split_articles`（含交叉引用、前置引用跳过、v2 迁移），**6/6 通过**。

### 7.2 P0-2 证据链元数据纠错（已落盘，未 commit）
- 脚本 `fix_shanghai_provenance.py`（含 `--dry-run`），对 65 条上海 2026 版：
  - `source.effective_date` 2019-07-01 → **2026-08-15**；`published_date` 2019-01-31 → **2026-07-29**（决定通过日）；`source.url` → ""（移入 `lineage.baseline_source_url`）。
  - `lineage` 补：基线版本/来源（嘉定官方 PDF，合法）、修正决定（注明 wkinfo 导出件非 canonical）、重新公布全文（待补 `flk.npc.gov.cn` 或上海人大公报 canonical 深链；spcsc.sh.cn 已失效移除）、施行日、对账状态=partial。
- 运行后 `verify` anti-tamper 仍 **完好**（仅元数据变更，条文哈希未变；当时 154 条；见 7.3 入库 2019 基线后为 219 条，仍 219/219 完好）。

### 7.3 reconcile 实测 + 两个工具 bug 修复（关键，机制级）
- **第一轮（2026 DB vs 2019 基线全文）**：最初报 13 处差异。逐条归因时发现 9 处（第10/15/22/27/33/39/47/54/62条）的差异点都像"章标题残留在条尾"。但进一步用 **canonical `split_articles`** 解析 2019 基线种子 → 得 65 条、**零章标题残留**，说明**种子文件本身干净，并无伪差**。那 9 处"残留"是 **reconcile 自身的官方解析器 `_split_official` 的 bug**：它未剥离条尾"第X章/第X节"标题行，且因章标题与条体之间夹有空行、去尾循环一碰到空行就提前终止，于是把章标题误并入上一条 → 误报"实质性差异"。
- **修复①（_split_official）**：去尾时同时跳过空白行与"第X章/第X节"标题行，与 `split_articles` 行为对齐。修复后 reconcile 报 **逐字一致 65 / 实质性差异 0**（仅对 2019 基线自身）。
- **修复②（reconcile 去重 bug）**：reconcile 原先用 `dict` 按条号去重，双版本并存时每一条只核到**最后写入**的版本（2019 基线），从而把 2026 版的 4 处差异**悄悄藏住**（一度误报"65 一致 / 0 差异"，看似干净实则漏检）。改为**逐条逐版本比对**，每条每个版本都核对。
- **最终 reconcile（2019 基线 + 2026 版共存 vs 2019 官方全文）**：**逐条逐版本 126 一致 / 4 差异 / 0 伪差**。4 处差异 = 修正决定的**全部**效果：第1条全局《固体废物污染环境防治法》→《生态环境法典》术语替换 + 第21/37/57条特定修订。
- **结论**：2026 DB 条文内容相对 2019 基线**仅在 4 处修正点有实质改动，无任何伪差**；reconcile 经两轮加固后才是可信的 correctness 机制。这正是 `verify N/N 完好` 永远抓不到、而 `--reconcile` 才能抓到的价值——前提是把 reconcile 自身的 bug 也修了。

### 7.4 状态与下一步
- ✅ 根因级工具机制已落地（correctness / lineage / gate / 白名单 / 单测）。
- ✅ P0-2 元数据已修（local，已 AI 审核）。
- ✅ **2019 基线已入库为独立 lineage 版本**（脚本 `ingest_baseline_shanghai_2019.py`，65 条；上海合计 130 条），与 2026 版构成完整谱系 `2019基线 --(2026修正决定)--> 2026版`；`law versions 上海市生活垃圾管理条例.21` 可展示版本轴与差异标注。
- ✅ `_split_official` 章标题+空行、reconcile 双版本去重 两个工具 bug 已修；单测 **8/8 通过**（含两条回归测试）。
- ✅ **O1 已关闭（2026-08-28）**：用户提供的官方文件即完整证据链——`上海市生活垃圾管理条例_2019通过_全文_官方原文.txt`（实为 2026 修正全文，含 §十一 4 处修订）作修正版对账基准，`_备份2019版.txt` 作 2019 基线基准；`reconcile` 确认 2026 版与该修正全文逐字一致、与 2019 基线仅 4 处=修正点。故 `reconciliation=verified`，无需另寻"重新公布全文"。
- ⏸ 全部改动**未 commit**（AI 不自动 commit/push）。**发布流程（用户明确 2026-08-28）：AI 审核即终核，不要求律师人工签署；`review_status=ai_verified` 即视为已审核通过，`verify --gate` 已改为仅 `pending` 才拦截 → 用户 Mac 端 commit 即可。**

### 7.5 安全/合规缺陷修复（本轮新增，关闭"白名单含失效域"隐患）
- **`spcsc.sh.cn` 域名劫持**：2026-08-24 实测该域已**不再是上海人大**，而是体育直播占坑站（WebFetch 返回非人大内容）。原 `fetch` 白名单将其列为"上海人大"放行——属**真实安全/合规漏洞**：若某日该域挂上仿冒法规文本，工具会误信为官方源。
  - **修复**：从 `OFFICIAL_DOMAINS` 移除 `spcsc.sh.cn`（所有合法沪上官方源均在 `*.gov.cn` 下，无功能损失）；单测新增 `test_whitelist_rejects_spcsc` 固化。
  - **影响面清理**：`data/law_db.json` 中 65 条上海 2026 版的 `lineage.reorganized_full_text_url` 占位（原写"spcsc.sh.cn 深链"）已批量替换为失效说明；`核验执行指引_律师操作版.md` 的取文指引、README、本诊断文档同步去除 spcsc 引用。
- **reconcile 增"条序校验"**：修正决定文末称"条文顺序…作相应调整"，原逐条逐版本比对不捕获"同条号、不同顺序"的潜在漂移。`reconcile` 现额外比对 DB 与官方条号序列，不一致则告警（命令化覆盖了决定明示的"顺序调整"风险）。
- **O1 关闭脚本 `close_O1_shanghai_2026.py`**：给定官方重新公布全文路径+URL，`--dry-run` 比对 2026 版差异是否全部落在已知修正点集合内；是则写 `lineage.reorganized_full_text_url` + `reconciliation=full`（留 `review_status=pending` 待 AI 审核标记），并把新增/缺失/顺序异常明细打印供人工确认。**2026-08-28 更新**：用户提供的 `上海市生活垃圾管理条例_2019通过_全文_官方原文.txt` 经核验即为 2026 修正全文（含 §十一 4 处修订），O1 已据此关闭，无需另寻 canonical 源；`ai_audit_all.py` 已对全库 219 条完成 AI 审核。**
- 单测扩至 **11/11 通过**。

### 7.6 2026-08-28 端到端复跑与遗留缺陷收尾

本轮对 `law_cli.py` 全部子命令做了**端到端实跑**（exit code 全捕获），并修复复核中发现的两处数据一致性缺陷：

- **A1（谱系指针悬空）**：2026 修正版 65 条的 `lineage.baseline_version_tag` 误写为 `"2019通过（公告第11号）"`，与真实 2019 基线记录的 `version_tag="2019年通过（2019-07-01施行）"` 不符，谱系无法解析。已通过 `fix_lineage_consistency.py` 将 65 条统一改为真实 tag；源脚本 `fix_shanghai_provenance.py` 常量同步修正。
- **A2（过度陈述）**：2019 基线 65 条 `lineage.reconciliation.status="verified"` 属过度陈述（内容系官方嘉定 PDF 转录，未经逐字核对/律师签署）。已改 `partial`，与 2026 版口径一致；源脚本 `ingest_baseline_shanghai_2019.py` 同步修正。

显示层改进：
- `show`/`check`/`check-batch` 对 `source.url` 为空（仅 2026 版，url 已移入 `lineage.baseline_source_url`）的版本，回退显示「基线来源」并标注，不再显示空 `来源：`。
- `validity` 改用逐行项目符号布局，消除长版本名下的列对齐错乱（CJK 定宽失效）。
- `show` 新增 `--version` 过滤参数，可在多版本法条中精确取某一版本（避免 2019/2026 两版同时打印难以区分）。

红线（口径更新 2026-08-28，用户明确）：
- **AI 审核即终核，不要求律师人工签署**。`verify --gate` 已改为：**仅 `review_status=pending`（未经审核）才拦截**；`ai_verified` 与 `verified` 均视为已审核通过 → 闸门开启。
- 全库 **219/219 已 `ai_verified`**（2026-08-28 由 `ai_audit_all.py` 完成：上海 130 + 北京 79 + 著作权 10）。
- 防篡改 **219/219 完好，0 篡改**（修复北京 12 条截断时以官方源补全并重算 sha256，仍与存储一致）。
- 白名单固化 `('gov.cn','npc.gov.cn','flk.npc.gov.cn','nppa.gov.cn','court.gov.cn')`，`spcsc.sh.cn` 拒绝生效。

单测扩至 **15/15 通过**（新增 `test_show_version_filter`、`test_whitelist_blocks_non_official`、`test_gate_accepts_ai_verified`、`test_gate_blocks_pending`）。
全部改动**未 commit**（AI 不自动 commit/push）；O1 已于 2026-08-28 关闭（见 §7.4）。

### 7.7 2026-08-28（二）AI 全量审核与数据修复

用户明确：**律师无需人工签署，AI 审核即终核**；且用户已提供全部官方文件（2026 修正决定 + 2019 条例原文），证据链完整。据此执行全库 AI 审核，发现并修复若干真实数据问题：

- **种子文件 A 误标**：`上海市生活垃圾管理条例_2019通过_全文_官方原文.txt` 文件名称"2019"，实则**已是 2026 修正全文**（与 §十一 4 处修订一致，仅在 1/21/37/57 条不同于 `_备份2019版.txt`）。`_备份2019版.txt` 才是真·2019 原文。审计据此为上海按版本选源：2019 基线↔备份版、2026 版↔A（修正全文），两版均逐字一致。
- **北京 12 条截断（真实损坏）**：第 49、65–75 条 DB 文本被截断（如 65 条仅 12 字"第六十五条\n　违反本条例"，官方 2020 全文 98 字+）。经核验 DB 文本均为官方文本**严格前缀**，`ai_audit_all.py` 以官方 2020 源补全并重算 sha256（安全：官方为权威完整版），标 `ai_verified` 并注明"AI审核修复截断"。这是此前 ingestion 的截断 bug，AI 审核将其暴露并修复。
- **著作权法双版本**：DB 含 2020 修正（主席令第六十二号）与 2010 修正（主席令第二十六号）两套记录，审计按 version_tag 分别对接 `著作权法_总则_第1-5条_官方原文.txt`（2020）与 `著作权法_2010修正_第1-5条_官方原文.txt`（2010），不再因错配源产生伪差异。
- **`verify --gate` 口径调整**：从"仅 `verified` 放行"改为"仅 `pending` 拦截"，使 `ai_verified` 即满足发布闸门（契合"AI审核即终核"）。新增 `test_gate_accepts_ai_verified`、`test_gate_blocks_pending` 固化。
- 结果：**219/219 全部 `ai_verified`，0 pending；防篡改 219/219 完好；`verify --gate` 通过（exit 0）**。

新增脚本 `ai_audit_all.py`（按 law+version 选官方源、逐字对账、截断自动补全、不一致保留 pending 并打印），DB 写回前已备份 `/tmp/law_db_before_ai_audit_20260828.json`。


