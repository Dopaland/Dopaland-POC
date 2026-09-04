# D0PA1 D4 -- reproduction command, Windows entry point.
#
# Identical behaviour to `make reproduce` -- both call the same
# reproduce.py, no separate logic lives here. See docs/D4_REPRODUCIBILITY.md
# for the full account: every seed, what is and is not covered, the
# actual measured byte-diff result of running this twice, and the
# recommended cross-machine comparison tolerance.
#
# Usage (from the repository root, in PowerShell):
#   .\reproduce.ps1

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

python reproduce.py
