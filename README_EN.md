# law-cli · Chinese Local-Regulation Statute Lookup CLI (Data-Compliance MVP)

[![CI](https://github.com/vickywu97/law-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/vickywu97/law-cli/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org)
[![Docs](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://vickywu97.github.io/law-cli/)
[![中文 README](https://img.shields.io/badge/README-中文-blue)](README.md)

> **✅ Real-data statement (reproducible-data project)**
> This repository is a **real, reproducible-data project**: statute texts are taken from official public channels (in the public domain per Article 5 of the *Copyright Law*), and every record carries a complete provenance chain (source URL / promulgation date / effective date / retrieval date / SHA-256), reproducible offline. Verification status per regulation is documented in [`docs/reports/地方性法规官方源调研.md`](docs/reports/地方性法规官方源调研.md) §2.1 / §2.2.
> The author's professional qualifications (lawyer / tax agent / patent attorney) do **not** add any warranty to this tool's output; official version determination and effect-status hints follow the official publications.

> **⚠️ Legal disclaimer**
> This tool only organizes publicly available statute texts. Effect-status hints follow official publications and **do not constitute legal advice**. Users must verify independently; for specific matters, consult a qualified lawyer.

---

## What this is

`law-cli` is the **minimal closed loop of the data layer** for a "statute lookup tool": it first solves the most sensitive IP link — the lawful acquisition, fixed sourcing, and reproducible proof of statute texts — before discussing lookup and effect annotation.

Commands implemented:

- `law fetch`: record an official text + complete provenance chain (source URL / promulgation date / effective date / retrieval date / SHA-256).
- `law show`: display an article + source + hash + disclaimer banner.
- `law verify`: check local data for tampering (anti-tamper). Extensions: `--reconcile --official <official full text> --law <law name>` does **official-source verbatim reconciliation (correctness)**; `--gate` is the **review gate** (non-zero exit if any unreviewed record exists — run before every release).
- `law fetch` hardening: source-domain **whitelist** (by default only official domains `*.gov.cn` / `npc.gov.cn` / `flk.npc.gov.cn` / `nppa.gov.cn` / `court.gov.cn`; hits on commercial databases such as wkinfo/pkulaw are rejected unless `--allow-non-official`); new `--lineage-*` and `--lineage-reorg-url` record the **amendment lineage** (baseline version/source, amendment decision, re-promulgated full text, effective date, reconciliation status).
- `law show` hardening: additionally shows `lineage` (amendment lineage) and `review_status` (review state / reviewer / date).
- `law versions <law.article>`: version axis — multiple versions side by side + diff (difflib, text-only).
- `law validity [law name]`: effect red/amber/green (self-determined from each version's `effective_date` and the current date).
- `law check <law name art. X>`: minimal citation check, returns the latest effective version's text and status.
- `law check-batch <file>`: batch-validate citations in a text file (one `law name art. X` per line), outputting per-line results + a summary (matched / unmatched / parse-failed). Local-only, no external access.
- `law relate <law.article> [--kb-path]`: query related clues in a local `verified-chinese-law-kb` (default `../verified-chinese-law-kb`); if the KB is absent, it says so clearly and never auto-scrapes third-party databases.

> ⚠️ **Source-compliance warning (measured)**: `.doc`/`.pdf` exports from commercial databases (e.g. wkinfo) contain statute text (public domain) but also embed their proprietary hyperlinks, "timeliness" annotations, etc. — protected value-added content forbidden by red line 4. This tool always uses the **official database (`flk.npc.gov.cn`)** as `source-url` and never treats a commercial export as the source.

Sample data: demonstrated with Articles 1–5 of the *Copyright Law*, covering both the **2010** and **2020** official versions (both public domain, manually saved from official channels), 10 records total. See also [`docs/reports/地方性法规官方源调研.md`](docs/reports/地方性法规官方源调研.md) (Beijing/Shanghai provincial pilots and official-source verification completed).

## Why this cut

- Validate the most uncertain link first: can official versions be stably acquired, can the provenance chain be fixed.
- Touch no third-party value-added content — lowest risk.
- Once working, naturally extend to version axis, effect red/amber/green, and bench citation checks.

## Compliance red lines (always on)

1. **Single official source**: national laws only from official public channels (National Laws & Regulations Database `flk.npc.gov.cn` / NPC website / State Council Gazette).
2. **Extract statute text only**: download/store no compilation structure, classification, annotations, or effect notes.
3. **Complete provenance chain**: source URL + promulgation date + effective date + retrieval date + SHA-256.
4. **No third-party value-added content**: never touch pkulaw, wkinfo, wusong, etc.
5. **No legal advice attached**: every output carries a disclaimer banner.
6. **Respect robots / ToS**: when automated scraping is forbidden, fall back to "manually save official text + record" (this MVP's `fetch --file` path); `--try-online` only does a single GET on a user-supplied exact official URL and saves it for human review — never auto-parses third-party structure.

## Copyright boundary of statute texts (Article 5, *Copyright Law*)

- Laws, regulations, and documents of a legislative/administrative/judicial nature from state organs, and their official translations, are **not subject to the Copyright Law** → statute texts are public domain, may be lawfully reproduced, but must use the **official version** and **cite the source**.
- An official gazette/database that merely compiles mechanically by time order lacks originality and is unprotected; but its **classification catalogs, navigation, topical compilations, article annotations, effect annotations, and case linkages** are copyright-protected and **must not be copied**.
- Conclusion: take only the article text; strip layout/annotations/notes.

## Quick start (zero dependencies, standard library only)

### Install (optional, reproducible / more professional)

```bash
git clone https://github.com/vickywu97/law-cli.git
cd law-cli
pip install -e .          # needs network to fetch the setuptools build backend; then `law-cli` is on PATH
law-cli verify --gate     # equivalent to python3 law_cli.py verify --gate
```

> Works without install too: `python3 law_cli.py <subcommand>` runs directly (pure stdlib; DB path is anchored to the module directory, so any CWD works).

### Use directly (zero install)

```bash
# 0) Prepare: manually save a law's official text from the National Laws & Regulations Database as UTF-8
# 1) Record (fetch) — import official text manually; the tool completes the provenance chain
python3 law_cli.py fetch \
  --law "中华人民共和国著作权法" \
  --file "seed/著作权法_2020修正_第1-5条_官方原文.txt" \
  --source-url "https://flk.npc.gov.cn/" \
  --publisher "全国人民代表大会常务委员会" \
  --published-date 2020-11-11 --effective-date 2021-06-01 \
  --version-tag "2020修正（第三次修正，主席令第六十二号）" \
  --articles 1-5

# 2) Show
python3 law_cli.py show "著作权法.5"      # single article
python3 law_cli.py show                    # list all

# 3) Verify (anti-tamper)
python3 law_cli.py verify

# 4) Version axis (needs multiple versions of the same article imported first)
python3 law_cli.py fetch --law "中华人民共和国著作权法" \
  --file "seed/著作权法_2010修正_第1-5条_官方原文.txt" \
  --source-url "https://www.nppa.gov.cn/.../t20160429_4556.html" \
  --publisher "全国人民代表大会常务委员会" --published-date 2010-02-26 \
  --effective-date 2010-04-01 --version-tag "2010修正（第二次修正，主席令第二十六号）" \
  --articles 1-5
python3 law_cli.py versions 著作权法.3      # both versions + diff

# 5) Effect red/amber/green
python3 law_cli.py validity 中华人民共和国著作权法

# 6) Citation check
python3 law_cli.py check "著作权法第5条"

# 7) Batch citation check (one citation per line)
python3 law_cli.py check-batch test_citations.txt

# 8) Relation query (local verified-chinese-law-kb)
KB=/path/to/verified-chinese-law-kb
python3 law_cli.py relate 公司法.1 --kb-path "$KB"
```

## Review stance: AI audit is the final check

The publisher's explicit decision: **AI audit is the final review — no lawyer manual signature required**. `review_status=ai_verified` is the terminal state. All statute texts are taken from official public channels (public domain per Article 5 of the *Copyright Law*), and every record carries a fixed complete provenance chain. Details in [`docs/compliance/03_AI审核终核声明.md`](docs/compliance/03_AI审核终核声明.md).

> ⚠️ Nothing in this repository constitutes legal advice; statute texts follow official publications, and specific matters should be referred to a qualified lawyer.

## About the author

Built by **Vicky Wu**, a trilingual (CN/EN/JP) legal-tech practitioner holding **three qualified professional credentials — PRC lawyer, tax agent, and patent attorney** — a rare combination at the intersection of law, tax, and IP. Currently building AI legal-compliance products (e.g. compliance-triangle) and legal-AI evaluation benchmarks (e.g. legal-hallucination-bench). This repo is both a real product and a portfolio artifact demonstrating the ability to (1) reason about law/tax/IP domains, (2) define and quantify AI quality (evaluation / scoring), and (3) ship runnable artifacts.

- LinkedIn: https://www.linkedin.com/in/wuyitong
- Email: vickywu97@163.com

## License

MIT — see [LICENSE](LICENSE).
