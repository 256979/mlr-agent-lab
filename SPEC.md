# SPEC.md — leaves.csv classification

Status: final draft after interview. All previously-OPEN decisions are
resolved; the resolution is stated inline.

# Goal

Given two numbers about a leaf — its height and its width — say which tree it
came from: maple, cherry or walnut. The result should answer, in numbers: how
well can this be predicted at all, which of the compared models does it best,
and is the best model actually better than a trivial baseline. Just as
important: whether the messiness of this particular file (three merged
sources, repeated rows, probably mislabelled rows) changes what "best" means.

# Context

`data/leaves.csv` — 518 rows, 3 columns: `Leaf height`, `Leaf width`
(centimetres; not stated in the file, but 2.5–29.7 matches real leaf sizes in
cm — the values would be insect-sized in mm), `Tree type` with exactly three
values: maple (216), cherry (173), walnut (129). No missing or non-numeric
values.

Provenance: provided with the lecture. No further source information is
known, which is why the file's internal structure has to speak for itself:

- **Three sources pasted together.** Decimal precision clusters by row range:
  lines 2–101 have 1–2 decimals, 102–303 have 3–6, 304–519 have 1.
- **Repeated leaves.** 20 groups of byte-identical rows (26 redundant rows,
  5.0% of the file), plus 10 groups where the same leaf appears once at full
  precision and once rounded (e.g. `8.99,4.96` vs `9.0,5.0`).
- **Suspect labels.** 11 rows have a width/height ratio typical of a
  different type; maple's median width (14.7) exceeds its median height
  (13.0), unlike the other types — possibly a swapped column in one source.
- **Pooling hurts.** Within-type correlation between height and width is
  r = 0.67–0.80, but r = 0.59 over all rows — the classes occupy different
  regions, so analyses are per-class or model the class explicitly.

Separable in 2-D but overlapping at the edges: walnut is tall and narrow,
cherry small and narrow, maple large and roughly square.

`data/leaves_train.csv` / `leaves_test.csv` are produced by
`split_leaves.py` (committed) and regenerate with one command.

# Constraints

- **Test set**: created by `split_leaves.py`, stratified 80/20, **split by
  duplicate group** so no leaf (exact or same-leaf-rounded) ever appears on
  both sides — a naive row split leaked in 200/200 tested seeds. Seed 0. The
  test set is opened exactly once per model, after all choices are frozen;
  every model choice happens on train with internal validation.
- **Duplicates**: the 26 redundant copies stay in train — the group-safe
  split means they cannot leak, and they carry class weight as given. The
  `--dedupe` variant (482 unique leaves) is reported as a robustness check on
  the ranking, not as the main result.
- **Suspect labels**: the 11 shape-mismatched rows stay in the main
  experiment; a robustness run excluding them quantifies what label noise
  costs. Nothing is silently deleted.
- **Models** (fixed ladder): majority baseline, multinomial logistic
  regression, k-nearest-neighbours, decision tree, random forest.
- **Environment**: scikit-learn via pip (this machine has none of
  pandas/numpy/sklearn yet). `requirements.txt` pins versions so a classmate
  rerun is comparable. Data is small (518×2), so runtime is never the
  bottleneck.
- **Hyperparameters**, tuned by **stratified 5-fold CV inside train only**:
  kNN k ∈ {1,3,5,7,9}; logistic C over a log grid (1e-3…1e3); tree
  max_depth ∈ {2,3,4,None}; forest n_estimators = 64 with max_features swept.
  Feature standardisation is folded into each CV pipeline (fit on train
  folds, applied to validation folds) so it cannot leak.
- **Budget**: deterministic (fixed seeds everywhere), full sweep + single
  test evaluation + figures + report regeneration in under ~10 minutes wall
  time on a laptop.
- **Metric that chooses the model**: **macro-F1** on CV (classes are
  42/33/25% and all three matter equally). Accuracy is reported alongside
  every number but never decides. Final test numbers: macro-F1, accuracy,
  per-class recall, and the confusion matrix for the chosen model.

# Done when

- `SPEC.md` — this file, final.
- `analyze_leaves.py`, `split_leaves.py` — committed, still run clean.
- `requirements.txt` — pinned scikit-learn (and numpy) versions.
- `train.py` — trains the ladder, CV-tunes on train, opens test once, writes:
  - `results/results.csv` — one row per (model, setting): CV macro-F1
    mean/std, CV accuracy;
  - `results/final.csv` — one row per model: chosen config, CV macro-F1, and
    the single test-set macro-F1 + accuracy + per-class recall;
  - `results/confusion_matrix.csv` — chosen model, test set;
  - `results/report.md` — 1–2 pages: which model won, margin over baseline,
    robustness runs (dedupe variant; suspect-labels-excluded variant),
    honest caveats (merged sources, unverified labels, unknown provenance).
  - `results/fig_scatter.svg` (already produced by analyze_leaves.py; copied
    or regenerated) and `results/fig_confusion.svg`.
- `slides.md` — ~6-slide markdown deck: question, data, method, results,
  robustness, caveats.
- A classmate reproduces everything with:
  `pip install -r requirements.txt && python split_leaves.py && python train.py`
  — fixed seeds, identical numbers, ~10 minutes start to finish.
- Sanity checks present in the report: baseline beats chance; the
  duplicate-free split check (printed by `split_leaves.py`) quoted; per-class
  recall for all three classes shown so no class is quietly sacrificed; the
  dedupe and suspect-label robustness runs included with their verdicts on
  whether the ranking changed.
