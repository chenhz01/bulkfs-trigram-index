# Alignment Audit (Rules 85-100 / 16 items)

Repo: bulkfs-trigram-index · Audited: 2026-10-11 · v0.1.1

| # | Check | Status | Evidence |
|---|-------|--------|----------|
| 1 | Safety/Ethics section | N/A | Non-security-domain file tool. |
| 2 | Privacy/zero secrets | PASS | No keys/tokens/real names; index stores local paths only. |
| 3 | Copyright boundary | PASS | Primitives re-described generically (bulk enumeration/delta/trigram); no copied source text >50 chars; MIT LICENSE present. |
| 4 | Fact-source labeling | PASS | All latency figures [measured] with repro; native 0.1 ms figure explicitly [estimated] context. |
| 5 | Confidence grading | PASS | Portability claim High (17-case self-test); latency-parity claim Medium with reason. |
| 6 | Minimal Fallback | PASS | `find` primitive + delta-classifier-without-SQLite chain. |
| 7 | Quickstart timing | PASS | ~10 s minimal example, ~6 s self-test, staged; build cost scaling noted. |
| 8 | Design trade-offs/priorities | PASS | portability > zero-dependency > freshness > raw latency, with consequences. |
| 9 | CHANGELOG ≥2 iterations | PASS | v0.1.0 → v0.1.1; correctness delta (latency honesty + mtime fix) documented. |
| 10 | Exemption (session rule) | N/A | Session-level; static repo. |
| 11 | Time-sensitive data dated | PASS | Footer "as of 2026-10-11". |
| 12 | Core assumptions ≥3 | PASS | 4 assumptions at README end. |
| 13 | Three-class self-test | PASS | A functional (6), B error paths (5), C edges (6 incl. empty tree, 200-char name, unicode); all PASS. Repro: `python self_test.py`. |
| 14 | When NOT to use | PASS | FAQ Q3: constant churn, millions of files, content ranking. |
| 15 | ≥2 iterations traceable | PASS | v0.1.1 correctness delta ≥20% (latency claims + detection fix). |
| 16 | ≤60-word first screen | PASS | First paragraph 55 words with a "for you?" judgment. |
