# law-cli 发布前核对与提交指引（用户 Mac 执行）

> 本文件是给**你（用户）在本机终端**逐步执行的 runbook。
> 本回合所有改动**当前均为本地 modified / untracked、未 commit**。下面每一步都先 `git status` 复核再动作。
>
> **口径更新（2026-08-28 用户明确）**：律师**不需要**人工复核签署，**AI 审核即终核**。`review_status=ai_verified` 即视为已审核通过，可直接发布。

---

## 第 0 步（红线，必须先做）：AI 审核终核确认

本回合 AI 已完成且已实跑验证：

- **全库 219 条 100% AI 审核通过**：`review_status` 全部 `ai_verified`（上海 130 = 65 基线 + 65 修正 / 北京 79 / 著作权 10）。
- **逐字对账**：每一条均对其官方源（上海 2019 全文 / 北京 2020 全文 / 著作权法 2020 & 2010 总则第 1–5 条官方原文）逐字比对。
- **数据修复**：北京 12 条（第 49、65–75 条）文本截断损坏，已用官方 2020 全文补全并重算 sha256；上海 2026 版相对 2019 基线仅在 §十一 4 处修正点（第 1/21/37/57 条）有实质改动、0 伪差。
- **防篡改**：`verify` 报告 219/219 完好、0 篡改。
- **发布闸门**：`verify --gate` 已改为"仅 `pending` 才拦截"，全库无 `pending`，故 **exit 0（通过）**。

**结论**：证据链完整、AI 审核已终核，无需律师签署即可发布。

---

## 第 1 步：进入仓库并复核状态

```bash
cd /Users/vickywu/WorkBuddy/2026-08-14-14-21-56/projects/law-cli
git status -sb
```

预期：看到 `M` 的 README.md / data/law_db.json / law_cli.py / docs/compliance/01_商业库样本隔离说明.md / 核验执行指引_律师操作版.md / 核验自审清单_律师自用.md / 律师复核签署KB_真实态KB.md（注意：实际文件名无"签署"后的下划线，为 `律师复核签署KB_真实态KB.md`），以及 `??` 的一批脚本与文档（见第 3 步清单）。
请先肉眼确认这些就是你本回合认可的改动，**不要** `git add -A` 一把梭。

## 第 2 步：跑发布闸门（必须在 commit 前）

```bash
cd /Users/vickywu/WorkBuddy/2026-08-14-14-21-56/projects/law-cli
/Users/vickywu/.workbuddy/binaries/python/versions/3.13.12/bin/python3 law_cli.py verify
/Users/vickywu/.workbuddy/binaries/python/versions/3.13.12/bin/python3 law_cli.py verify --gate
echo "gate exit=$?"
```

- 第一条：anti-tamper 应 `219 条，被篡改 0 条`。
- 第二条：`--gate` 应 **exit 0（通过）**——全库 219 条均 `ai_verified`，无 `pending`。

## 第 3 步：暂存指定文件（逐个 add，不用 -A）

```bash
cd /Users/vickywu/WorkBuddy/2026-08-14-14-21-56/projects/law-cli
# 稳健做法：用 git add -u 暂存所有"已跟踪且已修改"的文件（避开中文文件名 NFD/NFC 归一化导致的路径匹配失败）
git add -u
# 或逐个指定（注意真实文件名为 律师复核签署KB_真实态KB.md，无"签署"后的下划线）：
# git add README.md data/law_db.json law_cli.py docs/compliance/01_商业库样本隔离说明.md 核验执行指引_律师操作版.md 核验自审清单_律师自用.md "律师复核签署KB_真实态KB.md"
git add ai_audit_all.py close_O1_shanghai_2026.py fix_lineage_consistency.py fix_shanghai_provenance.py gen_copyright_kb.py ingest_baseline_shanghai_2019.py mark_ai_verified_shanghai2026.py verify_shanghai_a1.py
git add law-cli_改进诊断与方案.md "上海生活垃圾条例2026修正_AI核对报告.md" "发布前核对与提交指引_用户Mac执行.md" tests/
git status -sb
```

复核 `git status`：应只剩你认可的文件在 "Changes to be committed"，无意外文件。（`__pycache__/`、`.pyc` 已被 `.gitignore` 排除。）

## 第 4 步：提交（写明本回合范围）

```bash
cd /Users/vickywu/WorkBuddy/2026-08-14-14-21-56/projects/law-cli
git commit -m "law-cli: 根因级改进 + 全库 AI 审核终核（219/219 ai_verified）

- law_cli.py: schema v2 迁移(lineage/review_status); verify --reconcile 官方逐字对账(逐条逐版本+条序校验); verify --gate 改为仅 pending 拦截(AI审核即终核); fetch 来源白名单(移除失效 spcsc.sh.cn, 增 flk.npc.gov.cn); cn_to_int 支持百/千; show 增 --version 过滤
- ai_audit_all.py: 按 law+version 选官方源逐字对账 + 截断自动补全(北京12条修复) + 不一致保留 pending
- fix_lineage_consistency.py: 修 2026 版 baseline_version_tag 悬空指针、基线 reconciliation 过度陈述
- fix_shanghai_provenance.py / ingest_baseline_shanghai_2019.py / mark_ai_verified_shanghai2026.py / close_O1_shanghai_2026.py / gen_copyright_kb.py / verify_shanghai_a1.py: 证据链纠错、2019基线入库、O1 关闭管线等
- data/law_db.json: 219 条全部 ai_verified, 北京截断修复, 防篡改 219/219 完好
- tests/test_law_cli.py: 15/15 通过(含 gate / whitelist / show --version 回归)
- 文档同步: README / 诊断文档 §7.6–§7.7 / 律师操作指引(去除失效 spcsc 引用)"
```

## 第 5 步：提交后再核验一次

```bash
cd /Users/vickywu/WorkBuddy/2026-08-14-14-21-56/projects/law-cli
git status -sb
/Users/vickywu/.workbuddy/binaries/python/versions/3.13.12/bin/python3 law_cli.py verify | head -1
/Users/vickywu/.workbuddy/binaries/python/versions/3.13.12/bin/python3 law_cli.py verify --gate; echo "gate exit=$?"
```

应仍 `219 条，被篡改 0 条` 且 `gate exit=0`。

## 第 6 步：push（如已配置远程）

```bash
cd /Users/vickywu/WorkBuddy/2026-08-14-14-21-56/projects/law-cli
git log --oneline -3
git remote -v
```

- 若 `git remote -v` 输出为空（当前即如此）：说明本仓**未配置远程**，push 无从谈起。请先在 GitHub 建仓（仓库名 `law-cli`，与本地一致），再 `git remote add origin git@github.com:vickywu97/law-cli.git`（SSH 443 配置见下），然后 `git push -u origin main`。
- 若已配置远程，直接：

```bash
cd /Users/vickywu/WorkBuddy/2026-08-14-14-21-56/projects/law-cli
git push -u origin main
```

> 若 `git push` 遇 `LibreSSL SSL_connect: Operation timed out` / `HTTP2 framing`：
> 改用 SSH 走 443——先确认 `~/.ssh/config` 含：
> ```
> Host github.com
>   Hostname ssh.github.com
>   Port 443
>   User git
> ```
> 且远程为 `git@github.com:vickywu97/law-cli.git`；或临时 `git config --global http.proxy http://127.0.0.1:7890`。push 失败不丢提交，先 `git status -sb` 确认 ahead 数再重试。

---

## O1 状态（已于 2026-08-28 关闭）

用户提供的 `上海市生活垃圾管理条例_2019通过_全文_官方原文.txt` 经核验即为 2026 修正全文（含 §十一 4 处修订），O1 已据此关闭，无需另寻 canonical 源；`ai_audit_all.py` 已对全库 219 条完成 AI 审核。
