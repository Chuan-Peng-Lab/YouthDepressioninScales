# About this folder

## Authors of this folder

* Haoyuan Wang
* Zhihao Ma
* Hu Chuan-Peng

## Environment and versions

* Python:

  * jieba: 0.42.1
  * pandas: 2.3.3
  * nltk: 3.9.2
  * gensim: 4.4.0

## Data

* Input: Complains\_output\_depression\_related.xlsx, 
  This file is generated during the empirical data analysis stage (3\_2\_Empirical\_Data\_Analysis/Preprocessing.Rmd).
  It contains patients’complaint records related to depression and cannot be shared publicly due to the hospital’s data privacy protection policy.
* Output:processed\_result\_症状文本分析.xlsx
  TFIDF\_bigram\_候选症状.xlsx

## Aims of this folder

* Using NLP to extract symptoms from patients record.



# Workflow Context



The overall analysis pipeline is divided into two main parts:

3\_2\_Empirical\_Data\_Analysis

Responsible for empirical data preprocessing.

The script Preprocessing.Rmd generates the cleaned and structured dataset

Complains\_output\_depression\_related.xlsx.

3\_3\_NLP\_Profiles

Uses the output from the empirical data analysis stage as input and performs NLP-based symptom extraction and profiling.

## Progress

\[x] Preprocessing xlxs file
\[x] Tried LDA

