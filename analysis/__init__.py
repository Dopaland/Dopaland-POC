"""
D0PA1 D7/D3 analysis package -- baseline representations (analysis/baselines.py)
and absolute reliability measures (analysis/reliability.py).

Standalone: does not import from features/x_core.py, features/episodes.py,
or stage1_step4_vectors.py, and never touches the validated pipeline (G5).
Everything here is additive, operating on already-computed signal values
supplied by a caller -- it computes and stores numbers (G1); it never
decides pass/fail, never labels a signal reliable/unreliable, and never
compares a result against a threshold.
"""
