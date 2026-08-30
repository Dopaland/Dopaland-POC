"""
D6 precision simulation (D0PA1 Batch — precision simulation & synthetic
latent recovery, CLAUDE.md "WHAT D0PA1 ADDS"). Standalone: does not import
from features/ and does not touch the validated pipeline (G5).

Everything in this package operates on SYNTHETIC data only. It computes and
stores numbers (CI widths on Δ); it never decides RETAIN/DROP/INCONCLUSIVE
or compares a result against any δ (G1) -- that comparison is left to a
human reading artefacts/precision_analysis_v1.md.

See docs/D6_SIMULATION.md for the full generative model and every assumption.
"""
