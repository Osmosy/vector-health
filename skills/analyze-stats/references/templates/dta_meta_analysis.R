#!/usr/bin/env Rscript
# dta_meta_analysis.R — Diagnostic Test Accuracy Meta-Analysis
# ==============================================================
# Bivariate random-effects model (Reitsma) for DTA studies.
# Produces SROC curve, paired forest plots, pooled accuracy measures,
# Deeks' funnel plot, and threshold effect assessment.
#
# Requires: mada (>=0.5.11), meta (>=7.0-0), metafor (>=4.0-0)
# Install: install.packages(c("mada", "meta", "metafor"))
#
# Alternative: If mada is unavailable, bivariate model can be fitted
# with metafor::rma.mv() using a bivariate random-effects structure.
#
# Input CSV columns: study_label, TP, FP, FN, TN
#   Optional: subgroup, threshold
#
# Usage:
#   Rscript dta_meta_analysis.R --input dta_studies.csv --output dta_results
#   Or source() interactively -- edit CONFIG section below

set.seed(42)
suppressPackageStartupMessages({
  library(mada)
  library(meta)
  library(metafor)
})

cat(sprintf("dta_meta_analysis.R | Date: %s | R: %s\n",
            format(Sys.Date()), R.version$version.string))
cat(sprintf("mada: %s | meta: %s | metafor: %s\n\n",
            packageVersion("mada"), packageVersion("meta"), packageVersion("metafor")))

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

CONFIG <- list(
  input_file    = "dta_studies.csv",
  output_dir    = ".",
  output_prefix = "dta_meta",
  alpha         = 0.05,
  # Subgroup column name in CSV (NA to skip)
  subgroup_col  = NA
)

# ══════════════════════════════════════════════════════════════════════════════
# EXAMPLE DATA — Replace with real data or load from CSV
# ══════════════════════════════════════════════════════════════════════════════

example_data <- data.frame(
  study_label = c("Kim 2019", "Park 2020", "Lee 2021",
                  "Chen 2022", "Wang 2023", "Smith 2023",
                  "Jones 2024", "Zhang 2024"),
  TP = c(85, 120, 45, 95, 78, 60, 110, 55),
  FP = c(12, 18,  8, 15, 10,  9,  14,  7),
  FN = c( 5,  8,  3,  7,  4,  5,   6,  3),
  TN = c(98, 154, 44, 83, 108, 76, 170, 35),
  subgroup = c("A", "A", "A", "A", "B", "B", "B", "B")
)

# ══════════════════════════════════════════════════════════════════════════════
# LOAD DATA
# ══════════════════════════════════════════════════════════════════════════════

load_data <- function(config) {
  if (file.exists(config$input_file)) {
    df <- read.csv(config$input_file, stringsAsFactors = FALSE)
    cat(sprintf("Loaded: %s (%d studies)\n\n", config$input_file, nrow(df)))
    return(df)
  } else {
    cat("Input file not found. Using built-in example data.\n\n")
    return(example_data)
  }
}

df <- load_data(CONFIG)

# ══════════════════════════════════════════════════════════════════════════════
# BIVARIATE MODEL (Reitsma)
# ══════════════════════════════════════════════════════════════════════════════

cat("═══ BIVARIATE MODEL (Reitsma) ══════════════════════════════════════════\n")

# Prepare data for mada (requires TP, FP, FN, TN columns)
fit <- reitsma(df, formula = cbind(tsens, tfpr) ~ 1)
s <- summary(fit)
print(s)

# Extract pooled estimates
pooled_sens <- s$coefficients["tsens", "Estimate"]
pooled_fpr  <- s$coefficients["tfpr",  "Estimate"]
pooled_spec <- 1 - pooled_fpr

# Back-transform from logit
inv_logit <- function(x) exp(x) / (1 + exp(x))

sens_est  <- inv_logit(s$coefficients["tsens", "Estimate"])
sens_lo   <- inv_logit(s$coefficients["tsens", "Estimate"] - 1.96 * s$coefficients["tsens", "Std. Error"])
sens_hi   <- inv_logit(s$coefficients["tsens", "Estimate"] + 1.96 * s$coefficients["tsens", "Std. Error"])
spec_est  <- 1 - inv_logit(s$coefficients["tfpr", "Estimate"])
spec_lo   <- 1 - inv_logit(s$coefficients["tfpr", "Estimate"] + 1.96 * s$coefficients["tfpr", "Std. Error"])
spec_hi   <- 1 - inv_logit(s$coefficients["tfpr", "Estimate"] - 1.96 * s$coefficients["tfpr", "Std. Error"])

cat("\n─── Pooled Estimates ─────────────────────────────────────────────────\n")
cat(sprintf("  Pooled Sensitivity: %.3f (95%% CI: %.3f – %.3f)\n", sens_est, sens_lo, sens_hi))
cat(sprintf("  Pooled Specificity: %.3f (95%% CI: %.3f – %.3f)\n", spec_est, spec_lo, spec_hi))

# ── Pooled LR and DOR ────────────────────────────────────────────────────────

lr_pos <- sens_est / (1 - spec_est)
lr_neg <- (1 - sens_est) / spec_est
dor    <- lr_pos / lr_neg

cat(sprintf("  Positive LR: %.2f\n", lr_pos))
cat(sprintf("  Negative LR: %.2f\n", lr_neg))
cat(sprintf("  Diagnostic OR: %.2f\n", dor))

# ══════════════════════════════════════════════════════════════════════════════
# THRESHOLD EFFECT
# ══════════════════════════════════════════════════════════════════════════════

cat("\n═══ THRESHOLD EFFECT ════════════════════════════════════════════════════\n")

# Calculate per-study logit sensitivity and logit FPR
logit_sens <- log(df$TP / df$FN)
logit_fpr  <- log(df$FP / df$TN)

# Spearman correlation between logit(sensitivity) and logit(FPR)
sp_test <- cor.test(logit_sens, logit_fpr, method = "spearman")
cat(sprintf("  Spearman rho = %.3f, P = %.3f\n", sp_test$estimate, sp_test$p.value))
if (sp_test$p.value < 0.05) {
  cat("  → Significant threshold effect detected. Interpret pooled estimates with caution.\n")
  cat("  → Consider reporting SROC curve AUC rather than single pooled Se/Sp.\n")
} else {
  cat("  → No significant threshold effect.\n")
}

# ══════════════════════════════════════════════════════════════════════════════
# HETEROGENEITY
# ══════════════════════════════════════════════════════════════════════════════

cat("\n═══ HETEROGENEITY ══════════════════════════════════════════════════════\n")

# I-squared for sensitivity and specificity separately
# Using univariate random-effects for each
rma_sens <- rma(measure = "PLO",
                xi = df$TP, ni = df$TP + df$FN,
                method = "DL")
rma_spec <- rma(measure = "PLO",
                xi = df$TN, ni = df$TN + df$FP,
                method = "DL")

cat(sprintf("  I² for Sensitivity: %.1f%%\n", rma_sens$I2))
cat(sprintf("  I² for Specificity: %.1f%%\n", rma_spec$I2))

# ══════════════════════════════════════════════════════════════════════════════
# SROC CURVE
# ══════════════════════════════════════════════════════════════════════════════

cat("\n═══ SROC CURVE ══════════════════════════════════════════════════════════\n")

sroc_file <- file.path(CONFIG$output_dir,
                        paste0(CONFIG$output_prefix, "_sroc.pdf"))
pdf(sroc_file, width = 7, height = 7)
plot(fit, sroclwd = 2,
     main = "SROC Curve (Bivariate Model)",
     predict = TRUE,   # prediction region
     conf = TRUE)      # confidence region
legend("bottomleft",
       c("Summary point", "95% Confidence region", "95% Prediction region"),
       lty = c(NA, 1, 2), pch = c(1, NA, NA),
       col = c("black", "grey", "grey"), bty = "n")
dev.off()
cat(sprintf("Saved: %s\n", sroc_file))

# PNG version
sroc_png <- file.path(CONFIG$output_dir,
                       paste0(CONFIG$output_prefix, "_sroc.png"))
png(sroc_png, width = 7, height = 7, units = "in", res = 300)
plot(fit, sroclwd = 2,
     main = "SROC Curve (Bivariate Model)",
     predict = TRUE, conf = TRUE)
legend("bottomleft",
       c("Summary point", "95% Confidence region", "95% Prediction region"),
       lty = c(NA, 1, 2), pch = c(1, NA, NA),
       col = c("black", "grey", "grey"), bty = "n")
dev.off()
cat(sprintf("Saved: %s\n", sroc_png))

# ══════════════════════════════════════════════════════════════════════════════
# PAIRED FOREST PLOTS
# ══════════════════════════════════════════════════════════════════════════════

cat("\n═══ FOREST PLOTS ═══════════════════════════════════════════════════════\n")

# Sensitivity forest plot
forest_sens_file <- file.path(CONFIG$output_dir,
                               paste0(CONFIG$output_prefix, "_forest_sens.pdf"))
pdf(forest_sens_file, width = 10, height = max(5, nrow(df) * 0.4 + 2))
forest(fit, type = "sens", main = "Forest Plot: Sensitivity")
dev.off()
cat(sprintf("Saved: %s\n", forest_sens_file))

# Specificity forest plot
forest_spec_file <- file.path(CONFIG$output_dir,
                               paste0(CONFIG$output_prefix, "_forest_spec.pdf"))
pdf(forest_spec_file, width = 10, height = max(5, nrow(df) * 0.4 + 2))
forest(fit, type = "spec", main = "Forest Plot: Specificity")
dev.off()
cat(sprintf("Saved: %s\n", forest_spec_file))

# ══════════════════════════════════════════════════════════════════════════════
# PUBLICATION BIAS — Deeks' Funnel Plot Asymmetry Test
# ══════════════════════════════════════════════════════════════════════════════

cat("\n═══ PUBLICATION BIAS (Deeks' Funnel Plot) ═════════════════════════════\n")

if (nrow(df) >= 10) {
  # Deeks' funnel plot (appropriate for DTA, NOT standard funnel plot)
  deeks_file <- file.path(CONFIG$output_dir,
                           paste0(CONFIG$output_prefix, "_deeks_funnel.pdf"))
  pdf(deeks_file, width = 6, height = 6)

  # Calculate log DOR and effective sample size for Deeks' test
  log_dor <- log((df$TP * df$TN) / (df$FP * df$FN + 0.5))  # +0.5 for zero cells
  ess     <- 4 * (df$TP + df$FP) * (df$FN + df$TN) /
             (df$TP + df$FP + df$FN + df$TN)

  plot(1 / sqrt(ess), log_dor,
       xlab = "1 / sqrt(Effective Sample Size)",
       ylab = "log Diagnostic Odds Ratio",
       main = "Deeks' Funnel Plot Asymmetry Test",
       pch = 19)
  abline(lm(log_dor ~ I(1 / sqrt(ess))), lty = 2, col = "grey50")

  # Deeks' regression test
  deeks_lm <- lm(log_dor ~ I(1 / sqrt(ess)))
  deeks_p  <- summary(deeks_lm)$coefficients[2, 4]
  mtext(sprintf("Deeks' test P = %.3f", deeks_p),
        side = 3, line = 0.3, cex = 0.9)
  dev.off()
  cat(sprintf("Saved: %s\n", deeks_file))

  cat(sprintf("  Deeks' test: slope P = %.3f\n", deeks_p))
  if (deeks_p < 0.05) {
    cat("  → Significant asymmetry detected (possible publication bias)\n")
  } else {
    cat("  → No significant asymmetry\n")
  }
} else {
  cat("  Skipped: < 10 studies (Deeks' test underpowered)\n")
}

# ══════════════════════════════════════════════════════════════════════════════
# SENSITIVITY ANALYSIS — Leave-one-out
# ══════════════════════════════════════════════════════════════════════════════

cat("\n═══ SENSITIVITY ANALYSIS: Leave-one-out ══════════════════════════════\n")

loo_results <- data.frame(
  Study_removed    = character(),
  Pooled_Sens      = numeric(),
  Pooled_Spec      = numeric(),
  stringsAsFactors = FALSE
)

for (i in 1:nrow(df)) {
  df_loo <- df[-i, ]
  fit_loo <- tryCatch(
    reitsma(df_loo, formula = cbind(tsens, tfpr) ~ 1),
    error = function(e) NULL
  )
  if (!is.null(fit_loo)) {
    s_loo <- summary(fit_loo)
    se_loo <- inv_logit(s_loo$coefficients["tsens", "Estimate"])
    sp_loo <- 1 - inv_logit(s_loo$coefficients["tfpr", "Estimate"])
    loo_results <- rbind(loo_results, data.frame(
      Study_removed = df$study_label[i],
      Pooled_Sens   = round(se_loo, 3),
      Pooled_Spec   = round(sp_loo, 3)
    ))
  }
}

print(loo_results, row.names = FALSE)

loo_file <- file.path(CONFIG$output_dir,
                       paste0(CONFIG$output_prefix, "_leave_one_out.csv"))
write.csv(loo_results, loo_file, row.names = FALSE)
cat(sprintf("\nSaved: %s\n", loo_file))

# ══════════════════════════════════════════════════════════════════════════════
# DUAL APPROACH: Comparative + Single-Arm Pooled Proportion
# ══════════════════════════════════════════════════════════════════════════════
#
# When studies report both comparative (test A vs B) and single-arm data,
# use dual approach:
#   1. metabin() for comparative studies (OR/RR with Hartung-Knapp CI)
#   2. metaprop() for single-arm pooled proportion (logit transformation)
#
# Reference: Lin 2025 (PMID:41419890), Su 2026 (PMID:41653198)
#
# Uncomment and adapt the section below when you have comparative data:
#
# ── Comparative meta-analysis ──────────────────────────────────────────────
# m_comp <- metabin(
#   event.e = events_test, n.e = n_test,
#   event.c = events_ref,  n.c = n_ref,
#   studlab = study_label, data = df_comp,
#   sm = "OR",
#   method = "Inverse",      # NOT "MH" (avoids method.tau conflict)
#   method.tau = "DL",       # DL preferred for sparse data (REML may not converge)
#   method.random.ci = "HK", # Hartung-Knapp adjustment
#   common = FALSE,          # NOT fixed (deprecated)
#   random = TRUE,           # NOT comb.random (deprecated)
#   incr = 0.5               # continuity correction for zero cells
# )
#
# ── Single-arm pooled proportion ───────────────────────────────────────────
# m_prop <- metaprop(
#   event = events, n = total,
#   studlab = study_label, data = df_single,
#   sm = "PLOGIT",           # logit transformation
#   method.ci = "CP",        # Clopper-Pearson exact CI
#   method.tau = "DL",
#   method.random.ci = "HK",
#   common = FALSE,
#   random = TRUE
# )

# ══════════════════════════════════════════════════════════════════════════════
# RESULTS SUMMARY
# ══════════════════════════════════════════════════════════════════════════════

summary_df <- data.frame(
  Metric = c(
    "Pooled Sensitivity",
    "Sensitivity 95% CI lower",
    "Sensitivity 95% CI upper",
    "Pooled Specificity",
    "Specificity 95% CI lower",
    "Specificity 95% CI upper",
    "Positive LR",
    "Negative LR",
    "Diagnostic OR",
    "Threshold effect (Spearman rho)",
    "Threshold effect P-value",
    "I-squared Sensitivity (%)",
    "I-squared Specificity (%)",
    "N studies"
  ),
  Value = c(
    round(sens_est, 3),
    round(sens_lo, 3),
    round(sens_hi, 3),
    round(spec_est, 3),
    round(spec_lo, 3),
    round(spec_hi, 3),
    round(lr_pos, 2),
    round(lr_neg, 2),
    round(dor, 2),
    round(sp_test$estimate, 3),
    round(sp_test$p.value, 3),
    round(rma_sens$I2, 1),
    round(rma_spec$I2, 1),
    nrow(df)
  )
)

results_file <- file.path(CONFIG$output_dir,
                           paste0(CONFIG$output_prefix, "_summary.csv"))
write.csv(summary_df, results_file, row.names = FALSE)
cat(sprintf("\nSaved: %s\n", results_file))

# ── Session info ───────────────────────────────────────────────────────────────
cat("\n── Session Info ─────────────────────────────────────────────────────\n")
cat(sprintf("R: %s\n", R.version$version.string))
cat(sprintf("Date: %s\n", format(Sys.time())))
for (pkg in c("mada", "meta", "metafor")) {
  if (requireNamespace(pkg, quietly = TRUE)) {
    cat(sprintf("  %-12s %s\n", pkg, packageVersion(pkg)))
  }
}
cat("\nDTA meta-analysis complete.\n")
