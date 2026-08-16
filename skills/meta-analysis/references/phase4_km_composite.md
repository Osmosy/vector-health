# Phase 4 Reference — KM Reconstruction & Composite Exposure Disaggregation

Load this reference when `/meta-analysis` Phase 4 data extraction encounters either
of two special cases: (a) studies that report outcomes only as Kaplan-Meier curves
without raw event counts, or (b) studies whose intervention is a composite of
multiple techniques. The main Phase 4 body of SKILL.md lists the standard
extraction-form fields and the cross-verification checklist; this reference holds
the procedural detail for these two scenarios.

---

## 4b. KM Curve Reconstruction (when raw events not reported)

When studies report outcomes only as Kaplan-Meier curves without raw event counts:

1. **Digitise the KM curve**: Use WebPlotDigitizer
   (https://automeris.io/WebPlotDigitizer/)
   - Calibrate X/Y axes carefully — verify output range matches the original axis labels.
   - If coordinates come out in 0–1 range, multiply X by the actual time range
     (e.g., ×30 for months).
   - Clip negative Y values to 0 (digitisation artifact).
   - Export as CSV: `time, cumulative_event_rate` (or survival).

2. **Extract number-at-risk**: Record from the table below the KM plot at each time point.

3. **Reconstruct IPD**: Use the R `IPDfromKM` package (Guyot et al. 2012 method):
   ```r
   library(IPDfromKM)
   dat <- read.csv("digitised_curve.csv")
   preproc <- preprocess(dat, trisk, nrisk, totalpts, maxy = 1)
   ipd <- getIPD(preproc, armID = 1)  # armID starts at 1, NOT 0
   ```
   - ⚠️ `preprocess()` does NOT accept a `mateflag` parameter (common error).
   - ⚠️ `armID` starts at 1 (not 0).

4. **Verify**: Generate a reconstructed KM plot and visually compare to the
   original figure.

5. **Report in Methods**: Cite Guyot et al. 2012 (doi:10.1186/1471-2288-12-9) and
   state which studies required reconstruction.

**Alternative — Text-based extraction**: When no subgroup-specific KM curve exists
but the text reports "0% LTP at 12 months" or similar, extract directly from text.
Document the page number and exact quote.

---

## Composite Exposure Disaggregation

When a study's intervention is a composite of multiple techniques:

1. **Subgroup-specific KM curve** → use KM reconstruction (section 4b above).
2. **Component-specific Table/multivariate** → extract per-component data from Tables.
3. **Text-based subgroup report** → extract from narrative (e.g., "APE arm: 0% LTP").
4. **None available** → include as composite; flag in sensitivity analysis for exclusion.

Always pre-specify a sensitivity analysis excluding composite-exposure studies.
Document the extraction strategy in the data extraction form Notes column.
