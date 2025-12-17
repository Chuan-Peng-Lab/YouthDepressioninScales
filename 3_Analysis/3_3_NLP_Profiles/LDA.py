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
data_file      = "Complains_output_depression_500.xlsx"

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
    3）去停用词
    """
    if pd.isna(text):
        return []

    text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', '', str(text))
    tokens = jieba.lcut(text)

    tokens = [
        t for t in tokens
        if t not in stop_words and len(t) > 1
    ]
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


# ======================================================
# 6A. LDA —— 单词版（baseline）
# ======================================================
print("\n===== LDA：单词版（baseline）=====")

documents = []
for x in result_df["processed_tokens"]:
    if isinstance(x, list):
        documents.append(x)
    elif isinstance(x, str):
        documents.append(ast.literal_eval(x))
    else:
        documents.append([])

dictionary = corpora.Dictionary(documents)
corpus = [dictionary.doc2bow(doc) for doc in documents]

coherence_values = []
topics_range = range(2, 10)

for k in topics_range:
    lda_tmp = LdaModel(
        corpus=corpus,
        id2word=dictionary,
        num_topics=k,
        passes=10,
        random_state=42
    )
    cm = CoherenceModel(
        model=lda_tmp,
        texts=documents,
        dictionary=dictionary,
        coherence='c_v',
        processes=1  # ⭐⭐⭐ 关键：禁用多进程
    )

    coherence_values.append(cm.get_coherence())

best_k = topics_range[coherence_values.index(max(coherence_values))]
print(f"✅ 最佳主题数（单词版）：{best_k}")

lda_model = LdaModel(
    corpus=corpus,
    id2word=dictionary,
    num_topics=best_k,
    passes=10,
    random_state=42
)

for i, t in lda_model.print_topics(num_words=10):
    print(f"主题 {i+1}: {t}")


# ======================================================
# 6B. LDA —— 单词 + bigram 版（症状增强）
# ======================================================
print("\n===== LDA：加入 bigram（症状增强版）=====")

documents_bg = []

for _, row in result_df.iterrows():

    tokens = row["processed_tokens"]
    if isinstance(tokens, str):
        tokens = ast.literal_eval(tokens)

    bigrams = row["bigrams"]
    if isinstance(bigrams, str):
        bigrams = ast.literal_eval(bigrams)

    bigram_tokens = [f"{a}_{b}" for a, b in bigrams]

    documents_bg.append(tokens + bigram_tokens)

dictionary_bg = corpora.Dictionary(documents_bg)
corpus_bg = [dictionary_bg.doc2bow(doc) for doc in documents_bg]

coherence_values_bg = []

for k in topics_range:
    lda_tmp = LdaModel(
        corpus=corpus_bg,
        id2word=dictionary_bg,
        num_topics=k,
        passes=10,
        random_state=42
    )
    cm = CoherenceModel(
        model=lda_tmp,
        texts=documents_bg,
        dictionary=dictionary_bg,
        coherence='c_v',
        processes=1
    )

    coherence_values_bg.append(cm.get_coherence())

best_k_bg = topics_range[coherence_values_bg.index(max(coherence_values_bg))]
print(f"✅ 最佳主题数（bigram版）：{best_k_bg}")

lda_model_bg = LdaModel(
    corpus=corpus_bg,
    id2word=dictionary_bg,
    num_topics=best_k_bg,
    passes=10,
    random_state=42
)

for i, t in lda_model_bg.print_topics(num_words=10):
    print(f"主题 {i+1}: {t}")
