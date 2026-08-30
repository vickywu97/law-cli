# Contributing to law-cli

Thanks for your interest in law-cli. This document explains how to propose changes.

## Branching model

`main` is a **protected branch**. Direct push is disabled; all changes go through a pull request:

```bash
git checkout -b feat/your-change
# ... edit, commit ...
git push -u origin feat/your-change
# open a PR on GitHub; CI (test) must pass before merge
```

See [`docs/BRANCH_PROTECTION.md`](docs/BRANCH_PROTECTION.md) for the exact protection rules.

## Before opening a PR

- Run the test + gate locally:
  ```bash
  python3 tests/test_law_cli.py     # 15/15 expected
  python3 law_cli.py verify --gate  # exit 0
  ```
- CI (`.github/workflows/ci.yml`, job `test`) runs the same two checks on every PR — a red check blocks merge.

## Code conventions

- **Standard library only.** No third-party runtime dependencies. If you think a dependency is unavoidable, open an issue first to discuss.
- Type hints and clear docstrings are encouraged.
- Keep `law_cli.py` the single CLI entry; add subcommands via `build_parser()` + `cmd_<name>`.

## Data contributions (statute records)

All statute data follows strict compliance rules — do **not** bypass them:

1. **Official source only.** Source URL must be on the official-domain whitelist (`flk.npc.gov.cn`, `*.gov.cn`, `npc.gov.cn`, `nppa.gov.cn`, `court.gov.cn`). Commercial databases (pkulaw / wkinfo / etc.) are rejected.
2. **Public-domain text only.** Per Article 5 of the *Copyright Law*, statute texts are public domain; extract article text only — never copy a database's annotations, classifications, or effect notes.
3. **Complete provenance chain.** Every record needs source URL + promulgation date + effective date + retrieval date + SHA-256.
4. **AI audit is the final review.** `review_status=ai_verified` is the terminal state; no lawyer manual signature is required. See [`docs/compliance/03_AI审核终核声明.md`](docs/compliance/03_AI审核终核声明.md).
5. **Nothing constitutes legal advice.** All outputs keep their disclaimer banner.

## Commit messages

Conventional, scannable messages are appreciated (e.g. `feat:`, `fix:`, `docs:`, `test:`, `chore:`).

## Questions

Open an issue, or reach the maintainer via LinkedIn <https://www.linkedin.com/in/wuyitong> / email <vickywu97@163.com>.
