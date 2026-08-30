# law-cli 文档站说明（GitHub Pages）

> 本文件同时承担两个作用：**① 给你（维护者）的开启步骤**；**② 给访客的站点地图**。

---

## 一、如何开启（维护者操作，Web UI）

GitHub Pages 沙箱无法自动配置，需你在 GitHub Web UI 手动开启一次：

1. 打开仓库 **Settings → Pages**（左侧栏）。
2. **Build and deployment → Source** 选 `Deploy from a branch`。
3. **Branch** 选 `main`，**folder** 选 `/docs`，点 **Save**。
4. 等待 1–2 分钟，Actions 里出现 `pages-build-deployment` 跑完即上线。
5. 站点地址：`https://vickywu97.github.io/law-cli/`

> 站点首页是 `docs/index.md`；本说明（`docs/SITE_GUIDE.md`）作为站内导航补充，不会被设为首页。

---

## 二、站点结构（访客地图）

```
law-cli 文档站（/docs）
├── index.md                         ← 首页：数据现状 + 快速开始 + 导航
├── SITE_GUIDE.md                    ← 本文件：开启步骤 + 站点地图
└── compliance/                      ← 核心可信度记录
    ├── README.md                    ← 合规档案索引
    ├── 01_商业库样本隔离说明.md      ← 与商业库（北大法宝/威科等）的接触史与隔离政策
    ├── 02_逐站网站条款复核清单.md    ← 5 个政府源 robots / 使用条款技术性复核
    ├── 03_AI审核终核声明.md         ← 219/219 ai_verified 的审核范围/方式/开放项结论
    ├── 04_免责声明模板.md           ← 对外引用统一免责文案
    ├── 05_数据来源与核验记录.md      ← 每部法的来源域、核验方式、SHA
    └── 06_执行检查表.md             ← 待办闭环跟踪
```

根级报告（不在 `/docs` 内，走 GitHub blob 链接，不在 Pages 站内）：
- `law-cli_改进诊断与方案.md` — 根因级审查与再架构（含 §7.7 AI 终核决策）
- `上海生活垃圾条例2026修正_AI核对报告.md` — 上海 2026 修正版逐字对账记录
- `地方性法规官方源调研.md` — 北京 / 上海两省官方源接入与证据链
- `著作权法纳入KB_执行方案.md` / `著作权法纳入KB_只读草案.md` — 对接 `verified-chinese-law-kb` 的方案与草案

---

## 三、审核口径（访客须知）

本仓库统一口径：**AI 审核即终核，不要求律师人工签署**。`review_status=ai_verified` 即为终态；所有法条原文取自官方公开渠道（依《著作权法》第五条属公共领域），每条固定完整证据链（来源 URL / 公布·施行日期 / 检索日期 / SHA-256）。

> ⚠️ 本仓库所有内容**不构成法律意见**；法条以官方发布文本为准，具体事项请咨询具备相应资质的执业律师。

---

*本说明随 `main` 分支 `docs/` 目录一起版本管理。*
