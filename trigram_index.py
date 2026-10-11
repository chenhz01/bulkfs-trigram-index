#!/usr/bin/env python3
"""bulkfs-trigram-index: portable whole-tree filename search.

Three primitives composed into a local search layer (the pattern proven by
macOS getattrlistbulk-based tools, rebuilt portably with stdlib only):
  1. bulk enumeration   - os.walk once over the tree (the portable stand-in
                          for getattrlistbulk batched enumeration)
  2. event-style delta  - a rescan pass that classifies added/removed/changed
                          via (size, mtime) fingerprints (portable FSEvents
                          stand-in; point it at the same root periodically)
  3. trigram index      - a sqlite3-backed trigram inverted index with
                          fault-tolerant AND-matching

Pure stdlib. Cross-platform. No daemon.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time

SCHEMA = """
CREATE TABLE IF NOT EXISTS files (
    path   TEXT PRIMARY KEY,
    size   INTEGER,
    mtime  REAL
);
CREATE TABLE IF NOT EXISTS trigrams (
    tri    TEXT,
    path   TEXT
);
CREATE INDEX IF NOT EXISTS idx_tri ON trigrams(tri);
CREATE INDEX IF NOT EXISTS idx_path ON trigrams(path);
"""


class IndexError_(Exception):
    pass


def _trigrams(s: str) -> list[str]:
    s = s.lower()
    if len(s) < 3:
        return [s] if s else []
    return [s[i:i + 3] for i in range(len(s) - 2)]


class TrigramIndex:
    def __init__(self, db_path: str):
        d = os.path.dirname(os.path.abspath(db_path))
        if not os.path.isdir(d):
            raise IndexError_(f"directory does not exist: {d}")
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        try:
            self.conn.executescript(SCHEMA)
        except sqlite3.DatabaseError as exc:
            raise IndexError_(f"corrupted index file: {exc}") from exc
        self.conn.commit()

    # ---------------- 1) bulk build
    def build(self, root: str) -> dict:
        if not os.path.isdir(root):
            raise IndexError_(f"not a directory: {root}")
        t0 = time.perf_counter()
        files: list[tuple[str, int, float]] = []
        for cur, dirs, names in os.walk(root):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for n in names:
                if n.startswith("."):
                    continue
                p = os.path.join(cur, n)
                try:
                    stt = os.stat(p)
                    files.append((p, stt.st_size, stt.st_mtime))
                except OSError:
                    continue  # vanished mid-walk
        self.conn.execute("DELETE FROM files")
        self.conn.execute("DELETE FROM trigrams")
        self.conn.executemany("INSERT OR IGNORE INTO files VALUES (?,?,?)", files)
        tri_rows = [(t, p) for p, _sz, _mt in files for t in set(_trigrams(os.path.basename(p)))]
        self.conn.executemany("INSERT INTO trigrams VALUES (?,?)", tri_rows)
        self.conn.commit()
        return {"files": len(files), "trigram_rows": len(tri_rows),
                "build_s_measured": round(time.perf_counter() - t0, 3),
                "db_bytes": os.path.getsize(self.db_path)}

    # ---------------- 2) delta rescan (event-style)
    def update(self, root: str) -> dict:
        if not os.path.isdir(root):
            raise IndexError_(f"not a directory: {root}")
        seen: dict[str, tuple[int, float]] = {}
        for cur, dirs, names in os.walk(root):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for n in names:
                if n.startswith("."):
                    continue  # same exclusion rule as build
                p = os.path.join(cur, n)
                try:
                    stt = os.stat(p)
                    seen[p] = (stt.st_size, stt.st_mtime)
                except OSError:
                    pass
        old = dict(self.conn.execute("SELECT path, size FROM files"))
        old_mt = dict(self.conn.execute("SELECT path, mtime FROM files"))
        added = [p for p in seen if p not in old]
        removed = [p for p in old if p not in seen]
        changed = [p for p in seen if p in old and seen[p] != (old[p], old_mt[p])]
        for p in removed + changed:
            self.conn.execute("DELETE FROM files WHERE path=?", (p,))
            self.conn.execute("DELETE FROM trigrams WHERE path=?", (p,))
        for p in added + changed:
            sz, mt = seen[p]
            self.conn.execute("INSERT OR REPLACE INTO files VALUES (?,?,?)", (p, sz, mt))
            self.conn.executemany("INSERT INTO trigrams VALUES (?,?)",
                                  [(t, p) for t in set(_trigrams(os.path.basename(p)))])
        self.conn.commit()
        return {"added": len(added), "removed": len(removed), "changed": len(changed)}

    # ---------------- 3) query
    def query(self, text: str, k: int = 20) -> tuple[list[str], dict]:
        if not text or not text.strip():
            raise IndexError_("empty query")
        tris = _trigrams(text)
        t0 = time.perf_counter()
        sets = []
        for t in tris:
            rows = [r[0] for r in self.conn.execute(
                "SELECT path FROM trigrams WHERE tri=?", (t,))]
            sets.append(set(rows))
        if not sets:
            return [], {"latency_ms_measured": 0.0, "candidates": 0, "trigrams": 0}
        cand = set.intersection(*sets)
        # substring refine (trigrams are necessary but not sufficient)
        hits = sorted(p for p in cand if text.lower() in os.path.basename(p).lower())[:k]
        latency = (time.perf_counter() - t0) * 1000.0
        return hits, {"latency_ms_measured": round(latency, 3),
                      "candidates": len(cand), "trigrams": len(tris)}

    def stats(self) -> dict:
        n = self.conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        t = self.conn.execute("SELECT COUNT(*) FROM trigrams").fetchone()[0]
        return {"files": n, "trigram_rows": t,
                "db_bytes": os.path.getsize(self.db_path)}

    def close(self):
        self.conn.close()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="bulkfs-trigram-index",
                                description="portable filename trigram search over a directory tree")
    p.add_argument("--db", default="fsindex.db")
    sub = p.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="full build from a root")
    b.add_argument("--root", required=True)
    u = sub.add_parser("update", help="delta rescan (added/removed/changed)")
    u.add_argument("--root", required=True)
    q = sub.add_parser("query", help="substring search over filenames")
    q.add_argument("--text", required=True)
    q.add_argument("--k", type=int, default=20)
    sub.add_parser("stats")

    a = p.parse_args(argv)
    try:
        ix = TrigramIndex(a.db)
        if a.cmd == "build":
            print(json.dumps(ix.build(a.root), indent=2))
        elif a.cmd == "update":
            print(json.dumps(ix.update(a.root), indent=2))
        elif a.cmd == "query":
            hits, meta = ix.query(a.text, a.k)
            print(json.dumps({"meta": meta, "hits": hits}, indent=2))
        elif a.cmd == "stats":
            print(json.dumps(ix.stats(), indent=2))
        ix.close()
        return 0
    except IndexError_ as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except sqlite3.DatabaseError as exc:
        print(f"error: index problem: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
