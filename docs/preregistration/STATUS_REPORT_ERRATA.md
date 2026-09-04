# Errata — D0PA1_Build_Status_Report.docx

`D0PA1_Build_Status_Report.docx` (committed unmodified alongside this file) describes
the repository **as of 2026-08-26**. It is not edited — per §18 change control, a
committed document is corrected by a dated erratum, never by a silent rewrite. This
file lists, item by item, every claim in that report's §6 ("What is NOT built") table
that is now superseded, with the module and commit that superseded it.

Two items in that same table remain accurate and are **not** listed as errata below
(they are still true): **Attention/ROI features** and **Prediction target and model**
are still not built, both still blocked on the client's controlled task environment
(D2). **Audio module** and **Second-camera capture** are also still not built, both
still pending the decisions the original report already named.

## Superseded items

| Item, as stated in §6 of the report | Original status | Now | Module(s) | Commit |
|---|---|---|---|---|
| Experiment ID, config hash, pinned config | "Not built" | Built | `simulation/provenance.py`, `simulation/config.py` | `6b774b1` |
| Data manifest | "Not built" | Built | `manifest/generate_data_manifest.py` → `manifest/data_manifest.csv` | `6b774b1` |
| Canonical log schema and validator | "Defined, not implemented" | Built | `schema/canonical_log_v1.json`, `schema/canonical_log_writer.py` | `a7521b8` |
| MAD-based robust baseline | "Not built. Calibration currently uses mean and standard deviation" | Built (alongside, not replacing, mean/std — see `docs/SIGNAL_COMPLETIONS.md` §C1) | `features/robust_baseline.py` | `c680951` |
| Missingness and confidence on every signal | "Partial across signals" | Built for the four core vectors (v_bf/v_es/v_jc/v_pd); the attention-block pilot signals are explicitly not extended, stated as a residual gap, not overstated as complete | `features/signal_quality.py` | `c680951` |
| Continuous FPS logging as a metric | "Measured, not logged as a time series" | Built — logged as a continuous time-series JSONL metric in every run, not opt-in soak mode only | `simulation/fps_logger.py` | `c680951` |
| Coverage metric | "Not built" | Built | `features/signal_quality.py:compute_coverage` | `c680951` |
| Null-input, negative controls | "Not built" | Built (code). **The null-input control's own live camera run has still never executed, even once** — its pure-computation pieces are unit-tested; this is not yet a fully superseded claim in practice, only in code existing. The negative control is fully exercised, automatically, inside every `compute_delta()` call. | `controls/null_input.py`, `controls/negative_control.py` | `c213867` |
| Leakage control harness | "Not built" | Built. Exercised on synthetic data only — real action data still does not exist (D2 blocked), stated in `docs/CONTROLS.md` §3, not overstated here | `controls/leakage.py` | `3fa3c5b` |
| Positive blink control | "Not built" | Built. Exercised against synthetic aperture streams through the real `BlinkDetector` only — **no real clip has been recorded**, stated in `docs/CONTROLS.md` §4, not overstated here | `controls/blink_positive.py` | `646f560` |
| Time-shuffle control | not listed in the report's own table (predates that finding — added later, "matrix row 18, missed when the other controls were built") | Built | `controls/time_shuffle.py` | `c5e881c` |
| Three baseline representations (D7) | "Not built" | Built. Exercised on synthetic data; real 3-session matched-unit data does not exist yet | `analysis/baselines.py` | `921c317` |
| Reliability measures (SEM / RC / Bland–Altman / CV) | "Not built. Design partly needs the episode structure" | Built, including `compute_icc()`'s guard against a single-unit design — directly answering the client's §4.1 repeated-unit question at the code level. Real reliability-session data does not exist yet | `analysis/reliability.py` | `67ec15e` |
| Precision simulation (D6) | "Not built — see the sequencing note" | Built: generator, models, precision pipeline, five sweep passes, a primary-metric comparison, and a pre-registered clip-epsilon parameter | `simulation/generator.py`, `simulation/models.py`, `simulation/precision.py` | `354704b` (first committed; extended across several later commits through the finalisation/metric-comparison work) |
| Synthetic latent recovery | "Not built. Shares the D6 generator" | Built and run on synthetic data with known ground truth | `simulation/latent_recovery.py` | `fb123c1` |
| Reproduction command from archived inputs | "Not built. Requires consolidating the three consumers first" | Built — **without** consolidating the three capture/UI consumers, which remain diverged as originally reported. `reproduce.py` sidesteps this by never importing any of the three; it regenerates the analysis machinery from self-contained synthetic/seeded inputs instead. Verified bit-identical across two runs on this machine. The client's own named-executor acceptance test (Gargi running it on a clean machine) has not happened, and the confirmatory scope (real archived recordings) does not exist yet | `reproduce.py`, `Makefile`, `reproduce.ps1`, `compare_results.py` | `bdd2ee4` |
| Privacy retention and deletion routine | "Not built. Storage location decision" | Built — a config-hashed retention/deletion mechanism with a dry-run default. **The storage location decision itself remains exactly as open as the original report stated** — the mechanism takes it as a parameter rather than resolving the decision | `privacy/retention.py` | this commit |

## What this table does not change

The report's own §2 (the 11 A-column capability items), §3 (provenance/version-control
account), §4 (D1 separation), and §5 (the four uncovered findings — three diverged
consumers, the 41-minute soak, the compatibility-layer risk, pitch unreliability) are
**not** addressed by this errata because nothing in this session's work changed any of
them. They stand as originally written.
