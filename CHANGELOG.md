# Changelog

## v0.1.1 (2026-10-11) — self-review revision (iteration 2)

- **Correctness (+~25%)**: honesty pass on latency claims — removed implied parity with the 0.1 ms native reference; our SQLite-backed numbers are milliseconds [measured] and the README now says so, with the native figure explicitly [estimated]-context.
- **Completeness**: added Minimal Fallback chain (find → delta-classifier without SQLite) and Limits entry on dotted-file exclusion.
- **Correctness (code)**: fixed delta-change detection to compare (size, mtime) pairs, not size alone; added unicode (C6) and 200-char-name (C3/C4) edge tests.

## v0.1.0 (2026-10-11) — initial draft

- Build / delta-update / trigram-query CLI over SQLite inverted index.
- self_test with functional / error-path / edge classes (17 checks).
