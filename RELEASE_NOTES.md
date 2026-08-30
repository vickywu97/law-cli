# law-cli v1.0 — 中文地方法规法条速查器（数据合规 MVP）

> 一句话：**法条原文合法获取 → 固定来源 → 可复现证明**的最小闭环，219 条数据全部 **AI 审核终核**，零第三方依赖。

---

## 核心数据（本版本已发布）

| 指标 | 数值 |
|------|------|
| 法条总数 | **219 条** |
| 覆盖 | 著作权法 10 · 北京市生活垃圾管理条例 79 · 上海市生活垃圾管理条例 130（2019 通过 65 + 2026-08-15 修正 65，双 lineage 独立版本） |
| AI 审核终核 | **219/219 `ai_verified`**（由 `ai_audit_all.py` 按"法 + 版本"逐字对账，AI 审核即终态） |
| 防篡改 | **219/219 完好**（逐条 SHA-256，`verify` 比对） |
| 复核闸门 | `verify --gate` exit 0（仅 `pending` 拦截，已接入 CI） |
| 依赖 | 纯 Python 标准库，零第三方包 |

## 功能

`fetch` · `show`（支持 `--version` 过滤）· `verify`（`--reconcile` 官方逐字对账 / `--gate` 复核闸门）· `versions`（版本轴 + 差异对比）· `validity`（效力红黄绿）· `check`（最小引用校验）· `check-batch`（批量校验）· `relate`（对接本地 `verified-chinese-law-kb`）。

## 合规红线

- **官方源唯一化**：全国性法律只取国家法律法规数据库 `flk.npc.gov.cn`；地方性法规锁定省级官方站（`*.gov.cn` 白名单），命中商业库（北大法宝 / 威科先行等）直接拒绝，需 `--allow-non-official` 才放行。
- **只提取条文原文**，剥离编排 / 注释 / 效力说明等第三方增值内容。
- **完整证据链**：来源 URL + 公布日 + 施行日 + 检索日 + SHA-256，可离线复现。
- 所有输出附法律免责横幅。

## 快速开始（零依赖，仅标准库）

```bash
python3 law_cli.py show "中华人民共和国著作权法" --article 5
python3 law_cli.py verify --gate        # 终核闸门（全 ai_verified → exit 0）
python3 law_cli.py check "著作权法第5条" # 引用校验
python3 law_cli.py versions "上海市生活垃圾管理条例"  # 版本轴 + difflib 差异
```

## 可信度自检

```bash
python3 tests/test_law_cli.py           # 15/15 通过
python3 law_cli.py verify --gate         # 终核闸门，exit 0
```

CI（GitHub Actions）在每次 push / PR 自动复跑上述两项。

## 审核口径说明（重要）

发布者明确 **AI 审核即终核，不要求律师人工签署**：`review_status=ai_verified` 即为终态。所有法条原文取自官方公开渠道，依《著作权法》第五条属公共领域。详见仓库 `docs/compliance/03_AI审核终核声明.md`。

> ⚠️ **法律免责**：本工具仅整理公开法条原文，效力状态提示以官方发布为准，**不构成法律意见**；具体事项请咨询具备相应资质的执业律师。

## 已知范围与后续

- 范围：上海 / 北京生活垃圾管理条例 + 著作权法总则（试点）。后续可扩展其他地方性法规模板（见 `docs/compliance/` 检查表）。
- 上海 2026 修正版以人大公报 / `flk.npc.gov.cn` 重新公布的全文为最终参照；当前已按官方 2026 修正表述逐字对账并标记 `ai_verified`。

## 许可

MIT —— 见仓库 `LICENSE`。
