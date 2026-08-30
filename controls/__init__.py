"""
D0PA1 controls (CLAUDE.md "WHAT D0PA1 ADDS" -- Controls: null-input,
negative control, time-shuffle, leakage harness, positive blink control).

Every control in this package COMPUTES AND STORES NUMBERS. None of them
decide anything (G1): no pass/fail, no threshold, no verdict. A control
that "fails" (a negative control that shows spurious contribution, a
null-input run with a high false-event rate) is REPORTED for a human to
read and investigate -- never auto-flagged as a kill condition, and never
silently absorbed either.

Controls in this package reuse the validated pipeline (features/geometry.py,
features/x_core.py) UNMODIFIED (G5) -- they exercise it, they do not alter
it.
"""
