
import re
import jieba
import pandas as pd
from nltk.util import ngrams
from collections import defaultdict


# ==========================
# 第1步：加载停用词
# ==========================
def load_stopwords(file_path):
    stopwords = set()
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            stopwords.add(line.strip())
    return stopwords


# 路径设置（你根据自己机器调整）
stopwords_file = "hit_stopwords.txt"
file_path = "medical_data.csv"

# 加载停用词 & 数据
stop_words = load_stopwords(stopwords_file)
df = pd.read_csv(file_path)
print(f"✅ 加载停用词 {len(stop_words)} 个，读取数据 {len(df)} 条。")



# ==========================
# 第2步：文本清洗与分词
# ==========================
def preprocess_text(text, stop_words):
    """去标点、分词、去停用词"""
    if pd.isna(text) or str(text).strip() == "":
        return []

    # ① 去标点符号（仅保留中文、英文、数字）
    text_no_punc = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s]', '', str(text))
    text_no_punc = re.sub(r'\s+', '', text_no_punc)

    # ② jieba分词
    tokens = jieba.lcut(text_no_punc, HMM=True)

    # ③ 去停用词 + 去掉单个字
    tokens_no_stop = [t for t in tokens if t not in stop_words and len(t) > 1]
    return tokens_no_stop


# ==========================
# 第3步：生成 n-grams（二元组、三元组）
# ==========================
def generate_ngrams(tokens, n=2):
    """生成n元组"""
    return list(ngrams(tokens, n)) if len(tokens) >= n else []


# ==========================
# 主循环：处理每条文本
# ==========================
result = defaultdict(dict)

for idx, row in df.iterrows():
    original = row["病历文本"]
    processed = preprocess_text(original, stop_words)
    bigrams = generate_ngrams(processed, n=2)
    trigrams = generate_ngrams(processed, n=3)

    result[idx] = {
        "original": original,
        "processed_tokens": processed,
        "bigrams": bigrams,
        "trigrams": trigrams
    }

print(f"\n✅ 全部处理完成，共处理 {len(result)} 条文本。")

# ==========================
# 输出第1条示例
# ==========================
first = result[0]
print("\n【第1条结果示例】")
print(f"原始文本：{first['original'][:80]}...")
print(f"分词结果：{first['processed_tokens'][:15]}")
print(f"二元组：{first['bigrams'][:5]}")
print(f"三元组：{first['trigrams'][:5]}")


# 第四步 输出结果文件
import pandas as pd
import os

file_path = "medical_data.csv"  # 确保路径存在
save_dir = os.path.dirname(file_path)
save_path = os.path.join(save_dir, "processed_result_症状文本分析.xlsx")

# 转为DataFrame
result_df = pd.DataFrame.from_dict(result, orient="index")

# 保存
try:
    with pd.ExcelWriter(save_path, engine="openpyxl") as writer:
        result_df.to_excel(writer, sheet_name="Processed_Data", index_label="序号")
    print(f"\n✅ Excel 文件已保存至：{save_path}")
    print(f"共保存 {len(result_df)} 条处理后的数据。")
except Exception as e:
    print("❌ 文件保存失败，请检查路径或权限。")
    print(e)


# 第五步 LDA
# LDA第一步预处理

import pandas as pd
import ast

# 1. 读取Excel文件（改成你自己的路径）
excel_file = "processed_result_症状文本分析.xlsx"  # 使用相对路径
df = pd.read_excel(excel_file, sheet_name="Processed_Data")  # 读取指定sheet的Excel文件

# 2. 提取并转换分词列
documents = df['processed_tokens'].tolist()  # 获取分词列的内容

# 如果是字符串 '[词1, 词2]'，转成list
for i in range(len(documents)):
    if isinstance(documents[i], str):  # 如果是字符串
        try:
            documents[i] = ast.literal_eval(documents[i])  # 转换为list
        except:
            documents[i] = []  # 如果转换失败，赋空列表
    elif not isinstance(documents[i], list):  # 如果不是列表
        documents[i] = []  # 赋空列表

print(f"✅ 成功载入 {len(documents)} 条文本样本。")
print("示例：", documents[0][:10])  # 打印第一条数据的前10个分词


from gensim import corpora

# 2. 构建词袋模型
dictionary = corpora.Dictionary(documents)  # 创建字典（词袋模型）
corpus = [dictionary.doc2bow(doc) for doc in documents]  # 将文档转换为词袋向量表示
print(f"✅ 词袋模型构建成功，词典大小：{len(dictionary)}")
# %%
from gensim.models import LdaModel
from gensim.models import CoherenceModel

# 3. 调整主题数、计算并输出困惑度及一致性指标
min_topics = 2
max_topics = 15
step_size = 1
topics_range = range(min_topics, max_topics + 1, step_size)
coherence_values = []
perplexity_values = []
for num_topics in topics_range:
    lda_model = LdaModel(corpus=corpus, id2word=dictionary, num_topics=num_topics, random_state=100, chunksize=100,
                         passes=10, alpha='auto', per_word_topics=True)
    # 计算困惑度
    perplexity = lda_model.log_perplexity(corpus)
    perplexity_values.append(perplexity)
    # 计算主题一致性
    coherence_model_lda = CoherenceModel(model=lda_model, texts=documents, dictionary=dictionary, coherence='c_v')
    coherence_lda = coherence_model_lda.get_coherence()
    coherence_values.append(coherence_lda)

# 输出每个主题数对应的困惑度和一致性
for idx, num_topics in enumerate(topics_range):
    print(f"主题数 {num_topics}: 困惑度 = {perplexity_values[idx]}, 一致性 = {coherence_values[idx]}")

import matplotlib.pyplot as plt



# 4. 绘制困惑度及一致性曲线，并输出最佳主题数

import matplotlib.pyplot as plt

# 设置显示中文
plt.rcParams['font.sans-serif'] = ['SimHei']  # 设置字体为 SimHei
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

# 绘制困惑度曲线
plt.figure(figsize=(12, 6))

# 绘制困惑度
plt.subplot(1, 2, 1)
plt.plot(topics_range, perplexity_values, marker='o')
plt.title('不同主题数下的困惑度')
plt.xlabel('主题数')
plt.xticks(rotation=45)
plt.ylabel('困惑度')

# 绘制一致性
plt.subplot(1, 2, 2)
plt.plot(topics_range, coherence_values, marker='o')
plt.title('不同主题数下的一致性')
plt.xlabel('主题数')
plt.xticks(rotation=45)
plt.ylabel('一致性')

# 调整图表间距
plt.tight_layout()

# 保存图表到文件
save_path = "lda_topic_evaluation.png"  # 可以自定义保存路径和文件名
plt.savefig(save_path)  # 保存为 PNG 文件

# 显示图表
plt.show()

# 输出最佳主题数（根据一致性选择）
best_num_topics = topics_range[coherence_values.index(max(coherence_values))]

print(f"✅ 最佳主题数为：{best_num_topics}")
print(f"✅ 图表已保存至：{save_path}")


# 第5步：输出最佳主题数的不同主题及前10个关键词
num_topics = best_num_topics  # 使用最佳主题数

# 重新训练LDA模型，使用最佳主题数
lda_model = LdaModel(corpus=corpus, id2word=dictionary, num_topics=num_topics, random_state=100, chunksize=100, passes=10, alpha='auto', per_word_topics=True)

print(f"✅ 输出 {num_topics} 个主题及每个主题的前10个关键词：")

# 输出每个主题的前10个关键词
for idx, topic in lda_model.print_topics(num_topics=num_topics, num_words=10):
    print(f"主题 {idx + 1}: {topic}")


