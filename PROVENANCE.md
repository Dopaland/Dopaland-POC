# Provenance

Version control was established on this repository on **2026-08-24**.

All work in this repository prior to that date was performed without version
control. Commit timestamps in this repository's history therefore record when
the repository was created and when each commit was made from that point
forward — they do **not** record when the underlying work was originally
done. No commit in this history has been backdated. No prior history has been
reconstructed, synthesised, or staged to appear as though it existed before
this date.

A hardened `.gitignore` and a media-blocking, secret-blocking pre-commit hook
(`.githooks/pre-commit`, `core.hooksPath=.githooks`) were both in place and
verified to actually fire before the first file was ever staged. No face,
audio, or other raw participant media has entered this repository's history
at any point — verified directly (see `docs/PRIVACY_EVIDENCE.md`), not merely
assumed from the `.gitignore` rules.

From this commit onward, every material change to this repository is a dated
commit.

## Open item: raw data location

`logs/` is excluded from version control (`.gitignore`) and will never be
committed. That satisfies "raw data is not in git history." It does **not**
by itself satisfy the separate requirement that raw data live **outside the
repository directory, in a controlled location** — as of this commit,
`logs/` physically resides inside this repository's working directory on
disk, untracked but present. Being gitignored and being physically elsewhere
are two different guarantees; only the first is currently true.

This repository contains no raw media of any kind — no video, no audio, no
images — verified by a magic-byte content scan across every file in the
working tree, independent of file extension (method and result recorded in
`docs/PRIVACY_EVIDENCE.md`). What `logs/` currently holds is derived numeric
features and anonymous participant codes, not raw capture output.

The physical relocation of `logs/` to a location outside this repository is
an open decision, not yet made. This file records the gap; it does not
resolve it.
