# Follow-up prompt for the Claude Code agent — Task 1c redo

> Paste everything below the line as a single message.

---

**Read `CLAUDE.md` in full before doing anything else.** You are in `C:\Dopaland-POC`, the
D0PA1 vendor project. Guardrails G1–G5 bind this task.

You previously reported that Task 1c could not be done — that the two target paragraphs in
`docs/preregistration/D0PA1_Section19_SignOff_Response.docx` §4.14 "do not exist anywhere in
this document." **That conclusion is incorrect, and the reason is worth knowing before you
retry.**

The paragraphs are present, verbatim, right now. They were located by parsing
`word/document.xml` directly:

> `Directed testing during the POC established that horizontal head orientation (yaw) is
> detected reliably, but that pitch — looking up or down — is structurally unreliable in this
> approach. On a maximal, sustained, verified chin-to-chest look-down, measured pitch stayed
> at approximately 0.1° and the oriented-rate stayed at 1.0, indistinguishable from looking
> directly at the screen.`
>
> `The root cause is not a bug. The rotation decomposition is provably exact on synthetic
> rotations; the face foreshortens when looking down, degrading the landmark data that pitch
> depends on. It is not fixable within a single webcam at this resolution.`

**Why you missed them:** they sit **inside a `w:tbl` element** — specifically inside the 10th
table in the document body. `python-docx`'s `Document.paragraphs` enumerates **body-level
paragraphs only and excludes every paragraph inside a table cell.** Your Task 2 edit
succeeded because that paragraph *is* body-level. Your verification that "all 168 table cells
are byte-identical" is consistent with this: you correctly left the tables alone, and the
target text was inside one.

This also means one of your flagged findings is wrong and must **not** be acted on:
`docs/MATRIX_ROW_MAP.md` row 14's citation of §4.14 for the pitch pre-declaration is
**correct**. Do not change it.

## What to do

**Retry Task 1c**, reaching table-cell paragraphs this time. Either walk
`doc.tables[*].rows[*].cells[*].paragraphs` in addition to `doc.paragraphs`, or — more robust
against nested tables — iterate the body XML with `lxml` and handle every `<w:p>` regardless of
its ancestors. Locate paragraphs by their **full concatenated run text**; a visible paragraph
may be split across several runs, so rewrite the paragraph's runs rather than assuming one run
per paragraph. Preserve the existing paragraph style and the cell structure.

Replace those **two** paragraphs with these **four**, in order:

```
Directed testing established that horizontal head orientation (yaw) is detected reliably. Vertical orientation (pitch) is not usable for ROI attribution — but I am correcting the reason I gave for that in an earlier draft, because the reason was wrong.
```
```
The earlier draft stated that on a maximal, sustained chin-to-chest look-down, measured pitch stayed at approximately 0.1°, and attributed this to a structural limit of single-camera landmark head-pose. That figure had no documented verification method anywhere in the repository, and a subsequent graded-intensity capture, judged independently in real time before any number was shown, contradicts it: maximal held look-down attempts registered pitch as large as −43.1°, with magnitude scaling roughly with commanded intensity. I am retracting the figure and the mechanism claim built on it.
```
```
The practical conclusion is unchanged, and the evidence for it is now better. What fails during look-down is not the pitch measurement but face detection itself: detection rate fell to between 0.08% and 27.5% across the graded attempts, including on attempts where pitch registered at large magnitude. Because most window-samples are missing rather than present, the oriented-rate still reads close to 1.0 — a missingness artefact, not a reading of orientation. Two facts remain unexplained and I am not smoothing them over: a sign inconsistency between the medium and maximal readings, and why detection collapses this severely. The mechanism question is reopened, not settled.
```
```
The consequence for this row is what it was: the most common disengagement cue is looking down, and this signal cannot see it reliably. Your §11 failure rule already provides for that outcome, which is why I am declaring the expectation now rather than presenting it afterwards. I would rather show you a retracted claim and the data that retracted it than carry a tidy sentence I cannot support.
```

## Then, a sweep — the same blind spot may have hidden other things

Using **raw-XML enumeration of every `<w:p>`, not `Document.paragraphs`**, extract the full
text of this document and of `docs/preregistration/D0PA1_Build_Status_Report.docx`, and search
both for any other surviving instance of the retracted claim: `0.1°`, `structurally
unreliable`, `not fixable within a single webcam`, `chin-to-chest`. **Report what you find.
Do not edit anything you find in this sweep** — new wording is the methodology owner's call,
not yours.

## Verification — must not share the blind spot that caused the original error

1. Re-open the file and extract text by **parsing `word/document.xml` directly**, not via
   `Document.paragraphs`. Confirm the four new paragraphs are present and that neither
   `stayed at approximately 0.1°` nor `not fixable within a single webcam` appears anywhere in
   the part.
2. Confirm the Task 2 edit from your previous run is still intact: the closing paragraph must
   still read `Six rows` and must not contain `the null-input control has no camera run`.
3. Confirm paragraph and table counts are unchanged except for the intended +2 paragraphs
   inside the one table cell you edited. Your previous "168 table cells byte-identical" check
   will now legitimately show one cell changed — that is the expected result, not a regression.
4. Re-run the full test suite and `tests/test_refactor_snapshot.py`. The golden snapshot must
   still be `f7fa0575fba2959b9c21e88314e2fef645e8aa66fe11443102288db9dc1792b8`; a `.docx` edit
   cannot change it, so any change means something else moved.

**Do not commit.** Leave the change in the working tree.

Report: the diff, your verification output, and — stated plainly — anything you could not do.
If the replacement fails again, say so and stop. Do not substitute an approach.
