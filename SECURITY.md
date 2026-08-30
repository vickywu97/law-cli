# Security Policy

## Scope

law-cli is a **read-only, offline statute-lookup CLI** over publicly available (public-domain) Chinese legal texts. It:

- Stores no secrets, credentials, or personal data.
- Makes no network calls in normal operation (online fetch is opt-in and only does a single GET on a user-supplied exact official URL).
- Ships only statute texts sourced from official government domains.

## Reporting a vulnerability

If you discover a security issue (e.g. an unintended network call, a dependency/Supply-chain concern, or a data-integrity bug that could return tampered text), please report it **privately** rather than opening a public issue:

- Email: **vickywu97@163.com**
- LinkedIn: <https://www.linkedin.com/in/wuyitong>

Please include:
- A description of the issue and its impact.
- Steps to reproduce (or a proof-of-concept).
- Your suggested remediation, if any.

We aim to acknowledge within a few business days and will coordinate a fix and disclosure timeline with you.

## Data integrity

Every statute record carries a SHA-256 and a provenance chain; `law verify` detects tampering, and `law verify --gate` blocks release when any record is unreviewed. If you believe a record's text or source is wrong, open an issue with the official source URL so it can be reconciled.

## Responsible disclosure

Please give us a reasonable window to address the issue before any public disclosure. This is a personal/portfolio project, so timelines may be flexible — we appreciate your patience and credit contributors who report responsibly.
