# Table: Incremental (Added) Value Beyond a Baseline Model

The table standard for any "the new marker/model adds value **beyond** an established baseline"
claim — a new biomarker on top of a clinical score, an AI model on top of a radiologist or a
guideline nomogram. Discrimination alone (a higher AUROC) is not sufficient evidence of added
value; report the paired change in discrimination **with** a reclassification and a clinical-utility
metric, all on the **same patients** and the same held-out data.

## Reporting Guidelines
- **TRIPOD / TRIPOD+AI**: prediction-model development/validation, model comparison and performance
- **TRIPOD-LLM**: when the augmenting model is an LLM
- **CLAIM**: AI in medical imaging
- **STARD / STARD-AI**: when the added value is framed as diagnostic accuracy

## Standard Structure

```
Table 4. Incremental Value of [New Predictor/Model] Added to [Baseline] (external test set, n = ___, events = ___)

Model                         C-statistic (95% CI)   ΔC (95% CI)         P (ΔC)   Continuous NRI (95% CI)   IDI (95% CI)      ΔNet benefit @ threshold
Baseline ([predictors])       0.74 (0.70-0.78)       —  (reference)       —        —                          —                 — (reference)
Baseline + [new predictor]    0.81 (0.77-0.85)       0.07 (0.04-0.10)     <.001    0.38 (0.21-0.55)           0.045 (0.02-0.07) +0.021 @ 10%

ΔC by DeLong test on paired, same-patient predictions. NRI/IDI from the paired risk
estimates (event/non-event components reported separately in the footnote). Net benefit
from decision-curve analysis at the prespecified threshold; full curve in Figure X.
```

## Rules
- **Nested / same-patient comparison**: the augmented model must be the baseline **plus** the new
  term, evaluated on the **identical** held-out patients — not two models on different cohorts.
- **Baseline named and justified**: state exactly what the baseline contains (clinical score,
  guideline nomogram, prior model) and that it was applied as published / recalibrated / refit.
- **ΔAUC with a paired CI and test**: report ΔC-statistic with a 95% CI and the **DeLong** paired
  test, not two independent AUROCs eyeballed side by side. A tiny, non-significant ΔC with wide CI
  is not "added value."
- **Reclassification reported correctly**: prefer **continuous NRI** or category-free NRI; if a
  categorical NRI is used, prespecify and justify the risk categories (post-hoc categories inflate
  NRI). Always report **event** and **non-event** NRI components separately — a positive overall
  NRI driven only by the non-event component is weak. Report **IDI** alongside.
- **Clinical utility, not just statistics**: include **net benefit** (decision-curve analysis) at a
  prespecified, clinically justified threshold (and reference the full curve —
  `make-figures` `exemplar_plots/decision_curve.md`). Reclassification metrics without utility can
  mislead.
- **Calibration first**: NRI/IDI/net benefit all depend on predicted probabilities, so both models
  must be calibrated on the test data before these are computed (pair with the calibration plot).
- **One decimal discipline / CIs everywhere**: every estimate carries a 95% CI; bootstrap CIs state
  the number of replicates; the same bootstrap resamples are reused across paired metrics.

## Common pitfalls (flag in review)
- Reporting only ΔAUROC and calling it "added value" (no reclassification, no utility).
- NRI with post-hoc categories, or only the overall NRI without event/non-event split.
- New vs baseline AUROCs from different cohorts or different n (not a paired comparison).
- Net benefit asserted in prose with no decision curve and no stated threshold.

## Code (illustrative)

```r
# Paired ΔAUC with DeLong CI (pROC); NRI/IDI (Hmisc / nricens / PredictABEL-style).
library(pROC)
roc_base <- roc(y, p_baseline); roc_full <- roc(y, p_full)
roc.test(roc_base, roc_full, method = "delong", paired = TRUE)   # ΔC + p, paired
# NRI/IDI from paired risk vectors p_baseline, p_full (report event + non-event components);
# net benefit via the decision-curve template (analyze-stats references/templates/dca_plot.R).
```

```python
# Paired DeLong CI for ΔAUC (e.g., delong_roc_test); reclassification via statsmodels/lifelines-
# adjacent helpers. Compute NRI/IDI on the SAME held-out patients used for the AUCs; reuse one set
# of bootstrap resamples across ΔAUC, NRI, IDI, and net benefit so the CIs are mutually consistent.
```
