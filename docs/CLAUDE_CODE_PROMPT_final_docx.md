# Final prompt for the Claude Code agent — two .docx fixes

> Paste everything below the line as a single message.

---

**Read `CLAUDE.md` in full before doing anything else.** You are in `C:\Dopaland-POC`,
the D0PA1 vendor project. Guardrails G1–G5 bind this task. Two fixes, both in
`docs/preregistration/`. Both target text **inside `w:tbl` elements**, so reach paragraphs
through table cells — `Document.paragraphs` will not see them.

Your previous report was correct on both points that prompted this task. The redundancy in
Fix 1 is a drafting error in the replacement text you were given, not an error you made; you
were right to leave the paragraph alone and flag it rather than guess. Your note about the
`"stayed at approximately 0.1"` verification check is also correct — that string necessarily
appears inside the retraction sentence that quotes it, and the check as written was
context-blind. No action needed on that.

---

## Fix 1 — delete one now-redundant paragraph in `D0PA1_Section19_SignOff_Response.docx`

In §4.14, the cell now contains two consecutive paragraphs making the same point. The first
is the new replacement text; the second is the original, which should have been replaced
rather than left standing:

- **Keep:** the paragraph beginning `The consequence for this row is what it was: the most
  common disengagement cue is looking down, and this signal cannot see it reliably.`
- **Delete entirely:** the paragraph immediately following it, beginning `The consequence
  matters: the most common disengagement cue is looking down, and this signal cannot see it.
  Your §11 failure rule already provides for this outcome…`

The kept paragraph says everything the deleted one says and adds the closing line. Remove the
deleted paragraph's `<w:p>` element completely — do not blank its runs and leave an empty
paragraph behind.

After this fix, the §4.14 pre-declaration should read, in order: the `A pre-declaration I am
making now rather than later` heading, `I expect an elevated risk…`, the four retraction
paragraphs, then `Dependency: the ROI structure this test requires…`.

---

## Fix 2 — `D0PA1_Build_Status_Report.docx` §5.4 carries the full unretracted claim

You found this in the sweep and correctly did not act on it. Act on it now. The replacement
text below is final.

**Replace the section heading:**

```
5.4  Attention pitch detection is structurally unreliable
```

with:

```
5.4  Attention pitch: a retracted claim, and what the evidence now says
```

**Replace the two paragraphs** beginning `Directed testing established that horizontal head
orientation (yaw) is detected reliably, but that pitch…` and `The cause is not a bug…` —
note this document says `not fixable with a single webcam`, not `within` — with these three:

```
Directed testing established that horizontal head orientation (yaw) is detected reliably. Vertical orientation (pitch) is not usable for ROI attribution. An earlier version of this section gave a figure and a mechanism for that, and both are retracted here.
```
```
The retracted claim was that on a maximal, sustained chin-to-chest look-down, measured pitch stayed at approximately 0.1°, and that the cause was a structural limit of single-camera landmark head-pose, not fixable at this resolution. That figure had no documented verification method anywhere in the repository, and a later graded-intensity capture — judged independently in real time, before any number was shown — contradicts it: maximal held look-down attempts registered pitch as large as −43.1°, with magnitude scaling roughly with commanded intensity (small ≈6°, medium ≈2–3°, maximal ≈15–32°). Data: logs/orientation_trials.jsonl.
```
```
What actually fails during look-down is face detection, not the pitch measurement. Detection rate fell to between 0.08% and 27.5% across the graded attempts, including on attempts where pitch registered at large magnitude. Because most window-samples are missing rather than present, the oriented-rate still reads close to 1.0 — a missingness artefact, not a reading of orientation. Two facts remain unexplained and are not smoothed over: a sign inconsistency between the medium and maximal readings, and why detection collapses this severely. The practical conclusion is unchanged — pitch-based ROI attribution is not viable today — but the mechanism is reopened, not settled.
```

Preserve the heading's own paragraph style; clone the existing body paragraph's `pPr`/`rPr`
for the three new paragraphs, as you did in the previous task.

---

## Verification

Parse `word/document.xml` directly for both files — not `Document.paragraphs`.

1. **Sign-off response:** the `The consequence matters:` paragraph is gone; the `The
   consequence for this row is what it was:` paragraph remains; no empty `<w:p>` was left in
   its place; table-cell paragraph count drops by exactly 1 (186 → 185).
2. **Build status report:** the old heading and both old paragraphs are absent; the new
   heading and three new paragraphs are present; `stayed at approximately 0.1°` now occurs
   **only** inside the sentence that explicitly retracts it, and `not fixable with a single
   webcam` does not occur at all.
3. **Sweep both documents again** by raw XML for `0.1°`, `structurally unreliable`,
   `chin-to-chest`, `not fixable`, `oriented-rate stayed at 1.0`. Every surviving hit must sit
   inside retraction language. Report any that does not — **do not edit it**.
4. Golden snapshot still `f7fa0575fba2959b9c21e88314e2fef645e8aa66fe11443102288db9dc1792b8`;
   full test suite passing. A `.docx` edit cannot move either, so any change means something
   else did.

**Do not commit.** Report the diff, the verification output, and anything you could not do —
plainly, without substituting an approach.
