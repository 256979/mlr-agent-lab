"""Analyze data/leaves.csv: counts, height-vs-width scatter, anomalies.

Stdlib only (no pandas/matplotlib on this machine). Writes leaves_scatter.svg.
Column order per header: Leaf height, Leaf width, Tree type
"""
import csv
import statistics
from collections import Counter, defaultdict

PATH = "data/leaves.csv"
MARK = {"maple": "@", "walnut": "o", "cherry": "*"}


def load():
    rows, bad = [], []
    with open(PATH, newline="") as fh:
        for lineno, rec in enumerate(csv.DictReader(fh), start=2):
            raw_h = (rec.get("Leaf height") or "").strip()
            raw_w = (rec.get("Leaf width") or "").strip()
            typ = (rec.get("Tree type") or "").strip().lower()
            try:
                h, w = float(raw_h), float(raw_w)
            except ValueError:
                bad.append((lineno, raw_h, raw_w, typ))
                continue
            rows.append(
                {"n": lineno, "h": h, "w": w, "t": typ, "sh": raw_h, "sw": raw_w}
            )
    return rows, bad


def decimals(s):
    return len(s.split(".")[1]) if "." in s else 0


def main():
    rows, bad = load()
    print(f"rows parsed: {len(rows)}   unreadable: {len(bad)}")
    if bad:
        for b in bad[:10]:
            print(f"  line {b[0]}: {b[1]!r},{b[2]!r},{b[3]!r}")

    # ---- counts -------------------------------------------------------
    by_type = Counter(r["t"] for r in rows)
    print("\n=== leaves per type ===")
    for t, n in by_type.most_common():
        sub = [r for r in rows if r["t"] == t]
        hs = [r["h"] for r in sub]
        ws = [r["w"] for r in sub]
        print(
            f"  {t:<7} {n:>4}  ({n / len(rows) * 100:4.1f}%)   "
            f"height {min(hs):5.2f}-{max(hs):5.2f} (med {statistics.median(hs):5.2f})   "
            f"width {min(ws):5.2f}-{max(ws):5.2f} (med {statistics.median(ws):5.2f})"
        )
    odd_types = [t for t in by_type if t not in MARK]
    if odd_types:
        print(f"  !! unexpected type labels: {odd_types}")

    # ---- ASCII scatter ------------------------------------------------
    hs = [r["h"] for r in rows]
    ws = [r["w"] for r in rows]
    h0, h1 = min(hs), max(hs)
    w0, w1 = min(ws), max(ws)
    COLS, ROWS = 74, 28
    grid = defaultdict(list)
    for r in rows:
        c = int((r["w"] - w0) / (w1 - w0) * (COLS - 1))
        q = int((r["h"] - h0) / (h1 - h0) * (ROWS - 1))
        grid[(q, c)].append(r["t"])

    def band(v, lo, hi, edges):
        return {5.0: "5.0", 29.7: "30.0", 25.0: "25.0"}.get(v, f"{v:.0f}")

    print("\n=== scatter: height (y) vs width (x)   @ maple  o walnut  * cherry  # mixed ===")
    print(f"       width {w0:.1f} {'-' * 40} {w1:.1f}")
    for q in range(ROWS - 1, -1, -1):
        hline = h0 + q * (h1 - h0) / (ROWS - 1)
        cells = []
        for c in range(COLS):
            ts = grid.get((q, c))
            if not ts:
                cells.append(" ")
            elif len(set(ts)) == 1:
                cells.append(MARK.get(ts[0], "?"))
            else:
                cells.append("#")
        lbl = f"{hline:5.1f} |" if q % 4 == 0 or q == ROWS - 1 else "      |"
        print(f"{lbl}{''.join(cells)}")

    # ---- correlations -------------------------------------------------
    print("\n=== height vs width correlation (Pearson r) ===")
    for t in sorted(by_type):
        sub = [r for r in rows if r["t"] == t]
        if len(sub) < 3:
            continue
        a = [r["h"] for r in sub]
        b = [r["w"] for r in sub]
        ma, mb = statistics.mean(a), statistics.mean(b)
        num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
        den = (sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b)) ** 0.5
        r = num / den if den else float("nan")
        ratio = [y / x for x, y in zip(a, b)]
        print(
            f"  {t:<7} r={r:+.3f}  n={len(sub):>4}   "
            f"width/height median {statistics.median(ratio):.2f}"
        )
    a, b = hs, ws
    ma, mb = statistics.mean(a), statistics.mean(b)
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    den = (sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b)) ** 0.5
    print(f"  {'ALL':<7} r={num / den:+.3f}  n={len(rows):>4}   <-- pooled, see note")

    # ---- anomalies ----------------------------------------------------
    print("\n=== anomalies ===")

    dups = Counter((r["sh"], r["sw"], r["t"]) for r in rows)
    dup_sets = {k: v for k, v in dups.items() if v > 1}
    extra = sum(v - 1 for v in dup_sets.values())
    print(
        f"  exact duplicate rows: {extra} redundant of {len(rows)} "
        f"({extra / len(rows) * 100:.1f}%), across {len(dup_sets)} distinct values"
    )
    shown = 0
    for (sh, sw, t), v in dup_sets.items():
        if v >= 3 and shown < 6:
            lines = [r["n"] for r in rows if (r["sh"], r["sw"], r["t"]) == (sh, sw, t)]
            print(f"    {sh},{sw},{t} x{v} at lines {lines}")
            shown += 1

    jitter = Counter(decimals(r["sh"]) for r in rows)
    print("  decimal precision of height values: "
          + ", ".join(f"{d}dp={n}" for d, n in sorted(jitter.items()))
          + "   <-- mixed precision = merged sources")

    flipped = [r for r in rows if r["w"] > r["h"]]
    print(f"  width > height (unusual for a leaf): {len(flipped)} rows")
    for r in flipped[:12]:
        print(f"    line {r['n']}: h={r['h']:.2f} w={r['w']:.2f} {r['t']}")

    print("  per-type outlier candidates (Tukey 1.5*IQR on each axis):")
    for t in sorted(by_type):
        sub = [r for r in rows if r["t"] == t]
        for axis in ("h", "w"):
            vals = sorted(r[axis] for r in sub)
            q1 = statistics.quantiles(vals, n=4)[0]
            q3 = statistics.quantiles(vals, n=4)[2]
            hi = q3 + 1.5 * (q3 - q1)
            outs = [r for r in sub if r[axis] > hi]
            for r in outs:
                ratio = r["w"] / r["h"]
                print(
                    f"    {t:<7} {axis}={r[axis]:5.2f} above fence {hi:5.2f}  "
                    f"line {r['n']:>3}  (other axis {r['w' if axis=='h' else 'h']:5.2f}, w/h {ratio:.2f})"
                )

    misfit = [r for r in rows if r["t"] == "cherry" and r["h"] > 14]
    print(f"  cherry with height > 14 (maple/walnut sized): {len(misfit)}")
    for r in misfit:
        print(f"    line {r['n']}: h={r['h']:.2f} w={r['w']:.2f}")

    walnut_big = [r for r in rows if r["t"] == "walnut" and r["w"] / r["h"] > 1.0]
    print(f"  walnut wider than tall: {len(walnut_big)}")
    for r in walnut_big:
        print(f"    line {r['n']}: h={r['h']:.2f} w={r['w']:.2f}")

    # ---- does the label match the shape? ------------------------------
    print("\n=== label vs shape (is anything mislabeled?) ===")
    prof = {}
    for t in sorted(by_type):
        sub = [r for r in rows if r["t"] == t]
        rt = sorted(r["w"] / r["h"] for r in sub)
        prof[t] = (statistics.median(rt), rt[0], rt[-1])
        print(
            f"  {t:<7} w/h median {prof[t][0]:.2f}  range {prof[t][1]:.2f}-{prof[t][2]:.2f}"
        )
    print("  rows whose w/h sits in another type's middle, far from its own:")
    for r in rows:
        ratio = r["w"] / r["h"]
        own = prof[r["t"]][0]
        best = min(prof, key=lambda t: abs(prof[t][0] - ratio))
        if best != r["t"] and abs(own - ratio) > 0.45 and abs(prof[best][0] - ratio) < 0.14:
            print(
                f"    line {r['n']:>3}: {r['t']:<7} h={r['h']:5.2f} w={r['w']:5.2f} "
                f"w/h={ratio:.2f}  looks like {best} (med {prof[best][0]:.2f}, own {own:.2f})"
            )

    # ---- is the duplication block-shaped? -----------------------------
    print("\n=== structure of the duplicated block ===")
    sig = [(r["sh"], r["sw"], r["t"]) for r in rows]
    first = sig[:24]
    hits = [i for i in range(len(sig) - 24) if sig[i : i + 24] == first]
    if hits:
        print(
            f"  lines 2-25 reappear verbatim starting at file rows "
            f"{[h + 2 for h in hits]} (offsets {[h for h in hits]})"
        )
    else:
        print("  no 24-row verbatim block; duplication is scattered")

    # ---- SVG scatter --------------------------------------------------
    PAD, W, H = 56, 760, 520
    pw, ph = W - 2 * PAD, H - 2 * PAD
    col = {"maple": "#c0392b", "walnut": "#7f5539", "cherry": "#1f77b4"}
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" font-family="Segoe UI, sans-serif" font-size="12">',
        f'<rect width="{W}" height="{H}" fill="#fbfbfd"/>',
    ]
    for i in range(0, 11):
        gx = PAD + i * pw / 10
        gy = PAD + i * ph / 10
        out.append(f'<line x1="{gx:.1f}" y1="{PAD}" x2="{gx:.1f}" y2="{H-PAD}" stroke="#e3e3ea"/>')
        out.append(f'<line x1="{PAD}" y1="{gy:.1f}" x2="{W-PAD}" y2="{gy:.1f}" stroke="#e3e3ea"/>')
        wv = w0 + i * (w1 - w0) / 10
        hv = h1 - i * (h1 - h0) / 10
        out.append(f'<text x="{gx:.1f}" y="{H-PAD+16}" text-anchor="middle" fill="#555">{wv:.0f}</text>')
        out.append(f'<text x="{PAD-8}" y="{gy+4:.1f}" text-anchor="end" fill="#555">{hv:.0f}</text>')
    for r in rows:
        cx = PAD + (r["w"] - w0) / (w1 - w0) * pw
        cy = PAD + (1 - (r["h"] - h0) / (h1 - h0)) * ph
        c = col.get(r["t"], "#000")
        out.append(
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="3.4" fill="{c}" fill-opacity="0.62" '
            f'stroke="{c}" stroke-opacity="0.9" stroke-width="0.6">'
            f'{r["t"]} line {r["n"]}: h={r["h"]:.2f} w={r["w"]:.2f}</circle>'
        )
    out.append(f'<text x="{PAD+pw/2:.0f}" y="{H-12}" text-anchor="middle" font-size="14" fill="#222">Leaf width</text>')
    out.append(f'<text x="16" y="{PAD+ph/2:.0f}" text-anchor="middle" font-size="14" fill="#222" transform="rotate(-90 16 {PAD+ph/2:.0f})">Leaf height</text>')
    lx = PAD + 8
    for t in sorted(by_type):
        out.append(f'<circle cx="{lx}" cy="{PAD-22}" r="4.5" fill="{col.get(t,"#000")}"/>')
        out.append(f'<text x="{lx+9}" y="{PAD-18}" fill="#222">{t} (n={by_type[t]})</text>')
        lx += 118
    out.append("</svg>")
    with open("leaves_scatter.svg", "w") as fh:
        fh.write("\n".join(out))
    print("\nwrote leaves_scatter.svg")


if __name__ == "__main__":
    main()
