# main 分支保护配置说明

> 目的：防止误推、保证 **CI 绿了才能合入**，让公开仓库的 `main` 始终处于可发布状态。
> 适用仓库：`vickywu97/law-cli`（GitHub Web UI 操作；文末附 `gh` CLI 等价命令）。

---

## ⚠️ 先读：开启后会改变你的推送习惯

标准分支保护会 **禁止直接 `git push` 到 `main`**。你目前的习惯是「本地 commit 在 main → `git push`」，
开启后将**被拒绝**。新流程变为：

```bash
# 1) 在功能分支上工作
git checkout -b docs/fix-xxx
# ... 编辑、本地 commit ...
git push -u origin docs/fix-xxx

# 2) 到 GitHub 开 PR（Pull Request）→ 等 CI（test）变绿
# 3) 合入 main（Squash / Merge 都行）
```

若你**只想防误推、但仍要保留直接 push main 的便利**，见文末「轻量方案」。

---

## 一、Web UI 步骤（推荐：完整保护）

1. 仓库 **Settings → Branches**（左侧栏）。
2. 点 **Add branch protection rule**（或 "Add classic branch protection rule"）。
3. **Branch name pattern** 填 `main`。
4. 勾选以下项（其余保持默认）：

| 设置项 | 勾选 | 说明 |
|--------|------|------|
| **Require a pull request before merging** | ✅ | 禁止直接 push，强制走 PR |
| Require approvals | ✅（数量 `1`） |  solo 仓库可自审；核心是 CI 闸门 |
| **Require status checks to pass before merging** | ✅ | 见下，选 `test` |
| Status checks — `test` | ✅ 选中 | CI 工作流 `.github/workflows/ci.yml` 的 job 名就是 `test` |
| **Require branches to be up to date before merging** | ✅ | 合入前必须基于最新 main |
| **Do not allow bypassing the above settings** | ✅ | 包括管理员也不能绕过 |
| **Block force pushes** | ✅ | 禁止 `--force` 覆盖历史 |
| **Block deletions** | ✅ | 禁止误删分支 |

5. 点 **Create / Save**。

---

## 二、`gh` CLI 等价命令（可选）

```bash
gh api repos/vickywu97/law-cli/branches/main/protection \
  --method PUT \
  -f "required_pull_request_reviews[required_approving_review_count]=1" \
  -f "required_status_checks[strict]=true" \
  -f "required_status_checks[contexts][]=test" \
  -f "enforce_admins=true" \
  -f "required_linear_history=true"
```

> `required_status_checks.contexts` 必须与 CI 的 job 名完全一致（此处为 `test`），否则 PR 永远卡在
> "waiting for status checks"。

---

## 三、轻量方案（保留直接 push，只防误推）

如果你不想改推送习惯，可只勾这两项，仍允许 `git push` 直接上 main：

- ✅ **Require status checks to pass before merging**（选 `test`）
- ✅ **Block force pushes**

> 不勾 "Require a pull request before merging"，因此直接 push 仍可行，但**强制推送被禁**且
> 合入前需 CI 通过（仅对 PR 生效；直接 push 不会触发"必须绿"的硬性拦截，仅作为记录）。

---

## 四、验证

- 开启后，尝试 `git push` 到 main 应被拒（完整方案）或 `--force` 被拒（轻量方案）。
- 开一个测试 PR，确认 `test` 检查出现并需变绿才能合并。
- CI 定义见 `.github/workflows/ci.yml`（job 名 `test`：`tests/test_law_cli.py` 15/15 + `verify --gate`）。
