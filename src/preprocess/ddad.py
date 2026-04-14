import pandas as pd
import numpy as np
import os
import re
from sklearn.model_selection import StratifiedKFold, cross_val_predict, cross_val_score
from sklearn.preprocessing import LabelEncoder
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, f1_score
import jieba

def chinese_tokenizer(text):
    return list(jieba.cut(text))
jieba.add_word("头晕")
jieba.add_word("纳眠差")
jieba.add_word("言语不清")
jieba.add_word("肢体乏力")
jieba.add_word("膝关节")
jieba.add_word("右侧肢体乏力")
jieba.add_word("突发抽搐")

# ========== 1. 读取数据 ==========
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
INPUT_FILE = os.path.join(PROCESSED_DIR, "cases_ml_final.csv")
df = pd.read_csv(INPUT_FILE)

# 只保留建模需要的列，并去空值
df = df[["input_text", "label_coarse"]].dropna()
df["label_binary"] = df["label_coarse"].apply(
    lambda x: "脑系病" if x == "脑系病" else "非脑系病"
)
def clean_text(x):
    # 去时间
    x = re.sub(r'\d+年|\d+月|\d+天', '', x)
    x = re.sub(r"[，。、“”‘’：:；;！（）()\-,—]", " ", x)
    # 去检查类词
    for w in ["CT", "检查", "提示", "手术史"]:
        x = x.replace(w, "")
    return x
df['input_text']=df['input_text'].apply(clean_text)
# 文本和标签
X = df["input_text"].astype(str)
y_text = df["label_binary"].astype(str)
print("数据量：", len(df))
print("类别分布：")
print(y_text.value_counts())
stopwords=[
    "患者", "病人", "出现", "伴有", "给予", "进行",
    "服用", "明显", "一般", "情况", "1周", "数天",
    "无明显", "稍有", "考虑", "建议", "复查","月","年","天","近","来","个","史","否认","患者",
    "出现","伴","无","有","稍","较","一般","情况",'经','患','于','双','常有',' ','等'
]

# ========== 2. 标签编码 ==========
le = LabelEncoder()
y = le.fit_transform(y_text)
print("标签映射：")
for i, cls in enumerate(le.classes_):
    print(f"{cls} -> {i}")

# ========== 3. 分层交叉验证 ==========
cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)

# ========== 4. 模型1：Logistic Regression ==========
lr_pipeline = Pipeline([
    ("tfidf", TfidfVectorizer( tokenizer=chinese_tokenizer,token_pattern=None,ngram_range=(1,2),max_features=500,min_df=2,stop_words=stopwords)),
    ("clf", LogisticRegression(C=0.5,class_weight="balanced", max_iter=1000, random_state=42))
])

# accuracy
lr_acc_scores = cross_val_score(lr_pipeline, X, y, cv=cv, scoring="accuracy")
print("\n[LogisticRegression] 3折 accuracy:", lr_acc_scores)
print("平均 accuracy:", lr_acc_scores.mean())
# macro-f1
lr_f1_scores = cross_val_score(lr_pipeline, X, y, cv=cv, scoring="f1_macro")
print("[LogisticRegression] 3折 macro-f1:", lr_f1_scores)
print("平均 macro-f1:", lr_f1_scores.mean())
# 交叉验证预测结果
lr_pred = cross_val_predict(lr_pipeline, X, y, cv=cv)

print("\n[LogisticRegression] classification report:")
print(classification_report(y, lr_pred, target_names=le.classes_))

print("[LogisticRegression] confusion matrix:")
print(confusion_matrix(y, lr_pred))

# ========== 5. 模型2：LinearSVC ==========
svm_pipeline = Pipeline([
    ("tfidf", TfidfVectorizer(analyzer="char", ngram_range=(1, 2), min_df=1)),
    ("clf", LinearSVC(class_weight="balanced", random_state=42,C=2))
])

svm_acc_scores = cross_val_score(svm_pipeline, X, y, cv=cv, scoring="accuracy")
print("\n[LinearSVC] 3折 accuracy:", svm_acc_scores)
print("平均 accuracy:", svm_acc_scores.mean())

svm_f1_scores = cross_val_score(svm_pipeline, X, y, cv=cv, scoring="f1_macro")
print("[LinearSVC] 3折 macro-f1:", svm_f1_scores)
print("平均 macro-f1:", svm_f1_scores.mean())

svm_pred = cross_val_predict(svm_pipeline, X, y, cv=cv)

print("\n[LinearSVC] classification report:")
print(classification_report(y, svm_pred, target_names=le.classes_))

print("[LinearSVC] confusion matrix:")
print(confusion_matrix(y, svm_pred))
# ========== 6. 用全量数据拟合逻辑回归，查看每类高权重特征 ==========
lr_pipeline.fit(X, y)

vectorizer = lr_pipeline.named_steps["tfidf"]
clf = lr_pipeline.named_steps["clf"]

feature_names = np.array(vectorizer.get_feature_names_out())

coefs = clf.coef_[0]

# 更支持“脑系病”的特征（正方向）
top_pos_idx = np.argsort(coefs)[-15:][::-1]

print("\n类别：脑系病")
print("Top 15 特征：")
for idx in top_pos_idx:
    print(f"{feature_names[idx]} -> {coefs[idx]:.4f}")

# 更支持“非脑系病”的特征（负方向）
top_neg_idx = np.argsort(coefs)[:15]

print("\n类别：非脑系病")
print("Top 15 特征：")
for idx in top_neg_idx:
    print(f"{feature_names[idx]} -> {coefs[idx]:.4f}")