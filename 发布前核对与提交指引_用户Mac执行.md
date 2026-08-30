# law-cli 提交 / 发布指引（用户 Mac 执行）

> 本文件是给**你（用户）在本机终端**逐步操作的 runbook。
> 仓库最终态已发布完成：Release v1.0 已发、GitHub Pages 已开（`main` 分支 `/docs`）、`main` 分支保护已设为**轻量**（`Require status checks to pass before merging` 已开启，未禁止直接 push）。
>
> **口径（2026-08-28 用户明确，全程不变）**：律师**不需要**人工复核签署，**AI 审核即终核**。`review_status=ai_verified` 即视为已审核通过，可直接发布。

---

## 一、当前仓库最终态（一眼确认）

| 项 | 状态 |
|---|---|
| 记录数 | **219** 条（上海 130 = 65 基线 + 65 修正 / 北京 79 / 著作权 10） |
| 审核状态 | 全部 `ai_verified`（AI 终核，无 `pending`、无律师签署） |
| schema | v2（`lineage` + `review_status`） |
| 防篡改 | `verify` 报告 219/219 完好、0 篡改 |
| 单元测试 | 15/15 通过（CI 每次 push/PR 自动跑） |
| 发布闸门 | `verify --gate` 仅拦截 `pending`，全库无 `pending` → **exit 0** |
| 许可证 | MIT（`LICENSE` 已存在） |
| 安装 | `pip install -e .`（纯标准库，无需第三方依赖） |
| 文档站 | GitHub Pages 已开，首页 `docs/index.md` |
| 双语 | `README.md`（中）＋ `README_EN.md`（英，含作者三重资质） |
| 开源礼仪 | `CONTRIBUTING.md` / `SECURITY.md` / `BRANCH_PROTECTION.md` 齐备 |

---

## 二、日常改动的提交流程（轻量分支保护下）

轻量保护**只要求 PR 合入前状态检查通过**，不禁止直接 `git push` 到 `main`。两种走法任选：

### 走法 A — 直接 push（小改动、你已本地自测过）
```bash
cd /Users/vickywu/WorkBuddy/2026-08-14-14-21-56/projects/law-cli

# 1) 本地自测（等价于 CI 的 test 作业）
python3 tests/test_law_cli.py
python3 law_cli.py verify --gate; echo "gate exit=$?"

# 2) 提交
git add -A
git commit -m "docs/fix: <一句话说明本次改动>"

# 3) 推送（轻量保护允许直接 push main）
git push
```

### 走法 B — 走 PR（推荐用于非平凡改动，让 CI 先跑）
```bash
cd /Users/vickywu/WorkBuddy/2026-08-14-14-21-56/projects/law-cli

# 1) 开特性分支
git checkout -b feat/<简短描述>

# 2) 改动 + 本地自测
python3 tests/test_law_cli.py
python3 law_cli.py verify --gate; echo "gate exit=$?"

# 3) 提交并推送分支
git add -A
git commit -m "feat: <说明>"
git push -u origin feat/<简短描述>

# 4) 在 GitHub 提 PR 到 main → 等 CI(test) 变绿 → Merge
```
> 轻量保护下，PR 合入前会强制要求 `test` 状态检查通过；直接 push 不受影响。

---

## 三、发布 / 更新对外产物（已做过，留作复刻参考）

### 1) 发 Release（v1.0 已发，后续发 vX.Y 时）
- GitHub 仓库 → **Releases → Draft a new release**
- Tag：`v1.1`（递增），标题：`law-cli v1.1 — AI 终核中文地方法规 CLI`
- 正文：直接粘贴仓库内 `RELEASE_NOTES.md` 内容（按需更新版本号/计数）
- 点 **Publish release**

### 2) 更新文档站（GitHub Pages 已开）
- 文档源即 `main` 分支的 `/docs` 目录，首页 `docs/index.md`。
- 改完 `docs/` 下任意 `.md` → 提交并 push → Pages 自动重建（约 1–2 分钟）。
- 站点地图 / 开启步骤见 `docs/SITE_GUIDE.md`。

### 3) 分支保护（当前 = 轻量，已生效）
- Settings → Branches → `main` → **Require status checks to pass before merging** ✓（已勾选 `test`）
- 未勾选「Restrict pushes that create files」「Require branches to be up to date」等，故直接 push 仍可用。
- 完整方案（禁直接 push、强制 PR）见 `docs/BRANCH_PROTECTION.md`，按需升级。

---

## 四、新增一部法 / 一批条文（数据贡献）

1. 从官方源（`flk.npc.gov.cn` / `gov.cn` 系列）人工保存 UTF-8 全文文本到 `seed/`。
2. 用 `law_cli.py` 子命令入库并做逐字对账：
   ```bash
   python3 law_cli.py verify --reconcile   # 与官方种子逐字对账
   python3 law_cli.py verify              # 防篡改 219+新增/219+新增 完好
   python3 law_cli.py verify --gate       # 无 pending → exit 0
   ```
3. 新增记录默认 `review_status` 经 AI 逐字对账后标 `ai_verified`（**AI 审核即终核**，无需律师签署）。
4. 补齐 `docs/compliance/05_数据来源与核验记录.md` 对应行 + 在 `RELEASE_NOTES.md` / README 更新计数。
5. 跑测试、提交、按第二节流程推送。

---

## 五、红线（不可破）

- **数据来源须为政府官方域**（白名单见 `law_cli.py` `OFFICIAL_DOMAINS`：`gov.cn` / `npc.gov.cn` / `flk.npc.gov.cn` / `nppa.gov.cn` / `court.gov.cn`）；商业库（北大法宝/威科/法信）文本仅可作评测样本，**不得**进入 `data/law_db.json`。
- **不得**出现「待律师复核 / 须律师签署 / 具名签署」等强制表述（口径已统一为 AI 终核）；历史叙述可用「口径更新」横幅说明。
- **不得**把虚构草稿（`项目构思_虚构草稿.md`，已被 `.gitignore` 排除）混入本真实态仓库。
- 任何改动合入前，`verify --gate` 必须 exit 0（无 `pending` 残留）。

---

## 附：本机环境提示（非必读）
- 仓库路径：`/Users/vickywu/WorkBuddy/2026-08-14-14-21-56/projects/law-cli`
- Python：`python3`（系统 3.8.9 即可，CI 用 3.x 标准库，无第三方依赖）
- 远程：`origin` → `git@github.com:vickywu97/law-cli.git`
- 若 `git push` 遇 `LibreSSL SSL_connect: Operation timed out` / `HTTP2 framing`：
  确认 `~/.ssh/config` 含 `Host github.com / Hostname ssh.github.com / Port 443 / User git`，或临时 `git config --global http.proxy http://127.0.0.1:7890`。push 失败不丢提交，先 `git status -sb` 确认 ahead 数再重试。
