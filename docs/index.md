# law-cli · 文档中心

> **项目定位**：中文地方性法规 / 法律的**数据层最小闭环**——先把最敏感的 IP 环节（法条原文的合法获取、固定来源、可复现证明）做扎实，再谈查询与效力标注。
> **审核口径**：发布者明确 **AI 审核即终核，不要求律师人工签署**；`review_status=ai_verified` 即为终态。详见 [AI 审核终核声明](compliance/03_AI审核终核声明.md)。
> **免责**：本仓库所有内容**不构成法律意见**；法条以官方发布文本为准，具体事项请咨询具备相应资质的执业律师。

## 数据现状（已发布）

| 指标 | 数值 |
|------|------|
| 法条总数 | **219 条** |
| 覆盖 | 著作权法 10 · 北京市生活垃圾管理条例 79 · 上海市生活垃圾管理条例 130（2019 通过 65 + 2026-08-15 修正 65，双 lineage） |
| AI 审核终核 | **219/219 `ai_verified`** |
| 防篡改 | **219/219 完好**（逐条 SHA-256） |
| 复核闸门 | `verify --gate` exit 0（已接入 CI） |
| 依赖 | 纯 Python 标准库，零第三方包 |

## 快速开始

```bash
python3 law_cli.py show "中华人民共和国著作权法" --article 5
python3 law_cli.py verify --gate          # 发布前必跑：仅 pending 拦截
python3 law_cli.py versions "上海市生活垃圾管理条例"  # 版本轴 + difflib 差异
```

完整命令见仓库根 [README.md](https://github.com/vickywu97/law-cli/blob/main/README.md)。

## 文档导航

> 文档站开启与结构见 [站点说明（SITE_GUIDE）](SITE_GUIDE.md)。

### 合规与核验（核心可信度记录）
- [AI 审核终核声明](compliance/03_AI审核终核声明.md) — 219/219 `ai_verified` 的审核范围、方式与开放项结论
- [数据来源与核验记录](compliance/05_数据来源与核验记录.md) — 每部法的来源域、核验方式、SHA
- [商业库样本隔离说明](compliance/01_商业库样本隔离说明.md) — 与商业库（北大法宝 / 威科等）的接触史与隔离政策
- [逐站网站条款复核清单](compliance/02_逐站网站条款复核清单.md) — 5 个政府源 robots / 使用条款技术性复核
- [免责声明模板](compliance/04_免责声明模板.md) — 对外引用统一免责文案
- [合规执行检查表](compliance/06_执行检查表.md) — 待办闭环跟踪
- [合规档案索引](compliance/README.md)

### 工程与溯源
- [彻底改进诊断与方案](https://github.com/vickywu97/law-cli/blob/main/law-cli_改进诊断与方案.md) — 根因级审查与再架构（含 §7.7 AI 终核决策）
- [上海市生活垃圾管理条例（2026 修正）AI 核对报告](https://github.com/vickywu97/law-cli/blob/main/上海生活垃圾条例2026修正_AI核对报告.md) — 上海 2026 修正版逐字对账记录
- [地方性法规官方源调研](https://github.com/vickywu97/law-cli/blob/main/地方性法规官方源调研.md) — 北京 / 上海两省官方源接入与证据链
- [著作权法纳入 KB 执行方案](https://github.com/vickywu97/law-cli/blob/main/著作权法纳入KB_执行方案.md) — 著作权法对接 `verified-chinese-law-kb` 的方案

---

*本页为 GitHub Pages 文档站首页，由 `main` 分支 `docs/` 目录构建。*
