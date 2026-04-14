import pandas as pd
import numpy as np
import os
import re
import jieba

from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.preprocessing import LabelEncoder
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

# ========== 1. 分词器 ==========
def chinese_tokenizer(text):
    return list(jieba.cut(text))

jieba.add_word("头晕")
jieba.add_word("纳眠差")
jieba.add_word("言语不清")
jieba.add_word("肢体乏力")
jieba.add_word("膝关节")
jieba.add_word("右侧肢体乏力")
jieba.add_word("突发抽搐")

# ========== 2. 路径 ==========
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
INPUT_FILE = os.path.join(PROCESSED_DIR, "cases_ml_final.csv")

# ========== 3. 读数据 ==========
df = pd.read_csv(INPUT_FILE)
df = df[["input_text", "label_coarse"]].dropna()

df["label_binary"] = df["label_coarse"].apply(
    lambda x: "脑系病" if x == "脑系病" else "非脑系病"
)

def clean_text(x):
    x = re.sub(r"\d+年|\d+月|\d+天", "", x)
    x = re.sub(r"[，。、“”‘’：:；;！（）()\-,—]", " ", x)
    for w in ["CT", "检查", "提示", "手术史"]:
        x = x.replace(w, "")
    return x

df["input_text"] = df["input_text"].astype(str).apply(clean_text)

stopwords = [
    "患者", "病人", "出现", "伴有", "给予", "进行", "服用",
    "明显", "一般", "情况", "1周", "数天", "无明显", "稍有",
    "考虑", "建议", "复查", "月", "年", "天", "近", "来", "个",
    "史", "否认", "伴", "无", "有", "稍", "较", "经", "患",
    "于", "双", "常有", "等", " "
]

X = df["input_text"]
y_text = df["label_binary"]

# ========== 4. 标签编码 ==========
le = LabelEncoder()
y = le.fit_transform(y_text)

print("标签映射：")
for i, cls in enumerate(le.classes_):
    print(f"{cls} -> {i}")

# ========== 5. CV ==========
cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)

# ========== 6. 最终主模型：LinearSVC ==========
# 注意：
# 这里我先沿用你当前表现更好的 char 方案
svm_pipeline = Pipeline([
    ("tfidf", TfidfVectorizer(analyzer="char", ngram_range=(1, 2), min_df=1)),
    ("clf", LinearSVC(class_weight="balanced", random_state=42, C=2))
])

# ========== 7. 交叉验证预测 ==========
pred = cross_val_predict(svm_pipeline, X, y, cv=cv)
scores = cross_val_predict(svm_pipeline, X, y, cv=cv, method="decision_function")

result_df = df.copy().reset_index(drop=True)
result_df["true_label"] = le.inverse_transform(y)
result_df["pred_label"] = le.inverse_transform(pred)
result_df["correct"] = (pred == y)
result_df["decision_score"] = scores
result_df["abs_margin"] = np.abs(scores)

print("\n========== 全部样本结果 ==========")
print(result_df[["true_label", "pred_label", "correct", "decision_score", "abs_margin"]])

# ========== 8. 错分样本 ==========
wrong_df = result_df[result_df["correct"] == False].copy()
wrong_df = wrong_df.sort_values("abs_margin", ascending=True)

print("\n========== 错分样本 ==========")
if len(wrong_df) == 0:
    print("没有错分样本")
else:
    for i, row in wrong_df.iterrows():
        print(f"\n--- 错分样本 {i} ---")
        print("真实标签:", row["true_label"])
        print("预测标签:", row["pred_label"])
        print("decision_score:", round(row["decision_score"], 4))
        print("abs_margin:", round(row["abs_margin"], 4))
        print("文本:", row["input_text"][:300])

# ========== 9. 最靠近边界的样本 ==========
boundary_df = result_df.sort_values("abs_margin", ascending=True).head(10)

print("\n========== 最靠近边界的10个样本 ==========")
for i, row in boundary_df.iterrows():
    print(f"\n--- 边界样本 {i} ---")
    print("真实标签:", row["true_label"])
    print("预测标签:", row["pred_label"])
    print("decision_score:", round(row["decision_score"], 4))
    print("abs_margin:", round(row["abs_margin"], 4))
    print("文本:", row["input_text"][:300])

# ========== 10. 导出 ==========
OUT_FILE = os.path.join(PROCESSED_DIR, "boundary_analysis_svc.csv")
result_df.to_csv(OUT_FILE, index=False, encoding="utf-8-sig")
print(f"\n已导出：{OUT_FILE}")