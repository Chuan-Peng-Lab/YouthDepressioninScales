# Medical Record Preprocessing, Denoising and Dataset Generation
# 病历预处理、文本去噪与研究数据集生成

## 1. Overview / 流程概述

This project implements a three-stage pipeline for medical record preprocessing, rule-based text denoising, and research dataset generation.

本项目分为三个阶段，完成病历预处理、规则化文本去噪及最终研究数据集生成。

### Workflow / 处理流程

**Stage 1: R Markdown – Preprocessing / 病历预处理**

- Import and standardize medical records and questionnaire data.
- Extract medical history and match medical records with questionnaires.
- Select eligible records and generate intermediate datasets.

读取并整理新旧病历及问卷数据，提取现病史，完成病历与问卷匹配及患者筛选，生成去噪前中间数据。

**Stage 2: Python – Rule-based Denoising / 规则化文本去噪**

- Remove predefined psychological assessment results, scale scores, medication records, and irrelevant text fragments.
- Record deletion details and generate denoising statistics.

使用预设规则清理心理测评结果、量表分数、用药记录及其他无关文本，并记录删除明细和统计结果。

**Stage 3: R Markdown – Final Dataset Generation / 最终研究数据生成**

- Import and verify denoised records.
- Classify diagnostic groups and generate questionnaire datasets.
- Calculate questionnaire scores and assign five-fold cross-validation groups.
- Generate demographic summaries.

回接并验证去噪结果，完成诊断分组、问卷计分、五折交叉验证划分及人口学统计，生成最终研究数据集。

## 2. Input Files / 输入文件

Place the following raw files in the `DATA/` directory.

原始数据文件放置于 `DATA/` 文件夹：

| File / 文件 | Description / 说明 |
|---|---|
| `Complains_YoungClients.xls` | Old-format medical records / 旧格式病历 |
| `心身医学科精神科.xls` | New-format medical records / 新格式病历 |
| `Rawdata1.xlsx` | Questionnaire data / 问卷数据 |

## 3. Output Files / 输出文件

### Stage 1: R Preprocessing / 第一阶段：R 病历预处理

Output directory: `OUTPUT/`

| File / 文件 | Description / 内容 |
|---|---|
| `Complains_clean_step1_to_step4.xlsx` | Preprocessed medical records, cleaning summaries, diagnosis statistics, selection summaries, and assessment cleaning audit. / 预处理后的病历、清洗统计、诊断统计、筛选统计及行内检查清理审计。 |
| `Pre_denoising_state.rds` | Intermediate R data containing medical records, questionnaire data, and preprocessing summaries. / 保存病历、问卷及预处理统计的中间数据。 |

Additional output:

- `data/Raw_output.xlsx` – Selected questionnaire records / 筛选后的问卷数据。

Main worksheets in `Complains_clean_step1_to_step4.xlsx`:

- `Summary`
- `Diagnosis_key`
- `Diagnosis_full`
- `Selection_summary`
- `Clean_data`
- `行内检查清理`

### Stage 2: Python Denoising / 第二阶段：Python 文本去噪

Output directory: `OUTPUT/`

| File / 文件 | Description / 内容 |
|---|---|
| `Complains_denoised.xlsx` | Denoised medical records, including original text, cleaned text, deletion counts, and audit information. / 包含去噪前后文本、删除数量及审计信息的病历数据。 |

Worksheets:

- `Clean_data` – Complete denoised medical records / 去噪后的完整病历。
- `规则命中` – Summary of matched deletion rules / 删除规则命中汇总。
- `删除明细` – Detailed deletion records with original positions and text context / 删除位置、内容及上下文明细。
- `统计` – Denoising statistics by rule / 按规则汇总的去噪统计。

### Stage 3: R Final Dataset Generation / 第三阶段：R 最终数据集生成

Output directory: `OUTPUT/`

| File / 文件 | Description / 内容 |
|---|---|
| `Complains_output_depression_pure.xlsx` | Pure depression medical records / 单纯抑郁组病历 |
| `Complains_output_non_depression.xlsx` | Non-depression medical records / 非抑郁组病历 |
| `Complains_output_depression_comorbid.xlsx` | Depression-containing non-pure medical records / 含抑郁但非单纯抑郁组病历 |
| `Questionnaire_With_Diagnosis_Label.xlsx` | Questionnaire data with diagnostic labels / 带诊断标签的问卷数据 |
| `Questionnaire_Depression_Pure.xlsx` | Questionnaire data for the pure depression group / 单纯抑郁组问卷数据 |
| `ML_dataset_full_5fold_pure_depression.xlsx` | Full eligible binary classification dataset with five-fold assignments and questionnaire scores / 符合条件的二分类数据，包含五折划分及量表得分 |
| `Demographic_summary_age_sex.xlsx` | Demographic summaries by sample group / 各样本组的人口学统计 |
| `Export_run_info.txt` | Random seed, input file MD5 checksums, and R session information / 随机种子、输入文件 MD5 校验值及 R 环境信息 |

## 4. Execution Order / 运行顺序

1. Run the first R Markdown preprocessing stage.
2. Copy `Complains_clean_step1_to_step4.xlsx` and `Pre_denoising_state.rds` from `OUTPUT/` to `DATA/`.
3. Run the Python denoising script.
4. Copy `Complains_denoised.xlsx` from `OUTPUT/` to `DATA/`.
5. Run the final R Markdown dataset generation stage.

运行顺序：

1. 运行 R Markdown 第一阶段，完成病历预处理。
2. 将 `OUTPUT/` 中的 `Complains_clean_step1_to_step4.xlsx` 和 `Pre_denoising_state.rds` 复制到 `DATA/`。
3. 运行 Python 去噪脚本。
4. 将 `OUTPUT/Complains_denoised.xlsx` 复制到 `DATA/`。
5. 运行 R Markdown 最终数据生成阶段。

## 5. Notes / 注意事项

Intermediate files must be transferred between stages as described above.

各阶段需要按照上述步骤手动传递中间文件。

Raw clinical records and patient-level datasets contain sensitive information and should not be committed to a public repository.

原始病历及包含患者信息的数据应妥善保存，不应上传至公开 GitHub 仓库。

## 6. Technologies / 使用技术

R, R Markdown, Python, pandas, openpyxl, tidyverse.