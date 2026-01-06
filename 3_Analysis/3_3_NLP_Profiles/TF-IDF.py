# ==========================
# 0. 导入库
# ==========================
import re
import jieba
import pandas as pd
import ast
from nltk.util import ngrams
from collections import defaultdict
from gensim import corpora
from gensim.models import LdaModel, CoherenceModel


# ==========================
# 1. 加载停用词 & 症状词
# ==========================
def load_wordlist(file_path):
    words = set()
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            w = line.strip()
            if w:
                words.add(w)
    return words


stopwords_file = "hit_stopwords.txt"
symptom_file   = "symptom_keywords.txt"
data_file = "Complains_output_depression_related.xlsx"


stop_words = load_wordlist(stopwords_file)
symptom_keywords = load_wordlist(symptom_file)

print(f"✅ 停用词数量：{len(stop_words)}")
print(f"✅ 症状词数量：{len(symptom_keywords)}")


# ⭐ 核心：强制 jieba 把“症状短语”当成一个整体
for kw in symptom_keywords:
    jieba.add_word(kw)
    jieba.suggest_freq(kw, True)


# ==========================
# 2. 读取病历数据
# ==========================
df = pd.read_excel(data_file)
print(f"✅ 读取病历 {len(df)} 条")


# ==========================
# 3. 文本预处理函数
# ==========================
def preprocess_text(text):
    """
    功能：
    1）清洗符号
    2）jieba 分词（症状短语不被拆）
    3）症状词优先，其余再去停用词
    """
    if pd.isna(text):
        return []

    # 清洗非中文字符
    text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', '', str(text))

    # 分词
    raw_tokens = jieba.lcut(text)

    tokens = []
    for t in raw_tokens:
        # ⭐ 规则 1：如果是症状词，直接保留
        if t in symptom_keywords:
            tokens.append(t)

        # ⭐ 规则 2：否则，才判断是不是停用词
        elif t not in stop_words and len(t) > 1:
            tokens.append(t)

    return tokens



# ==========================
# 4. 主处理流程（生成 tokens + bigrams）
# ==========================
result = defaultdict(dict)

for idx, row in df.iterrows():
    raw_text = row["现病史"]

    tokens = preprocess_text(raw_text)
    bigrams = list(ngrams(tokens, 2))

    # ⭐ 症状命中：直接在原文中查短语（最稳）
    hits = [kw for kw in symptom_keywords if kw in str(raw_text)]

    result[idx] = {
        "原始文本": raw_text,
        "processed_tokens": tokens,
        "bigrams": bigrams,
        "症状命中": ",".join(hits)
    }

print("✅ 文本处理完成")


# ==========================
# 5. 保存处理结果
# ==========================
result_df = pd.DataFrame.from_dict(result, orient="index")
save_path = "processed_result_症状文本分析.xlsx"
result_df.to_excel(save_path, index=False)
print(f"✅ 结果已保存：{save_path}")

# ==========================
# TF-IDF（挖掘不常见症状候选）
# ==========================

import pandas as pd
import ast
from sklearn.feature_extraction.text import TfidfVectorizer

# 1. 读取你已经处理好的结果文件
input_file = "processed_result_症状文本分析.xlsx"
df = pd.read_excel(input_file)

# 2. processed_tokens：list -> 句子（空格分隔）
def tokens_to_text(x):
    if isinstance(x, str):
        try:
            tokens = ast.literal_eval(x)
            return " ".join(tokens)
        except:
            return ""
    elif isinstance(x, list):
        return " ".join(x)
    else:
        return ""

documents = df["processed_tokens"].apply(tokens_to_text).tolist()

print(f"✅ TF-IDF 输入文档数：{len(documents)}")

# 3. 构建 TF-IDF 向量器
vectorizer = TfidfVectorizer(
    min_df=3,        # 至少出现在 3 条病历中（防止纯噪声）
    max_df=0.6,      # 出现太频繁的词自动降权
    token_pattern=r"(?u)\b\w+\b"
)

tfidf_matrix = vectorizer.fit_transform(documents)
feature_names = vectorizer.get_feature_names_out()

# 4. 计算“全语料平均 TF-IDF”
avg_tfidf = tfidf_matrix.mean(axis=0).A1

tfidf_scores = list(zip(feature_names, avg_tfidf))

# 5. 按 TF-IDF 得分排序
tfidf_sorted = sorted(tfidf_scores, key=lambda x: x[1], reverse=True)

# 6. 导出前 N 个候选词（建议 200）
TOP_N = 200
top_words = tfidf_sorted[:TOP_N]

output_df = pd.DataFrame(top_words, columns=["候选词", "平均TF-IDF"])

output_file = "TFIDF_top200_候选症状.xlsx"
output_df.to_excel(output_file, index=False)

print(f"🔥 TF-IDF 完成，已导出：{output_file}")

# ==========================
# 7. Bigram TF-IDF（挖掘不常见症状候选）
# ==========================

import pandas as pd
import ast
from sklearn.feature_extraction.text import TfidfVectorizer

# 1. 读取已处理结果
input_file = "processed_result_症状文本分析.xlsx"
df = pd.read_excel(input_file)

# 2. processed_tokens → 文本
def tokens_to_text(x):
    if isinstance(x, str):
        try:
            tokens = ast.literal_eval(x)
            return " ".join(tokens)
        except:
            return ""
    elif isinstance(x, list):
        return " ".join(x)
    else:
        return ""

documents = df["processed_tokens"].apply(tokens_to_text).tolist()

print(f"✅ TF-IDF 输入文档数：{len(documents)}")

# 3. Bigram TF-IDF（⭐ 只改这里）
vectorizer = TfidfVectorizer(
    ngram_range=(2, 2),   # ⭐ 只输出二元短语
    min_df=3,
    max_df=0.6,
    token_pattern=r"(?u)\b\w+\b"
)

tfidf_matrix = vectorizer.fit_transform(documents)
feature_names = vectorizer.get_feature_names_out()

# 4. 平均 TF-IDF
avg_tfidf = tfidf_matrix.mean(axis=0).A1
tfidf_scores = list(zip(feature_names, avg_tfidf))

# 5. 排序
tfidf_sorted = sorted(tfidf_scores, key=lambda x: x[1], reverse=True)

# 6. 导出前 200 个
TOP_N = 200
output_df = pd.DataFrame(
    tfidf_sorted[:TOP_N],
    columns=["二元短语", "平均TF-IDF"]
)

output_file = "TFIDF_bigram_候选症状.xlsx"
output_df.to_excel(output_file, index=False)

print(f"🔥 Bigram TF-IDF 完成，已导出：{output_file}")
