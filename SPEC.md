# SPEC.md — leaves.csv classification (first draft)

Status: draft, being refined through interview. Decisions marked OPEN below.

# Goal

Given two numbers about a leaf — its height and its width — say which tree it
came from: maple, cherry or walnut. The result should answer, in numbers: how
well can this be predicted at all, which model does it best, and is the best
model actually better than a trivial baseline. Just as important: whether the
messiness of this particular file (three merged sources, repeated rows,
probably mislabelled rows) changes what "best" means.

# Context

`data/leaves.csv` — 518 rows, 3 columns: `Leaf height`, `Leaf width`
(units unstated in the file; the 2.5–29.7 range reads as centimetres, OPEN),
`Tree type` with exactly three values: maple (216), cherry (173), walnut
(129). No missing or non-numeric values. Units do not affect any model here
(both columns share a scale and every model is scale-invariant after
standardising), but they belong in the report.

The file is not a single clean measurement set. Findings from the audit
(`analyze_leaves.py`, committed):

- **Three sources pasted together.** Decimal precision clusters by row range:
  lines 2–101 have 1–2 decimals, 102–303 have 3–6, 304–519 have 1.
- **Repeated leaves.** 20 groups of byte-identical rows (26 redundant rows,
  5.0% of the file), plus 10 groups where the same leaf appears once at full
  precision and once rounded (e.g. `8.99,4.96` vs `9.0,5.0`).
- **Suspect labels.** 11 rows have a width/height ratio typical of a
  different type; maple's median width (14.7) exceeds its median height
  (13.0), unlike the other types — possibly a swapped column in that source.
- **Pooling hurts.** Within-type correlation between height and width is
  r = 0.67–0.80, but r = 0.59 over all rows — the classes occupy different
  regions, so analyses must be per-class or model the class explicitly.

Separable in 2-D but overlapping at the edges: walnut is tall and narrow,
cherry small and narrow, maple large and roughly square.

`data/leaves_train.csv` / `leaves_test.csv` are produced by
`split_leaves.py` (committed) and regenerate with one command.

# Constraints

- **Test set**: created by `split_leaves.py`, stratified 80/20, **split by
  duplicate group** so no leaf (exact or same-leaf-rounded) ever appears on
  both sides — a naive row split leaked in 200/200 tested seeds. Seed 0
  unless a sweep needs others. The test set is opened only for the final
  number; all model choice happens on train (with internal validation).
- **Duplicates**: kept in train (they carry class weight honestly) — the
  `--dedupe` variant must be reported as a robustness check, not as the main
  result. OPEN: confirm this is the intended reading.
- **Models**: comparison of a small ladder — majority/nearest-basic baseline,
  logistic regression (multinomial), k-nearest-neighbours, a decision tree,
  and one ensemble (random forest). OPEN: confirm the ladder; a simple
  per-class Gaussian or LDA may replace logistic regression.
- **Environment**: plain Python on this machine, currently **no pandas,
  numpy, matplotlib or sklearn installed**. Either models are implemented in
  the stdlib or we `pip install` — that decision is open and shapes
  everything. The data itself is small enough that pure Python is feasible.
- **Hyperparameters**: k in {1,3,5,7,9} for kNN; tree max_depth {2,3,4,None};
  logistic C over a log grid if sklearn is used; forest n_estimators fixed
  small {64} with max_features swept. Tuning on **training data only**, via
  stratified 5-fold CV inside train. OPEN: confirm CV scheme.
- **Budget**: everything runs in seconds to a couple of minutes on a laptop;
  full sweep + final evaluation in under ~10 minutes wall time, fixed seeds,
  fully deterministic.
- **Metric for choosing the model**: OPEN — macro-F1 proposed (classes are
  imbalanced 42/33/25% and all three classes matter equally), accuracy as
  reporting companion. Final numbers reported on test exactly once per model.

# Done when

- `SPEC.md` — this file, no OPEN markers left.
- `split_leaves.py`, `analyze_leaves.py` — already committed; still run clean.
- `train.py` (or notebook) — trains the model ladder, does CV tuning on train,
  writes:
  - `results/results.csv` — one row per (model, hyperparameter setting): CV
    mean/std of the chosen metric;
  - `results/final.csv` — one row per model: chosen config, CV metric, and the
    single test-set metric (chosen metric + accuracy + full confusion matrix);
  - `results/report.md` — 1–2 pages: which model won, by how much over the
    baseline, whether duplicates or suspect labels changed the ranking
    (robustness runs), and the honest caveats.
- A classmate can reproduce everything with:
  `python split_leaves.py && python train.py` — fixed seeds, same numbers,
  start to finish in ~10 minutes.
- Sanity checks present in the report: baseline beats chance, test set
  verified duplicate-free against train (the check `split_leaves.py` already
  prints), and per-class recall for all three classes shown so no class is
  being quietly sacrificed.
