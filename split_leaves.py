"""Split data/leaves.csv into train/test WITHOUT leaking duplicate leaves.

The file contains identical rows, and also the same leaf recorded twice at
different decimal precision (a consequence of three merged sources, e.g.
line 21 "8.99,4.96" vs line 483 "9.0,5.0"). A row-level random split would
place such copies on opposite sides of the boundary, so the model would meet
the same physical leaf in train and again in test and report an optimistic
score that does not generalise.

Fix: cluster rows into leaf GROUPS, then split by group so every copy of a
leaf lands in exactly one of train or test -- never both.

Grouping rule (union-find, transitive):
  same tree type AND (exactly equal coords OR equal after rounding to 1 dp)

Usage:
  python split_leaves.py               # 80/20 split, writes 2 CSVs + report
  python split_leaves.py --dedupe      # collapse each group to one row first
  python split_leaves.py --frac 0.7    # different train fraction
"""
import argparse
import csv
import os
import random
from collections import Counter, defaultdict

SRC = os.path.join("data", "leaves.csv")
COLS = ["Leaf height", "Leaf width", "Tree type"]


def load(path):
    with open(path, newline="") as fh:
        rdr = csv.DictReader(fh)
        rows = []
        for i, rec in enumerate(rdr, start=2):
            rows.append(
                {
                    "line": i,
                    "h": float(rec["Leaf height"]),
                    "w": float(rec["Leaf width"]),
                    "t": rec["Tree type"].strip().lower(),
                    "raw": [rec[c] for c in COLS],
                }
            )
    return rows


class DSU:
    def __init__(self, n):
        self.p = list(range(n))

    def find(self, x):
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[rb] = ra


def build_groups(rows):
    """Union-find over 'is the same leaf' keyed on type + rounded coords."""
    dsu = DSU(len(rows))
    exact = defaultdict(list)   # full-precision key
    loose = defaultdict(list)   # 1dp key, catches cross-precision copies
    for idx, r in enumerate(rows):
        exact[(r["h"], r["w"], r["t"])].append(idx)
        loose[(round(r["h"], 1), round(r["w"], 1), r["t"])].append(idx)
    for bucket in list(exact.values()) + list(loose.values()):
        for other in bucket[1:]:
            dsu.union(bucket[0], other)
    groups = defaultdict(list)
    for idx in range(len(rows)):
        groups[dsu.find(idx)].append(idx)
    return list(groups.values())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frac", type=float, default=0.8, help="train fraction")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--dedupe", action="store_true",
                    help="keep one row per leaf group instead of all copies")
    a = ap.parse_args()

    rows = load(SRC)
    groups = build_groups(rows)

    dup_groups = [g for g in groups if len(g) > 1]
    print(f"rows: {len(rows)}   leaf groups: {len(groups)}   "
          f"groups holding >1 row: {len(dup_groups)}")
    print(f"redundant copies inside groups: "
          f"{sum(len(g) - 1 for g in dup_groups)}")
    sizes = Counter(len(g) for g in groups)
    print("group size histogram:", dict(sorted(sizes.items())))
    biggest = max(groups, key=len)
    if len(biggest) > 2:
        print(f"  largest group: {len(biggest)} rows -> lines "
              f"{[rows[i]['line'] for i in biggest]}")

    # Split whole groups, stratified by tree type. Groups never cross types
    # (type is part of the grouping key), so splitting within each class keeps
    # both the no-leak guarantee and the class proportions. Without this,
    # walnut landed at 15.5% of test vs 24.9% of the data and per-class scores
    # were misleading.
    rnd = random.Random(a.seed)
    train_idx, test_idx = [], []
    by_type = defaultdict(list)
    for g in groups:
        by_type[rows[g[0]]["t"]].append(g)
    for t, tgroups in sorted(by_type.items()):
        order = sorted(tgroups, key=lambda g: (rnd.random(), -len(g)))
        # count what will actually be written (dedupe collapses each group to 1)
        trows = sum(1 if a.dedupe else len(g) for g in tgroups)
        target = int(round(trows * a.frac))
        n_train = 0
        for g in order:
            keep = [g[0]] if a.dedupe else g
            if n_train < target:
                train_idx.extend(keep)
                n_train += len(keep)
            else:
                test_idx.extend(keep)

    def dump(path, idxs):
        idxs = sorted(idxs, key=lambda i: rows[i]["line"])
        with open(path, "w", newline="") as fh:
            wr = csv.writer(fh)
            wr.writerow(COLS)
            for i in idxs:
                wr.writerow(rows[i]["raw"])
        return len(idxs)

    ntr = dump(os.path.join("data", "leaves_train.csv"), train_idx)
    nte = dump(os.path.join("data", "leaves_test.csv"), test_idx)
    print(f"\nwrote data/leaves_train.csv ({ntr}) and data/leaves_test.csv ({nte})")
    print(f"train {ntr / (ntr + nte) * 100:.1f}% / test {nte / (ntr + nte) * 100:.1f}%")

    # ---- prove no leakage ------------------------------------------------
    def keys(idxs):
        return Counter((rows[i]["h"], rows[i]["w"], rows[i]["t"]) for i in idxs)

    def loose_keys(idxs):
        return Counter((round(rows[i]["h"], 1), round(rows[i]["w"], 1), rows[i]["t"])
                       for i in idxs)

    for name, fn in (("exact", keys), ("rounded-0.1", loose_keys)):
        shared = set(fn(train_idx)) & set(fn(test_idx))
        print(f"  {name} leaves in BOTH train and test: {len(shared)}")

    print("\nclass balance:")
    tr, te = Counter(rows[i]["t"] for i in train_idx), Counter(rows[i]["t"] for i in test_idx)
    for t in sorted(set(tr) | set(te)):
        print(f"  {t:<7} train {tr[t]:>4}  test {te[t]:>3}")


if __name__ == "__main__":
    main()
