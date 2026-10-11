#!/usr/bin/env python3
"""self_test for bulkfs-trigram-index. Three classes (rule 97).
Run: python self_test.py
"""
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trigram_index as m  # noqa: E402

RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))


def make_tree(root: str):
    for rel in ["report_2026_q3.pdf", "meeting_notes.txt", "MEETING-RECording.mp3",
                "deep/nested/path/data_export_v2.csv", "Photo.JPG", "empty_dir/.keep"]:
        p = os.path.join(root, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            f.write("x" * (len(rel) % 7))


def main() -> int:
    td = tempfile.mkdtemp()
    root = os.path.join(td, "tree")
    make_tree(root)
    db = os.path.join(td, "idx.db")
    ix = m.TrigramIndex(db)

    # ---------------- A. functional
    st = ix.build(root)
    check("A1 build indexes all visible files", st["files"] == 5, str(st))
    hits, meta = ix.query("meeting")
    check("A2 query finds meeting files (case-insensitive)",
          len(hits) == 2, str(hits))
    hits, meta = ix.query("data_export")
    check("A3 finds deeply nested file", any("data_export_v2" in h for h in hits))
    check("A4 meta reports measured latency",
          "latency_ms_measured" in meta and meta["latency_ms_measured"] >= 0)
    os.remove(os.path.join(root, "Photo.JPG"))
    with open(os.path.join(root, "new_note.txt"), "w") as f:
        f.write("hi")
    delta = ix.update(root)
    check("A5 delta detects add+remove", delta["added"] == 1 and delta["removed"] == 1,
          str(delta))
    hits, _ = ix.query("new_note")
    check("A6 post-update query sees new file", len(hits) == 1)

    # ---------------- B. error paths
    try:
        ix.query("")
        check("B1 empty query raises", False)
    except m.IndexError_:
        check("B1 empty query raises", True)
    check("B2 build on nonexistent root raises",
          _raises(lambda: ix.build(os.path.join(td, "nope"))))
    try:
        m.TrigramIndex(os.path.join(td, "missing_dir", "x.db"))
        check("B3 missing db dir raises", False)
    except m.IndexError_:
        check("B3 missing db dir raises", True)
    bad = os.path.join(td, "corrupt.db")
    with open(bad, "wb") as f:
        f.write(b"garbage bytes, not sqlite")
    try:
        m.TrigramIndex(bad)
        check("B4 corrupted index rejected", False)
    except m.IndexError_:
        check("B4 corrupted index rejected", True)
    check("B5 update on missing root raises",
          _raises(lambda: ix.update(os.path.join(td, "nope"))))

    # ---------------- C. extreme edges
    empty_root = os.path.join(td, "empty")
    os.makedirs(empty_root)
    st = ix.build(empty_root)
    check("C1 empty tree builds to zero files", st["files"] == 0)
    hits, _ = ix.query("xyz-no-match")
    check("C2 zero-hit query returns empty", hits == [])
    long_name = "L" * 200 + ".txt"
    with open(os.path.join(root, long_name), "w") as f:
        f.write("x")
    ix.update(root)
    hits, _ = ix.query("L" * 50)
    check("C3 200-char filename queryable via long substring", len(hits) == 1)
    hits, _ = ix.query("LLLL")
    check("C4 long-name found via prefix trigrams", len(hits) == 1)
    check("C5 1-2 char query handled (degenerate trigram)",
          isinstance(ix.query("ab")[0], list))
    unicode_root = os.path.join(td, "uni")
    os.makedirs(unicode_root)
    with open(os.path.join(unicode_root, "数据表_2026.xlsx"), "w") as f:
        f.write("x")
    ix.build(unicode_root)
    hits, _ = ix.query("数据表")
    check("C6 unicode filename queryable", len(hits) == 1)

    ix.close()
    shutil.rmtree(td, ignore_errors=True)
    fails = [r for r in RESULTS if not r[1]]
    for name, ok, detail in RESULTS:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  ({detail})" if detail else ""))
    print(f"\ntotal={len(RESULTS)} pass={len(RESULTS)-len(fails)} fail={len(fails)}")
    print("repro: python self_test.py")
    return 1 if fails else 0


def _raises(fn) -> bool:
    try:
        fn()
        return False
    except m.IndexError_:
        return True


if __name__ == "__main__":
    sys.exit(main())
