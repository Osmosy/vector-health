# Ссылки на файлы внутри навыков: инвентарь

Сгенерировано `scripts/broken_refs.py`. Ссылок на файлы в дереве: 3528; на месте: 3036; битых: 492.

Битые ссылки — унаследованное свойство апстримов: файла, который навык упоминает, нет ни в их HEAD, ни в истории — он либо не был закоммичен, либо лежал в служебном каталоге, убранном при сборке (`tests/`, `evals/`). Тестовые файлы, на которые навык ССЫЛАЕТСЯ, при этом сохранены — см. `scripts/service_artifacts.py`. Правится не ссылка в чужом тексте, а знание о том, где файл есть.

| Категория | Сколько | Что значит |
|---|---|---|
| Пример пути в коде | 14 | форма пути (`YYYY`, `xxx`, `<file>`), а не файл — требовать его нельзя |
| Восстановимо | 0 | файл есть у источника — закрывается `scripts/sync_upstreams.py` |
| Внешний ресурс | 81 | путь ведёт в сторонний проект (git-подмодуль) или в каталог, создаваемый при работе (`src/`, `output_dir/`, `/opt`) — в репозитории такого файла быть не может |
| В корне источника | 9 | файл ЕСТЬ в репозитории-источнике, но вне каталога навыка (`scripts/`, `examples/`, `docs/`) — ссылка писалась под их раскладку, где навыки лежат глубже |
| Путь разошёлся | 11 | файл с таким именем есть в самом навыке, но по другому пути — ссылка не сработает, однако файл у читателя перед глазами (типично: данные лежат в `tests/expected_output/`) |
| Своя версия в апстриме | 0 | у навыка в апстриме ЕСТЬ файл по этому пути, но он не попал в сборку — свой контент навыка, копия из соседа подошла бы неверно |
| Общий файл апстрима | 0 | ссылку можно закрыть копией: файл размножен по навыкам апстрима и одинаков у них, `scripts/plant_sibling_files.py` кладёт копию рядом |
| Файл чужого навыка | 75 | у навыка в апстриме своего файла нет, а найденный — уникальный контент чужого навыка (у `guide.md` — 17 копий и 17 разных версий); копировать его нельзя, текст ссылается на файл соседа |
| Апстрим не публиковал | 73 | каталог навыка в источнике есть, но подкаталогов в нём нет: `references/`, `scripts/`, `data/` апстрим не выкладывал — файла не было и в момент сборки |
| Тяжёлые данные | 2 | файл есть, но это демо-датасет на мегабайты — сознательно не тянем |
| Унаследованное | 227 | файла нет ни в источнике, ни у соседнего навыка: апстрим его не выложил. Часть таких ссылок описывает РЕЗУЛЬТАТ работы навыка (выходные файлы `data/*.vcf.gz`), и требовать их не нужно — но отличить это автоматически нельзя: признак только в тексте, поэтому файлы остаются здесь, а не выдаются за «создаётся при работе» |

## Пример пути в коде (не ссылка)

| Навык | Файл | Источник |
|---|---|---|
| `bio-atac-seq-footprinting` | `jaspar.genereg.net/download/data/2022/CORE/JASPAR2022_CORE_vertebrates_non-redundant_pfms_jaspar.txt` | пример пути |
| `bio-chipseq-motif-analysis` | `jaspar.genereg.net/download/data/2024/CORE/JASPAR2024_CORE_vertebrates_non-redundant_pfms_meme.txt` | пример пути |
| `bio-variant-calling-deepvariant` | `data/output.g.vcf.gz` | пример пути |
| `bio-variant-calling-deepvariant` | `data/output.vcf.gz` | пример пути |
| `data-viz-plots` | `seaborn.pydata.org/examples/index.html` | пример пути |
| `fitness-analyzer` | `data/fitness-logs/YYYY-MM/YYYY-MM-DD.json` | пример пути |
| `rehabilitation-analyzer` | `data/rehabilitation-logs/YYYY-MM/YYYY-MM-DD.json` | пример пути |
| `skill-auditor` | `scripts/xxx.py` | пример пути |
| `statsmodels` | `www.statsmodels.org/stable/examples/index.html` | пример пути |
| `travel-health-analyzer` | `data/travel-health-logs/pre-trip-assessment-YYYY-MM-DD.json` | пример пути |
| `variant-interpretation-acmg/bioSkills/deepvariant` | `data/output.g.vcf.gz` | пример пути |
| `variant-interpretation-acmg/bioSkills/deepvariant` | `data/output.vcf.gz` | пример пути |
| `weightloss-analyzer` | `data/health-logs/YYYY-MM/YYYY-MM-DD.json` | пример пути |
| `writing-plans` | `src/path/file.py` | пример пути |

## Внешний ресурс (не файл этого репозитория)

Путь ведёт **не** в репозиторий навыка: в сторонний проект или в каталог, который создаётся при работе. Файла здесь быть не может — ссылка описывает, где ресурс лежит или появится.

| Навык | Ссылка в тексте | Что это | Где взять | Состояние |
|---|---|---|---|---|
| `scientific-visualization` | `scientific-packages/seaborn/references/examples.md` | внешний пакет | — | — |
| `scientific-visualization` | `scientific-packages/seaborn/references/function_reference.md` | внешний пакет | — | — |
| `scientific-visualization` | `scientific-packages/seaborn/references/objects_interface.md` | внешний пакет | — | — |
| `bulk-combat-correction` | `../../omicverse_guide/docs/Tutorials-bulk/t_bulk_combat.ipynb` | внешний проект | https://github.com/omicverse/omicverse-tutorials | путь совпадает |
| `bulk-deg-analysis` | `../../omicverse_guide/docs/Tutorials-bulk/t_deg.ipynb` | внешний проект | https://github.com/omicverse/omicverse-tutorials | путь совпадает |
| `bulk-deseq2-analysis` | `../../omicverse_guide/docs/Tutorials-bulk/t_deseq2.ipynb` | внешний проект | https://github.com/omicverse/omicverse-tutorials | путь совпадает |
| `bulk-stringdb-ppi` | `../../omicverse_guide/docs/Tutorials-bulk/t_network.ipynb` | внешний проект | https://github.com/omicverse/omicverse-tutorials | путь совпадает |
| `bulk-to-single-deconvolution` | `../../omicverse_guide/docs/Tutorials-bulk2single/t_bulk2single.ipynb` | внешний проект | https://github.com/omicverse/omicverse-tutorials | переехал → `docs/Tutorials-Multi-Omics/bulk-single/t_bulk2single.ipynb` |
| `bulk-trajblend-interpolation` | `../../omicverse_guide/docs/Tutorials-bulk2single/t_bulktrajblend.ipynb` | внешний проект | https://github.com/omicverse/omicverse-tutorials | переехал → `docs/Tutorials-Multi-Omics/bulk-single/t_bulktrajblend.ipynb` |
| `bulk-wgcna-analysis` | `../../omicverse_guide/docs/Tutorials-bulk/t_wgcna.ipynb` | внешний проект | https://github.com/omicverse/omicverse-tutorials | путь совпадает |
| `gsea-enrichment` | `../../omicverse_guide/docs/Tutorials-bulk/t_deg.ipynb` | внешний проект | https://github.com/omicverse/omicverse-tutorials | путь совпадает |
| `single-annotation` | `../../../omicverse_guide/docs/Tutorials-single/t_anno_trans.ipynb` | внешний проект | https://github.com/omicverse/omicverse-tutorials | путь совпадает |
| `single-annotation` | `../../../omicverse_guide/docs/Tutorials-single/t_cellanno.ipynb` | внешний проект | https://github.com/omicverse/omicverse-tutorials | переехал → `docs/Tutorials-single/anno-zoo/t_cellanno.ipynb` |
| `single-annotation` | `../../../omicverse_guide/docs/Tutorials-single/t_cellmatch.ipynb` | внешний проект | https://github.com/omicverse/omicverse-tutorials | путь совпадает |
| `single-annotation` | `../../../omicverse_guide/docs/Tutorials-single/t_cellvote.md` | внешний проект | https://github.com/omicverse/omicverse-tutorials | **в проекте нет** |
| `single-annotation` | `../../../omicverse_guide/docs/Tutorials-single/t_cellvote_pbmc3k.ipynb` | внешний проект | https://github.com/omicverse/omicverse-tutorials | переехал → `docs_zh/Tutorials-single/t_cellvote_pbmc3k.ipynb` |
| `single-annotation` | `../../../omicverse_guide/docs/Tutorials-single/t_gptanno.ipynb` | внешний проект | https://github.com/omicverse/omicverse-tutorials | переехал → `docs/Tutorials-single/anno-zoo/t_gptanno.ipynb` |
| `single-annotation` | `../../../omicverse_guide/docs/Tutorials-single/t_metatime.ipynb` | внешний проект | https://github.com/omicverse/omicverse-tutorials | переехал → `docs/Tutorials-single/anno-zoo/t_metatime.ipynb` |
| `single-cellphone-db` | `../../omicverse_guide/docs/Tutorials-single/t_cellphonedb.ipynb` | внешний проект | https://github.com/omicverse/omicverse-tutorials | **в проекте нет** |
| `single-clustering` | `../../omicverse_guide/docs/Tutorials-single/t_cluster.ipynb` | внешний проект | https://github.com/omicverse/omicverse-tutorials | путь совпадает |
| `single-clustering` | `../../omicverse_guide/docs/Tutorials-single/t_single_batch.ipynb` | внешний проект | https://github.com/omicverse/omicverse-tutorials | переехал → `docs/Tutorials-single/batch/t_single_batch.ipynb` |
| `single-preprocessing` | `../../omicverse_guide/docs/Tutorials-single/t_preprocess.ipynb` | внешний проект | https://github.com/omicverse/omicverse-tutorials | путь совпадает |
| `single-preprocessing` | `../../omicverse_guide/docs/Tutorials-single/t_preprocess_cpu.ipynb` | внешний проект | https://github.com/omicverse/omicverse-tutorials | путь совпадает |
| `single-preprocessing` | `../../omicverse_guide/docs/Tutorials-single/t_preprocess_gpu.ipynb` | внешний проект | https://github.com/omicverse/omicverse-tutorials | путь совпадает |
| `single-to-spatial-mapping` | `../../omicverse_guide/docs/Tutorials-bulk2single/t_single2spatial.ipynb` | внешний проект | https://github.com/omicverse/omicverse-tutorials | переехал → `docs/Tutorials-Multi-Omics/bulk-single/t_single2spatial.ipynb` |
| `spatial-tutorials` | `../../omicverse_guide/docs/Tutorials-space/t_cellpose.ipynb` | внешний проект | https://github.com/omicverse/omicverse-tutorials | путь совпадает |
| `spatial-tutorials` | `../../omicverse_guide/docs/Tutorials-space/t_cluster_space.ipynb` | внешний проект | https://github.com/omicverse/omicverse-tutorials | путь совпадает |
| `spatial-tutorials` | `../../omicverse_guide/docs/Tutorials-space/t_commot_flowsig.ipynb` | внешний проект | https://github.com/omicverse/omicverse-tutorials | путь совпадает |
| `spatial-tutorials` | `../../omicverse_guide/docs/Tutorials-space/t_crop_rotate.ipynb` | внешний проект | https://github.com/omicverse/omicverse-tutorials | путь совпадает |
| `spatial-tutorials` | `../../omicverse_guide/docs/Tutorials-space/t_decov.ipynb` | внешний проект | https://github.com/omicverse/omicverse-tutorials | путь совпадает |
| `spatial-tutorials` | `../../omicverse_guide/docs/Tutorials-space/t_gaston.ipynb` | внешний проект | https://github.com/omicverse/omicverse-tutorials | путь совпадает |
| `spatial-tutorials` | `../../omicverse_guide/docs/Tutorials-space/t_slat.ipynb` | внешний проект | https://github.com/omicverse/omicverse-tutorials | путь совпадает |
| `spatial-tutorials` | `../../omicverse_guide/docs/Tutorials-space/t_spaceflow.ipynb` | внешний проект | https://github.com/omicverse/omicverse-tutorials | путь совпадает |
| `spatial-tutorials` | `../../omicverse_guide/docs/Tutorials-space/t_staligner.ipynb` | внешний проект | https://github.com/omicverse/omicverse-tutorials | путь совпадает |
| `spatial-tutorials` | `../../omicverse_guide/docs/Tutorials-space/t_starfysh.ipynb` | внешний проект | https://github.com/omicverse/omicverse-tutorials | путь совпадает |
| `spatial-tutorials` | `../../omicverse_guide/docs/Tutorials-space/t_stt.ipynb` | внешний проект | https://github.com/omicverse/omicverse-tutorials | путь совпадает |
| `tcga-preprocessing` | `../../omicverse_guide/docs/Tutorials-bulk/t_tcga.ipynb` | внешний проект | https://github.com/omicverse/omicverse-tutorials | путь совпадает |
| `bulk-deg-analysis` | `../../sample/counts.txt` | данные примера | — | — |
| `bulk-deseq2-analysis` | `../../sample/counts.txt` | данные примера | — | — |
| `chemistry-agent` | `src/chemistry/main.py` | каталог запуска | — | — |
| `crisis-response-protocol` | `src/lib/ai/chat-handler.ts` | каталог запуска | — | — |
| `crisis-response-protocol` | `src/lib/ai/crisis-detection.ts` | каталог запуска | — | — |
| `crisis-response-protocol` | `src/lib/crisis/emergency-contacts.ts` | каталог запуска | — | — |
| `crisis-response-protocol` | `src/lib/crisis/resources.ts` | каталог запуска | — | — |
| `deep-research-swarm` | `src/research/agents/agent_coordinator.py` | каталог запуска | — | — |
| `differential-expression-analysis` | `tests/data/Combined_Datasets_Matrix_mus.csv` | каталог запуска | — | — |
| `dispatching-parallel-agents` | `src/agents/agent-tool-abort.test.ts` | каталог запуска | — | — |
| `dnanexus-integration` | `src/my-app.py` | каталог запуска | — | — |
| `estimate-immune-score-analysis` | `tests/output/data/estimate_input.gct` | каталог запуска | — | — |
| `estimate-immune-score-analysis` | `tests/output/data/estimate_score.gct` | каталог запуска | — | — |
| `estimate-immune-score-analysis` | `tests/output/data/expression_input.tsv` | каталог запуска | — | — |
| `gsea` | `test_output/data/GSEA_list.rda` | каталог запуска | — | — |
| `gsva-analysis-and-visualization` | `tests/data/expr_matrix.csv` | каталог запуска | — | — |
| `gsva-analysis-and-visualization` | `tests/output/data/GSVA_list.rda` | каталог запуска | — | — |
| `hipaa-compliance` | `src/lib/auth.ts` | каталог запуска | — | — |
| `hipaa-compliance` | `src/lib/hipaa/audit.ts` | каталог запуска | — | — |
| `knn-imputation` | `tests/data/sample_expression_matrix.csv` | каталог запуска | — | — |
| `lit-sync` | `src/refs.bib` | каталог запуска | — | — |
| `lncrna-regulatory-network-construction-analysis` | `output_dir/data/lncrna_network.rda` | каталог запуска | — | — |
| `lncrna-regulatory-network-construction-analysis` | `tests/output/data/lncrna_network.rda` | каталог запуска | — | — |
| `ma-scout` | `.claude/skills/search-lit/references/parse_pubmed.py` | каталог запуска | — | — |
| `ma-scout` | `.claude/skills/search-lit/references/pubmed_eutils.sh` | каталог запуска | — | — |
| `manage-refs` | `src/refs.bib` | каталог запуска | — | — |
| `nomogram-construction` | `output/data/Nomogram_list.qs` | каталог запуска | — | — |
| `obsidian-paper-vault` | `src/refs.bib` | каталог запуска | — | — |
| `orchestrate` | `src/refs.bib` | каталог запуска | — | — |
| `ppi-network-analysis` | `output_dir/data/ppi_result.rds` | каталог запуска | — | — |
| `ppi-network-analysis` | `tests/output/basic-run/data/ppi_result.rds` | каталог запуска | — | — |
| `review-paper` | `src/refs.bib` | каталог запуска | — | — |
| `rf-model-importance-analysis` | `output_dir/data/rf_result.rds` | каталог запуска | — | — |
| `sample-group-sankey-plot` | `tests/data/minimal_annotations.csv` | каталог запуска | — | — |
| `search-lit` | `src/refs.bib` | каталог запуска | — | — |
| `spatial-transcriptomics-agent` | `repo/src/main.py` | каталог запуска | — | — |
| `spatial-transcriptomics-analysis/STAgent` | `repo/src/main.py` | каталог запуска | — | — |
| `svm-model-importance-analysis` | `output_dir/data/svm_result.rds` | каталог запуска | — | — |
| `time-dependent-roc` | `tests/validation_output/data/time_roc_points.csv` | каталог запуска | — | — |
| `verify-refs` | `src/refs.bib` | каталог запуска | — | — |
| `write-paper` | `src/refs.bib` | каталог запуска | — | — |
| `bio-long-read-sequencing-clair3-variants` | `opt/bin/run_clair3.sh` | установленный инструмент | — | — |
| `bio-variant-calling-deepvariant` | `opt/hap.py/bin/hap.py` | установленный инструмент | — | — |
| `variant-interpretation-acmg/bioSkills/deepvariant` | `opt/hap.py/bin/hap.py` | установленный инструмент | — | — |

## Файл в корне репозитория-источника (вне каталога навыка)

Файл существует в репозитории-источнике, но **вне каталога навыка** — в его корне (`scripts/`, `examples/`, `docs/`). Навык писал ссылку под исходную раскладку, где каталоги навыков лежат глубже; мы складываем навыки плоско, поэтому та же ссылка (`../../`) выводит за пределы репозитория. Ссылка не станет рабочей от простой закачки файла в навык: путь в тексте останется прежним. Брать файл — по URL ниже, требовать его внутри репозитория нельзя.

| Навык | Ссылка в тексте | Файл в источнике | Взять |
|---|---|---|---|
| `benchmark-pii-recall` | `../../examples/v16_policy_audit_release_gates.py` | `examples/v16_policy_audit_release_gates.py` | https://github.com/maziyarpanahi/openmed/blob/HEAD/examples/v16_policy_audit_release_gates.py |
| `deidentify-a-dataset` | `../../examples/datasets_walkthrough.py` | `examples/datasets_walkthrough.py` | https://github.com/maziyarpanahi/openmed/blob/HEAD/examples/datasets_walkthrough.py |
| `extract-clinical-entities-to-fhir` | `../../examples/first_five_minutes_redact_extract_fhir.py` | `examples/first_five_minutes_redact_extract_fhir.py` | https://github.com/maziyarpanahi/openmed/blob/HEAD/examples/first_five_minutes_redact_extract_fhir.py |
| `meta-analysis` | `../../scripts/extraction_consensus_log_init.py` | `scripts/extraction_consensus_log_init.py` | https://github.com/Aperivue/medsci-skills/blob/HEAD/scripts/extraction_consensus_log_init.py |
| `meta-analysis` | `../../scripts/prisma_5way_consistency.py` | `scripts/prisma_5way_consistency.py` | https://github.com/Aperivue/medsci-skills/blob/HEAD/scripts/prisma_5way_consistency.py |
| `meta-analysis` | `../../scripts/tag_cleanup_gate.sh` | `scripts/tag_cleanup_gate.sh` | https://github.com/Aperivue/medsci-skills/blob/HEAD/scripts/tag_cleanup_gate.sh |
| `meta-analysis` | `../../scripts/verify_package_integrity.py` | `scripts/verify_package_integrity.py` | https://github.com/Aperivue/medsci-skills/blob/HEAD/scripts/verify_package_integrity.py |
| `pick-a-pii-model` | `../../examples/pii_model_comparison.py` | `examples/pii_model_comparison.py` | https://github.com/maziyarpanahi/openmed/blob/HEAD/examples/pii_model_comparison.py |
| `radiomics-ml` | `../../docs/method_coverage_map.md` | `docs/method_coverage_map.md` | https://github.com/Aperivue/medsci-skills/blob/HEAD/docs/method_coverage_map.md |

## Путь разошёлся (файл в навыке есть)

| Навык | Файл | Источник |
|---|---|---|
| `find-paper-references` | `SKILL_DIR/scripts/batch_search.py` | scripts/batch_search.py |
| `nomogram-construction` | `data/Nomogram_list.qs` | tests/expected_output/data/Nomogram_list.qs |
| `nomogram-construction` | `data/analysis_data.rds` | tests/expected_output/data/analysis_data.rds |
| `roc-diagnostic-performance` | `data/analysis_data.rds` | tests/expected_output/data/analysis_data.rds |
| `roc-diagnostic-performance` | `data/roc_model.rds` | tests/expected_output/data/roc_model.rds |
| `schedule-management` | `data/events.jsonl` | events.jsonl |
| `search-lit` | `references/library.bib` | references/snowball_challenge/fixture/library.bib |
| `tooluniverse-drug-repurposing` | `../chemical-compound-retrieval/SKILL.md` | SKILL.md |
| `tooluniverse-drug-repurposing` | `../disease-intelligence-gatherer/SKILL.md` | SKILL.md |
| `tooluniverse-drug-repurposing` | `../tooluniverse-sdk/SKILL.md` | SKILL.md |
| `univariate-multivariable-cox-regression` | `data/analysis_data.rds` | tests/expected_output/data/analysis_data.rds |

## Файл принадлежит другому навыку

| Навык | Файл | Источник |
|---|---|---|
| `academic-norm-review` | `references/guide.md` | meeting-assistant |
| `analyze-stats` | `references/exemplar_plots/decision_curve.md` | make-figures |
| `analyze-stats` | `references/exemplar_plots/mrmc_roc.md` | make-figures |
| `analyze-stats` | `scripts/check_reverse_coding.py` | clean-data |
| `analyze-stats` | `scripts/check_structural_zero.py` | clean-data |
| `authorship-credit-gen` | `references/guide.md` | meeting-assistant |
| `basic-research-design` | `references/prompt_templates.md` | prospero-registration-helper |
| `buffer-calculator` | `references/troubleshooting.md` | pca-dimensionality-reduction |
| `calc-sample-size` | `references/templates/sample_size.R` | analyze-stats |
| `check-reporting` | `references/analysis_guides/burden_decomposition_forecasting.md` | analyze-stats |
| `citation-chasing-mapping` | `references/audit-reference.md` | nih-biosketch-builder |
| `citation-chasing-mapping` | `references/guide.md` | meeting-assistant |
| `citation-chasing-mapping` | `scripts/main.py` | hipaa-compliance-auditor |
| `citation-formatter` | `references/guide.md` | meeting-assistant |
| `citation-formatter` | `scripts/main.py` | hipaa-compliance-auditor |
| `citation-network` | `references/README.md` | preprint-surveillance-finder |
| `clinic-research-design` | `scripts/main.py` | hipaa-compliance-auditor |
| `clinical-decision-support` | `scripts/generate_schematic.py` | scientific-schematics |
| `clinical-reports` | `scripts/generate_schematic.py` | scientific-schematics |
| `code-refactor-for-reproducibility` | `references/guide.md` | meeting-assistant |
| `cover-letter-generator` | `assets/cover_letter_template.md` | cover-letter-drafter |
| `cover-letter-generator` | `references/guide.md` | meeting-assistant |
| `cross-disciplinary-bridge-finder` | `references/guide.md` | meeting-assistant |
| `diffdock-molecular-docking` | `references/workflows_examples.md` | diffdock |
| `discussion-section-architect` | `references/guide.md` | meeting-assistant |
| `fastqc-report-interpreter` | `references/troubleshooting.md` | pca-dimensionality-reduction |
| `forest-plot-styler` | `scripts/main.py` | hipaa-compliance-auditor |
| `humanize` | `references/r2r_voice.md` | revise |
| `humanize` | `scripts/check_aphorism_density.py` | self-review |
| `humanize` | `scripts/check_emphasis_density.py` | self-review |
| `humanize` | `scripts/check_paren_spans.py` | self-review |
| `humanize` | `scripts/check_rhetorical_density.py` | self-review |
| `hypothesis-generation` | `scripts/generate_schematic.py` | scientific-schematics |
| `irb-application-assistant` | `references/audit-reference.md` | nih-biosketch-builder |
| `irb-application-assistant` | `references/guide.md` | meeting-assistant |
| `irb-application-assistant` | `scripts/main.py` | hipaa-compliance-auditor |
| `key-takeaways` | `references/guide.md` | meeting-assistant |
| `literature-management` | `references/examples.md` | open-notebook |
| `literature-management` | `scripts/requirements.txt` | preprint-surveillance-finder |
| `literature-review` | `scripts/generate_schematic.py` | scientific-schematics |
| `literature-statistics` | `scripts/process_references.py` | format-references-endnote |
| `meta-manuscript-generator` | `references/writing-guide.md` | nsfc-grant-writer |
| `model-calibration-curve` | `scripts/install_dependencies.R` | sample-group-sankey-plot |
| `nomogram-construction` | `scripts/install_dependencies.R` | sample-group-sankey-plot |
| `orchestrate` | `scripts/check_citation_keys.py` | manage-refs |
| `orchestrate` | `scripts/check_xref.py` | manage-refs |
| `orchestrate` | `scripts/render_pandoc.sh` | manage-refs |
| `paper-2-web` | `scripts/generate_schematic.py` | scientific-schematics |
| `pathology-roi-selector` | `scripts/main.py` | hipaa-compliance-auditor |
| `pdf-processing-pro` | `scripts/extract_text.py` | academic-highlight-generator |
| `pdf-processing-pro` | `scripts/fill_form.py` | fill-protocol |
| `pdf-processor` | `references/examples.md` | open-notebook |
| `pdf-processor` | `scripts/requirements.txt` | preprint-surveillance-finder |
| `render-pdf-doc` | `scripts/render_pandoc.sh` | manage-refs |
| `research-grants` | `scripts/compliance_checker.py` | clinical-reports |
| `research-grants` | `scripts/generate_schematic.py` | scientific-schematics |
| `research-lookup` | `scripts/generate_schematic.py` | scientific-schematics |
| `research-proposal-generator` | `references/prompts.md` | academic-highlight-generator |
| `revise` | `references/ai_patterns.md` | humanize |
| `revise` | `references/section_guides/step7_1_classical_qc.md` | write-paper |
| `revise` | `scripts/check_wordcount_cap.py` | sync-submission |
| `sample-size-power-calculator` | `references/audit-reference.md` | nih-biosketch-builder |
| `sample-size-power-calculator` | `scripts/main.py` | hipaa-compliance-auditor |
| `scientific-critical-thinking` | `scripts/generate_schematic.py` | scientific-schematics |
| `scientific-slides` | `scripts/generate_schematic.py` | scientific-schematics |
| `scientific-writing` | `scripts/generate_schematic.py` | scientific-schematics |
| `self-review` | `scripts/check_xref.py` | manage-refs |
| `survival-analysis-km` | `scripts/main.py` | hipaa-compliance-auditor |
| `text-format-organizer` | `scripts/init_run.py` | article-format-adjustment |
| `tooluniverse-gene-enrichment` | `references/common_patterns.md` | cellxgene-census |
| `tooluniverse-gene-enrichment` | `references/report_template.md` | arxiv-preflight |
| `treatment-plans` | `scripts/generate_schematic.py` | scientific-schematics |
| `write-paper` | `scripts/check_citation_keys.py` | manage-refs |
| `write-paper` | `scripts/check_xref.py` | manage-refs |
| `write-paper` | `scripts/render_pandoc.sh` | manage-refs |

## Апстрим не публиковал каталог

| Навык | Файл | Источник |
|---|---|---|
| `Case-control-study-quality-assessment-nos` | `references/nos_criteria_prompts.md` | aipoch |
| `Case-control-study-quality-assessment-nos` | `scripts/format_nos_table.py` | aipoch |
| `academic-norm-review` | `assets/academic_compliance_checklist.md` | aipoch |
| `ai-analyzer` | `data/ai-config.json` | OpenClaw |
| `ai-analyzer` | `data/ai-history.json` | OpenClaw |
| `ai-analyzer` | `data/allergies.json` | OpenClaw |
| `ai-analyzer` | `data/index.json` | OpenClaw |
| `ai-analyzer` | `data/medications.json` | OpenClaw |
| `ai-analyzer` | `data/profile.json` | OpenClaw |
| `ai-analyzer` | `scripts/generate_ai_report.py` | OpenClaw |
| `boltz` | `../../docs/installation.md` | OpenClaw |
| `bulk-to-single-deconvolution` | `../dg_vae.pth` | OpenClaw |
| `bulk-trajblend-interpolation` | `../dg_btb_vae.pth` | OpenClaw |
| `bulk-wgcna-analysis` | `../sampleInfo.csv` | OpenClaw |
| `clinic-research-design` | `scripts/calculators/sample_size.py` | aipoch |
| `cohort-study-quality-assessment-nos` | `references/nos_criteria.md` | aipoch |
| `cohort-study-quality-assessment-nos` | `scripts/calculate_nos_score.py` | aipoch |
| `computational-pathology-agent` | `data/biopsy_001.svs` | OpenClaw |
| `data-visualization-biomedical` | `references/color_guidelines.md` | OpenClaw |
| `data-visualization-biomedical` | `scripts/figure_templates.py` | OpenClaw |
| `emergency-card` | `data/allergies.json` | OpenClaw |
| `emergency-card` | `data/copd-tracker.json` | OpenClaw |
| `emergency-card` | `data/diabetes-tracker.json` | OpenClaw |
| `emergency-card` | `data/emergency-cards/emergency-card-2025-12-31.json` | OpenClaw |
| `emergency-card` | `data/emergency-example.json` | OpenClaw |
| `emergency-card` | `data/hypertension-tracker.json` | OpenClaw |
| `emergency-card` | `data/index.json` | OpenClaw |
| `emergency-card` | `data/medications/medications.json` | OpenClaw |
| `emergency-card` | `data/profile.json` | OpenClaw |
| `emergency-card` | `data/radiation-records.json` | OpenClaw |
| `emergency-card` | `scripts/generate_emergency_card.py` | OpenClaw |
| `exporting-bulk-fhir` | `data/export.html` | openmed |
| `family-health-analyzer` | `data/diabetes-tracker.json` | OpenClaw |
| `family-health-analyzer` | `data/family-health-tracker.json` | OpenClaw |
| `family-health-analyzer` | `data/hypertension-tracker.json` | OpenClaw |
| `family-health-analyzer` | `data/profile.json` | OpenClaw |
| `fitness-analyzer` | `data/diabetes-tracker.json` | OpenClaw |
| `fitness-analyzer` | `data/fitness-tracker.json` | OpenClaw |
| `fitness-analyzer` | `data/hypertension-tracker.json` | OpenClaw |
| `fitness-analyzer` | `data/profile.json` | OpenClaw |
| `journal-latest-issue` | `scripts/journal_digest.py` | aipoch |
| `ligandmpnn` | `../../docs/installation.md` | OpenClaw |
| `literature-management` | `scripts/import_library.py` | aipoch |
| `meta-abstract-screener` | `references/screening_prompts.md` | aipoch |
| `meta-abstract-screener` | `scripts/screen_paper.py` | aipoch |
| `meta-screening-fulltext` | `references/screening_prompts.md` | aipoch |
| `meta-screening-fulltext` | `scripts/query_pubmed.py` | aipoch |
| `molecular-review-workflow` | `scripts/pubmed_api.py` | aipoch |
| `mpn-research-assistant` | `references/mpn_clinical_trials.md` | OpenClaw |
| `mpn-research-assistant` | `references/mpn_mutations_database.md` | OpenClaw |
| `ngs-analysis` | `references/conda_envs.md` | OpenClaw |
| `ngs-analysis` | `scripts/batch_pipeline.py` | OpenClaw |
| `pdf-processor` | `scripts/pdf_tool.py` | aipoch |
| `pydicom` | `examples/index.html` | aipoch |
| `rehabilitation-analyzer` | `data/rehabilitation-tracker.json` | OpenClaw |
| `scientific-manuscript` | `references/journal_templates.md` | OpenClaw |
| `scientific-manuscript` | `references/statistical_tests.md` | OpenClaw |
| `search-strategy` | `../../CONNECTORS.md` | OpenClaw |
| `single-annotation` | `data/analysis_lymph/atac-emb.h5ad` | OpenClaw |
| `single-annotation` | `data/analysis_lymph/rna-emb.h5ad` | OpenClaw |
| `single-annotation` | `data/pbmc3k.h5ad` | OpenClaw |
| `single-cellphone-db` | `data/cpdb/normalised_log_counts.h5ad` | OpenClaw |
| `single-to-spatial-mapping` | `../pdac_df.pth` | OpenClaw |
| `solublempnn` | `../../docs/installation.md` | OpenClaw |
| `spatial-tutorials` | `data/cluster_svg.h5ad` | OpenClaw |
| `spatial-tutorials` | `data/sc.h5ad` | OpenClaw |
| `tcga-preprocessing` | `../ov_tcga_survial_all.h5ad` | OpenClaw |
| `tcga-preprocessing` | `data/TCGA_OV/ov_tcga_raw.h5ad` | OpenClaw |
| `tcm-constitution-analyzer` | `data/constitution-recommendations.json` | OpenClaw |
| `tcm-constitution-analyzer` | `data/constitutions.json` | OpenClaw |
| `travel-health-analyzer` | `data/travel-health-tracker.json` | OpenClaw |
| `weightloss-analyzer` | `data/fitness-tracker.json` | OpenClaw |
| `weightloss-analyzer` | `data/nutrition-tracker.json` | OpenClaw |

## Тяжёлые данные (не тянем)

| Навык | Файл | Источник |
|---|---|---|
| `genome-compare` | `data/george_church_23andme.txt.gz` | OpenClaw |
| `genome-compare` | `data/manuel_corpas_23andme.txt.gz` | OpenClaw |

## Унаследованное (файла нет в источнике)

| Навык | Файл | Источник |
|---|---|---|
| `LightGBM-analysis` | `data/lightgbm_categorical_levels.txt` | aipoch |
| `LightGBM-analysis` | `data/lightgbm_run_summary.txt` | aipoch |
| `alphafold` | `../../docs/installation.md` | OpenClaw |
| `article-format-adjustment` | `templates/science_format.json` | aipoch |
| `author-strategy` | `data/corpus_manifest.json` | Aperivue |
| `baseline-extraction-for-clinical-trials` | `scripts/baseline_extractor.py` | aipoch |
| `bindcraft` | `../../docs/installation.md` | OpenClaw |
| `bio-data-visualization-circos-plots` | `data/heatmap.txt` | OpenClaw |
| `bio-data-visualization-circos-plots` | `data/histogram.txt` | OpenClaw |
| `bio-data-visualization-circos-plots` | `data/karyotype.human.hg38.txt` | OpenClaw |
| `bio-data-visualization-circos-plots` | `data/links.txt` | OpenClaw |
| `bio-data-visualization-circos-plots` | `data/scatter.txt` | OpenClaw |
| `bio-epidemiological-genomics-amr-surveillance` | `data/genome.fasta` | OpenClaw |
| `bio-long-read-sequencing-clair3-variants` | `data/reference.fasta` | OpenClaw |
| `bio-long-read-sequencing-clair3-variants` | `data/sample.bam` | OpenClaw |
| `bio-long-read-sequencing-isoseq-analysis` | `data/clustered.bam` | OpenClaw |
| `bio-long-read-sequencing-isoseq-analysis` | `data/refined.bam` | OpenClaw |
| `bio-read-qc-quality-reports` | `data/multiqc_fastqc.txt` | OpenClaw |
| `bio-read-qc-quality-reports` | `data/multiqc_general_stats.txt` | OpenClaw |
| `bio-reporting-jupyter-reports` | `data/counts.csv` | OpenClaw |
| `bio-research-tools-biomarker-signature-studio` | `data/expression.csv` | OpenClaw |
| `bio-research-tools-biomarker-signature-studio` | `data/metadata.csv` | OpenClaw |
| `bio-single-cell-splicing` | `scripts/bam2junc.py` | OpenClaw |
| `bio-single-cell-splicing` | `scripts/leafcutter_ds.R` | OpenClaw |
| `bio-variant-calling-deepvariant` | `data/HG002_GRCh38_truth.vcf.gz` | OpenClaw |
| `bio-variant-calling-deepvariant` | `data/call_variants.tfrecord.gz` | OpenClaw |
| `bio-variant-calling-deepvariant` | `data/deepvariant_output.vcf.gz` | OpenClaw |
| `bio-variant-calling-deepvariant` | `data/examples.tfrecord.gz` | OpenClaw |
| `bio-variant-calling-deepvariant` | `data/exome.bam` | OpenClaw |
| `bio-variant-calling-deepvariant` | `data/exome_variants.vcf.gz` | OpenClaw |
| `bio-variant-calling-deepvariant` | `data/gvcf.tfrecord.gz` | OpenClaw |
| `bio-variant-calling-deepvariant` | `data/hifi_aligned.bam` | OpenClaw |
| `bio-variant-calling-deepvariant` | `data/hifi_variants.vcf.gz` | OpenClaw |
| `bio-variant-calling-deepvariant` | `data/ont_aligned.bam` | OpenClaw |
| `bio-variant-calling-deepvariant` | `data/ont_variants.vcf.gz` | OpenClaw |
| `bio-variant-calling-deepvariant` | `data/reference.fa` | OpenClaw |
| `bio-variant-calling-deepvariant` | `data/sample.bam` | OpenClaw |
| `bio-variant-calling-deepvariant` | `data/targets.bed` | OpenClaw |
| `bio-workflow-management-cwl-workflows` | `data/sample1_R1.fq.gz` | OpenClaw |
| `bio-workflow-management-cwl-workflows` | `data/sample1_R2.fq.gz` | OpenClaw |
| `bio-workflow-management-snakemake-workflows` | `data/all_samples.txt` | OpenClaw |
| `bio-workflow-management-snakemake-workflows` | `scripts/deseq2.R` | OpenClaw |
| `bio-workflow-management-wdl-workflows` | `data/sample1_R1.fq.gz` | OpenClaw |
| `bio-workflow-management-wdl-workflows` | `data/sample1_R2.fq.gz` | OpenClaw |
| `bio-workflow-management-wdl-workflows` | `data/sample2_R1.fq.gz` | OpenClaw |
| `bio-workflow-management-wdl-workflows` | `data/sample2_R2.fq.gz` | OpenClaw |
| `bioinformatics-singlecell` | `references/scvi_advanced.md` | OpenClaw |
| `biopython-advanced` | `scripts/codon_usage.py` | aipoch |
| `biopython-advanced` | `scripts/motif_stats.py` | aipoch |
| `biopython-advanced` | `scripts/restriction_sites.py` | aipoch |
| `biopython-entrez` | `scripts/pubmed_summaries.py` | aipoch |
| `biopython-phylo` | `data/input_tree.nwk` | aipoch |
| `biopython-phylo` | `scripts/phylo_task.py` | aipoch |
| `biopython-sequence-io` | `data/index.sqlite` | aipoch |
| `biopython-sequence-io` | `data/input.fasta` | aipoch |
| `biopython-sequence-io` | `data/output.gb` | aipoch |
| `biopython-sequence-io` | `scripts/sequence_io.py` | aipoch |
| `biopython-structure` | `data/1ubq.pdb` | aipoch |
| `biopython-structure` | `scripts/neighbor_search.py` | aipoch |
| `bmi-bsa-calculator` | `references/bsa_formulas_comparison.md` | aipoch |
| `bmi-bsa-calculator` | `references/chemotherapy_dosing.md` | aipoch |
| `bmi-bsa-calculator` | `references/ethnic_adjustments.md` | aipoch |
| `bmi-bsa-calculator` | `references/pediatric_norms.md` | aipoch |
| `boltzgen` | `../../docs/installation.md` | OpenClaw |
| `chai` | `../../docs/installation.md` | OpenClaw |
| `cibersort-immune-infiltration-analysis` | `data/cibersort_input.rds` | aipoch |
| `cibersort-immune-infiltration-analysis` | `data/cibersort_null_distribution.rds` | aipoch |
| `cibersort-immune-infiltration-analysis` | `data/cibersort_result.rds` | aipoch |
| `circos-plot-generator` | `data/cnv_track.txt` | aipoch |
| `circos-plot-generator` | `data/sample_variations.csv` | aipoch |
| `circos-plot-generator` | `data/snp_track.txt` | aipoch |
| `circos-plot-generator` | `data/sv_links.txt` | aipoch |
| `citation-network` | `data/citations.csv` | aipoch |
| `code-refactor-for-reproducibility` | `data/raw.csv` | aipoch |
| `code-refactor-for-reproducibility` | `references/environment-setup.md` | aipoch |
| `decision-curve-analysis` | `data/dca_model.rds` | aipoch |
| `decision-tree-analysis` | `data/decision_tree_model.rds` | aipoch |
| `decision-tree-analysis` | `data/decision_tree_predictions.csv` | aipoch |
| `deg-screening-analysis` | `data/DEG_list.rda` | aipoch |
| `diffdock-molecular-docking` | `data/protein.pdb` | aipoch |
| `digital-twin-discharge-drafter` | `scripts/discharge_drafter.py` | aipoch |
| `equity-scorer` | `data/samples.vcf` | OpenClaw |
| `estimate-immune-score-analysis` | `data/estimate_input.gct` | aipoch |
| `estimate-immune-score-analysis` | `data/estimate_score.gct` | aipoch |
| `estimate-immune-score-analysis` | `data/expression_input.tsv` | aipoch |
| `external-model-validation` | `data/risk_data.rds` | aipoch |
| `fastqc-report-interpreter` | `scripts/fastqc_interpreter.py` | aipoch |
| `fda-guideline-search` | `../guidance.pdf` | aipoch |
| `file-search` | `scripts/test_skill.py` | aipoch |
| `gene-protein-expression-matrix-normalization` | `data/normalized_matrix.rds` | aipoch |
| `glycoengineering` | `bin/webface2.cgi` | OpenClaw |
| `grant-proposal-assistant` | `references/budget_templates.xlsx` | aipoch |
| `graph-interpretation` | `scripts/graph_interpreter.py` | aipoch |
| `gsea` | `data/GSEA_list.rda` | aipoch |
| `gsva-analysis-and-visualization` | `data/GSVA_list.rda` | aipoch |
| `health-trend-analyzer` | `data/allergies.json` | OpenClaw |
| `health-trend-analyzer` | `data/cycle-tracker.json` | OpenClaw |
| `health-trend-analyzer` | `data/menopause-tracker.json` | OpenClaw |
| `health-trend-analyzer` | `data/pregnancy-tracker.json` | OpenClaw |
| `health-trend-analyzer` | `data/profile.json` | OpenClaw |
| `health-trend-analyzer` | `data/radiation-records.json` | OpenClaw |
| `hipaa-compliance-auditor` | `references/hipaa_safe_harbor_guide.pdf` | aipoch |
| `hmdb-database` | `data/hmdb_metabolites.xml` | aipoch |
| `hypogenic` | `data/my_task/config.yaml` | aipoch |
| `hypogenic` | `data/my_task_test.json` | aipoch |
| `hypogenic` | `data/my_task_train.json` | aipoch |
| `hypogenic` | `data/my_task_val.json` | aipoch |
| `imaging-data-commons` | `data/rider/rider_pilot/RIDER-1007893286/CT_1.3.6.1` | OpenClaw |
| `immune-pathway-analysis` | `data/immune_pathway_result.rds` | aipoch |
| `journal-cover-prompter` | `scripts/cover_prompter.py` | aipoch |
| `lab-inventory-predictor` | `.openclaw/workspace/data/lab-inventory.json` | aipoch |
| `lab-result-interpretation` | `references/test_metadata.json` | aipoch |
| `linkedin-optimizer` | `references/headline-templates.md` | aipoch |
| `linkedin-optimizer` | `references/keywords-by-specialty.json` | aipoch |
| `linkedin-optimizer` | `references/linkedin-examples.md` | aipoch |
| `linkedin-optimizer` | `scripts/linkedin_optimizer.py` | aipoch |
| `lit-sync` | `references/fulltext_retrieval.json` | Aperivue |
| `lit-sync` | `references/zotero_collection.json` | Aperivue |
| `lncrna-regulatory-network-construction-analysis` | `data/lncrna_network.rda` | aipoch |
| `manage-project` | `scripts/init_project.py` | Aperivue |
| `manage-project` | `scripts/migrate_project_to_ssot.py` | Aperivue |
| `manage-project` | `scripts/validate_project_contract.py` | Aperivue |
| `manage-refs` | `scripts/verify_package_integrity.py` | Aperivue |
| `mindmap` | `assets/local-mindmap/index.html` | aipoch |
| `model-calibration-curve` | `data/calibration_data.qs` | aipoch |
| `multi-search-engine` | `references/advanced-search.md` | OpenClaw |
| `networkx` | `examples/index.html` | OpenClaw |
| `neuropixels-analysis` | `bin/.lf.bin` | aipoch |
| `note-summarizer` | `examples/example.json` | aipoch |
| `open-access-scout` | `scripts/oa_scout.py` | aipoch |
| `orchestrate` | `references/zotero_collection.json` | Aperivue |
| `patent-claim-mapper` | `scripts/claim_mapper.py` | aipoch |
| `patent-landscape` | `references/ipc-classifications.md` | aipoch |
| `patent-landscape` | `references/patent-search-strategies.md` | aipoch |
| `patent-landscape` | `scripts/patent_landscape.py` | aipoch |
| `patient-consent-simplifier` | `scripts/consent_simplifier.py` | aipoch |
| `pdf-processing-pro` | `scripts/extract_tables.py` | OpenClaw |
| `pdf-processing-pro` | `scripts/merge_pdfs.py` | OpenClaw |
| `pdf-processing-pro` | `scripts/split_pdf.py` | OpenClaw |
| `pdf-processing-pro` | `scripts/validate_form.py` | OpenClaw |
| `pdf-processing-pro` | `scripts/validate_pdf.py` | OpenClaw |
| `personal-statement` | `references/personal-statement-examples.md` | aipoch |
| `ppi-network-analysis` | `data/ppi_result.rds` | aipoch |
| `ppt-master` | `../../docs/templates-architecture.md` | aipoch |
| `ppt-master` | `templates/design_spec.md` | aipoch |
| `preprocess-imaging` | `../plans.json` | Aperivue |
| `present-paper` | `../patched.pptx` | Aperivue |
| `present-paper` | `make-figures/references/design_principles.md` | Aperivue |
| `prior-auth-letter-drafter` | `references/letter_template.docx` | aipoch |
| `proteinmpnn` | `../../docs/installation.md` | OpenClaw |
| `publish-skill` | `scripts/validate_skills.sh` | Aperivue |
| `radiology-image-quiz` | `scripts/radiology_quiz.py` | aipoch |
| `research-grants` | `references/budget_preparation.md` | aipoch |
| `research-grants` | `references/resubmission_strategies.md` | aipoch |
| `research-grants` | `references/review_criteria.md` | aipoch |
| `research-grants` | `references/team_building.md` | aipoch |
| `research-grants` | `references/timeline_planning.md` | aipoch |
| `research-grants` | `scripts/budget_calculator.py` | aipoch |
| `research-grants` | `scripts/deadline_tracker.py` | aipoch |
| `rf-model-importance-analysis` | `data/rf_result.rds` | aipoch |
| `rfdiffusion` | `../../docs/installation.md` | OpenClaw |
| `sample-group-sankey-plot` | `data/session_info.txt` | aipoch |
| `schedule-management` | `data/notified.log` | aipoch |
| `scientific-slides` | `../document-skills/pptx/scripts/thumbnail.py` | OpenClaw |
| `scikit-learn` | `examples/index.html` | OpenClaw |
| `search-lit` | `references/zotero_collection.json` | Aperivue |
| `self-review` | `scripts/check_domain_probe_sync.py` | Aperivue |
| `shift-handover-summarizer` | `data/shift_records.json` | aipoch |
| `spatial-transcriptomics-mapper` | `scripts/generate_test_data.py` | aipoch |
| `ssgsea-immune-infiltration-analysis` | `data/ssgsea_list.rds` | aipoch |
| `svm-model-importance-analysis` | `data/svm_result.rds` | aipoch |
| `symptom-checker-triage` | `references/red_flags.md` | aipoch |
| `sync-submission` | `path/to/medsci-skills/scripts/verify_package_integrity.py` | Aperivue |
| `sync-submission` | `scripts/verify_package_integrity.py` | Aperivue |
| `systematic-review-screener` | `references/prisma_2020_checklist.pdf` | aipoch |
| `time-dependent-roc` | `data/time_roc_points.csv` | aipoch |
| `time-dependent-roc` | `data/time_roc_points.txt` | aipoch |
| `tone-adjuster` | `scripts/tone_adjuster.py` | aipoch |
| `tooluniverse-gene-enrichment` | `references/cross_validation.md` | OpenClaw |
| `tooluniverse-gene-enrichment` | `references/id_conversion.md` | OpenClaw |
| `tooluniverse-gene-enrichment` | `references/multiple_testing.md` | OpenClaw |
| `tooluniverse-gene-enrichment` | `references/organism_support.md` | OpenClaw |
| `tooluniverse-gene-enrichment` | `scripts/compare_enrichment_sources.py` | OpenClaw |
| `tooluniverse-gene-enrichment` | `scripts/filter_by_gene_set_size.py` | OpenClaw |
| `torch-geometric` | `references/api_patterns.md` | OpenClaw |
| `torch-geometric` | `references/layer_capabilities.md` | OpenClaw |
| `torch_geometric` | `references/api_patterns.md` | OpenClaw |
| `torch_geometric` | `references/layer_capabilities.md` | OpenClaw |
| `umap-tsne-analysis` | `data/analysis_data.rda` | aipoch |
| `umap-tsne-analysis` | `data/session_info.txt` | aipoch |
| `variant-interpretation-acmg/bioSkills/deepvariant` | `data/HG002_GRCh38_truth.vcf.gz` | OpenClaw |
| `variant-interpretation-acmg/bioSkills/deepvariant` | `data/call_variants.tfrecord.gz` | OpenClaw |
| `variant-interpretation-acmg/bioSkills/deepvariant` | `data/deepvariant_output.vcf.gz` | OpenClaw |
| `variant-interpretation-acmg/bioSkills/deepvariant` | `data/examples.tfrecord.gz` | OpenClaw |
| `variant-interpretation-acmg/bioSkills/deepvariant` | `data/exome.bam` | OpenClaw |
| `variant-interpretation-acmg/bioSkills/deepvariant` | `data/exome_variants.vcf.gz` | OpenClaw |
| `variant-interpretation-acmg/bioSkills/deepvariant` | `data/gvcf.tfrecord.gz` | OpenClaw |
| `variant-interpretation-acmg/bioSkills/deepvariant` | `data/hifi_aligned.bam` | OpenClaw |
| `variant-interpretation-acmg/bioSkills/deepvariant` | `data/hifi_variants.vcf.gz` | OpenClaw |
| `variant-interpretation-acmg/bioSkills/deepvariant` | `data/ont_aligned.bam` | OpenClaw |
| `variant-interpretation-acmg/bioSkills/deepvariant` | `data/ont_variants.vcf.gz` | OpenClaw |
| `variant-interpretation-acmg/bioSkills/deepvariant` | `data/reference.fa` | OpenClaw |
| `variant-interpretation-acmg/bioSkills/deepvariant` | `data/sample.bam` | OpenClaw |
| `variant-interpretation-acmg/bioSkills/deepvariant` | `data/targets.bed` | OpenClaw |
| `verify-refs` | `references/library.bib` | Aperivue |
| `verify-refs` | `references/verified_references.tsv` | Aperivue |
| `verify-refs` | `scripts/validate_project_contract.py` | Aperivue |
| `volcano-plot-labeler` | `data/deseq2_results.csv` | aipoch |
| `wellally-tech` | `data/fitness/activities.json` | OpenClaw |
| `wellally-tech` | `data/fitness/heart-rate.json` | OpenClaw |
| `wellally-tech` | `data/fitness/recovery.json` | OpenClaw |
| `wellally-tech` | `data/profile.json` | OpenClaw |
| `wellally-tech` | `data/sleep/sleep-records.json` | OpenClaw |
| `wellally-tech` | `scripts/import_apple_health.py` | OpenClaw |
| `wellally-tech` | `scripts/import_fitbit.py` | OpenClaw |
| `wellally-tech` | `scripts/import_generic.py` | OpenClaw |
| `wellally-tech` | `scripts/import_oura.py` | OpenClaw |
| `western-blot-quantifier` | `data/wb_gel.png` | aipoch |
| `wgcna-analysis` | `data/analysis_objects.rds` | aipoch |
| `wgcna-analysis` | `data/net.rds` | aipoch |
| `wgcna-analysis` | `references/diagnosis-report.md` | aipoch |
| `zarr-python` | `data/hierarchy.zarr` | OpenClaw |
| `zarr-python` | `data/my_array.zarr` | OpenClaw |
| `zinc-database` | `../catitems.txt` | aipoch |
| `zinc-database` | `../smiles.txt` | aipoch |
| `zinc-database` | `../substance/random.txt` | aipoch |
| `zinc-database` | `../substances.txt` | aipoch |
