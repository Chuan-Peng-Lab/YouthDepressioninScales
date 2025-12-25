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
data_file = "Complains_output_non_depression.xlsx"

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
save_path = "processed_result_非抑郁_症状文本分析.xlsx"
result_df.to_excel(save_path, index=False)
print(f"✅ 结果已保存：{save_path}")


# ==========================
# 6. HanLP 词性标注 + POS Bigram
# （基于 processed_result_症状文本分析.xlsx）
# ==========================

import pandas as pd
import ast
import hanlp

print("\n===== 开始进行 HanLP 词性标注（POS） =====")

# ==========================
# 1️⃣ 读取已保存的分词结果文件
# ==========================
input_file = "processed_result_非抑郁_症状文本分析.xlsx"
result_df = pd.read_excel(input_file)

print(f"✅ 读取文件成功，共 {len(result_df)} 条文本")

# ==========================
# 2️⃣ 加载 HanLP 词性标注模型
# ==========================
pos_tagger = hanlp.load(hanlp.pretrained.pos.CTB5_POS_RNN)

# ==========================
# 3️⃣ POS 标注 + POS Bigram
# ==========================
pos_results = []        # [(词, 词性), ...]
pos_bigram_results = [] # [词性_词性, ...]

for tokens in result_df["processed_tokens"]:

    # Excel 里是字符串形式的 list，需要转回 list
    if isinstance(tokens, str):
        try:
            tokens = ast.literal_eval(tokens)
        except:
            tokens = []

    if not tokens:
        pos_results.append([])
        pos_bigram_results.append([])
        continue

    # HanLP 词性标注
    pos_tags = pos_tagger(tokens)

    # 词 + 词性
    word_pos = list(zip(tokens, pos_tags))
    pos_results.append(word_pos)

    # POS Bigram（例如：n_v, a_n）
    pos_bigrams = [
        f"{pos_tags[i]}_{pos_tags[i+1]}"
        for i in range(len(pos_tags) - 1)
    ]
    pos_bigram_results.append(pos_bigrams)

# ==========================
# 4️⃣ 写回 DataFrame
# ==========================
result_df["pos_tags"] = pos_results
result_df["pos_bigrams"] = pos_bigram_results

print("✅ POS 标注完成")

# ==========================
# 5️⃣ 导出，方便人工查看
# ==========================
def list_to_str(x):
    if isinstance(x, list):
        return " | ".join(map(str, x))
    return ""

export_df = result_df.copy()
export_df["processed_tokens"] = export_df["processed_tokens"].apply(list_to_str)
export_df["pos_tags"] = export_df["pos_tags"].apply(list_to_str)
export_df["pos_bigrams"] = export_df["pos_bigrams"].apply(list_to_str)

output_file = "POS_Bigram_非抑郁_结果查看.xlsx"
export_df.to_excel(output_file, index=False)

print(f"📘 POS + POS Bigram 结果已保存：{output_file}")



# ==========================
# 7. HanLP 命名实体识别（NER）
# （基于 processed_result_症状文本分析.xlsx）
# ==========================

import pandas as pd
import ast
import hanlp

print("\n===== 开始进行 HanLP 命名实体识别（NER） =====")

# ==========================
# 1️⃣ 读取已处理好的分词结果文件
# ==========================
input_file = "processed_result_非抑郁_症状文本分析.xlsx"
result_df = pd.read_excel(input_file)

print(f"✅ 读取文件成功，共 {len(result_df)} 条文本")

# ==========================
# 2️⃣ 加载 HanLP NER 模型（官方通用模型）
# ==========================
ner_tagger = hanlp.load(hanlp.pretrained.ner.MSRA_NER_BERT_BASE_ZH)

# ==========================
# 3️⃣ 对每条文本做 NER
# ==========================
ner_results = []   # 每条文本的实体结果

for tokens in result_df["processed_tokens"]:

    # Excel 里的 list 是字符串形式
    if isinstance(tokens, str):
        try:
            tokens = ast.literal_eval(tokens)
        except:
            tokens = []

    if not tokens:
        ner_results.append([])
        continue

    # HanLP NER（输入 token list）
    entities = ner_tagger(tokens)

    """
    entities 格式示例：
    [
      ('学校', 'LOCATION'),
      ('母亲', 'PERSON'),
      ('半年', 'TIME')
    ]
    """
    ner_results.append(entities)

# ==========================
# 4️⃣ 写回 DataFrame
# ==========================
result_df["named_entities"] = ner_results

print("✅ NER 识别完成")

# ==========================
# 5️⃣ 导出，方便人工查看
# ==========================
def list_to_str(x):
    if isinstance(x, list):
        return " | ".join(map(str, x))
    return ""

export_df = result_df.copy()
export_df["processed_tokens"] = export_df["processed_tokens"].apply(list_to_str)
export_df["named_entities"] = export_df["named_entities"].apply(list_to_str)

output_file = "NER_非抑郁_结果查看.xlsx"
export_df.to_excel(output_file, index=False)

print(f"📘 NER 结果已保存：{output_file}")


# ==========================
# 统计实体频次
# ==========================

import pandas as pd
import re
from collections import Counter

# 1) 只读 named_entities 这一列（更快）
input_file = "NER_非抑郁_结果查看.xlsx"
df = pd.read_excel(input_file, usecols=["named_entities"])

# 2) 正则：抓取 ('协和医院', 'NT', 5, 6) 的前两项
# 兼容单引号/双引号：('xxx', 'NT'...) 或 ("xxx","NT"...)
pattern = re.compile(r"\(\s*['\"]([^'\"]+)['\"]\s*,\s*['\"]([^'\"]+)['\"]")

counter = Counter()

total = len(df)
for i, cell in enumerate(df["named_entities"].fillna("").astype(str), start=1):
    if i % 200 == 0:
        print(f"⏳ 正在处理 {i}/{total} 行...")

    # 从字符串中直接提取所有 (实体名, 实体类型)
    matches = pattern.findall(cell)
    if matches:
        counter.update(matches)

# 3) 转成 DataFrame 并排序
entity_df = pd.DataFrame(
    [(ent, etype, freq) for (ent, etype), freq in counter.items()],
    columns=["实体", "实体类型", "出现次数"]
).sort_values(by="出现次数", ascending=False)

# 4) 导出
output_file = "NER_非抑郁_实体频次统计.xlsx"
entity_df.to_excel(output_file, index=False)

print(f"✅ 完成：共 {len(entity_df)} 个唯一实体-类型组合")
print(f"📄 已导出：{output_file}")

entity_df.groupby("实体类型")["出现次数"].sum().sort_values(ascending=False)


# LDA
import pandas as pd
import ast
from gensim import corpora
from gensim.models import LdaModel, CoherenceModel

# 从已保存的分词结果读取
lda_df = pd.read_excel("processed_result_非抑郁_症状文本分析.xlsx")

# processed_tokens → list
def parse_list(x):
    if isinstance(x, list):
        return x
    if isinstance(x, str):
        try:
            return ast.literal_eval(x)
        except:
            return []
    return []

lda_df["processed_tokens"] = lda_df["processed_tokens"].apply(parse_list)
lda_df["bigrams"] = lda_df["bigrams"].apply(parse_list)


print("\n===== LDA：单词版（baseline）=====")

documents = lda_df["processed_tokens"].tolist()

dictionary = corpora.Dictionary(documents)
corpus = [dictionary.doc2bow(doc) for doc in documents]

topics_range = range(2, 10)
coherence_values = []

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
        processes=1
    )
    coherence_values.append(cm.get_coherence())

best_k = list(topics_range)[coherence_values.index(max(coherence_values))]
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

print("\n===== LDA：Bigram 版（症状增强）=====")

documents_bg = []

for bigrams in lda_df["bigrams"]:
    # bigrams = [('学校','情绪'), ('注意力','不集中'), ...]
    bigram_tokens = [f"{a}_{b}" for a, b in bigrams]
    documents_bg.append(bigram_tokens)

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

best_k_bg = list(topics_range)[coherence_values_bg.index(max(coherence_values_bg))]
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




# ==========================
# 7. TF-IDF（挖掘不常见症状候选）
# ==========================

import pandas as pd
import ast
from sklearn.feature_extraction.text import TfidfVectorizer

# 1. 读取你已经处理好的结果文件
input_file = "processed_result_非抑郁_症状文本分析.xlsx"
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

output_file = "TFIDF_非抑郁_top200_候选症状.xlsx"
output_df.to_excel(output_file, index=False)

print(f"🔥 TF-IDF 完成，已导出：{output_file}")

# ==========================
# 7. Bigram TF-IDF（挖掘不常见症状候选）
# ==========================

import pandas as pd
import ast
from sklearn.feature_extraction.text import TfidfVectorizer

# 1. 读取已处理结果
input_file = "processed_result_非抑郁_症状文本分析.xlsx"
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

output_file = "TFIDF_非抑郁_bigram_候选症状.xlsx"
output_df.to_excel(output_file, index=False)

print(f"🔥 Bigram TF-IDF 完成，已导出：{output_file}")
