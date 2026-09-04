# D0PA1 D4 -- reproduction command.
#
# THE ACCEPTANCE TEST: run ONE documented command on a clean machine and
# the reported results tables regenerate. `make reproduce` -- or, on
# Windows without make, `.\reproduce.ps1` (identical behaviour, calls the
# same reproduce.py) -- is that command. See docs/D4_REPRODUCIBILITY.md
# for the full account: every seed, what is and is not covered, the
# actual measured byte-diff result of running this twice, and the
# recommended cross-machine comparison tolerance.
#
# Never touches a live camera (2.1) -- reproduce.py imports only
# features/, analysis/, simulation/, controls/, schema/, never the three
# capture/UI consumers (2.2).

.PHONY: reproduce

reproduce:
	python reproduce.py
