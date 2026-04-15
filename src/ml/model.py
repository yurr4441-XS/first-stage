import re
import jieba
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold, cross_val_predict, cross_val_score
from sklearn.preprocessing import LabelEncoder
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.metrics import classification_report, confusion_matrix


class MLModel:
    def __init__(self, input_file: str):
        self.input_file = input_file
        self.stopwords = [
            "患者", "病人", "出现", "伴有", "给予", "进行",
            "服用", "明显", "一般", "情况", "1周", "数天",
            "无明显", "稍有", "考虑", "建议", "复查",
            "月", "年", "天", "近", "来", "个", "史", "否认",
            "伴", "无", "有", "稍", "较", "经", "患", "于", "双",
            "常有", " ", "等"
        ]
        self._init_jieba()

    def _init_jieba(self):
        custom_words = [
            "头晕", "纳眠差", "言语不清", "肢体乏力",
            "膝关节", "右侧肢体乏力", "突发抽搐"
        ]
        for word in custom_words:
            jieba.add_word(word)

    def chinese_tokenizer(self, text):
        return list(jieba.cut(text))

    def clean_text(self, text: str) -> str:
        text = str(text)
        text = re.sub(r"\d+年|\d+月|\d+天", "", text)
        text = re.sub(r"[，。、“”‘’：:；;！（）()\-,—]", " ", text)
        for w in ["CT", "检查", "提示", "手术史"]:
            text = text.replace(w, "")
        return text.strip()

    def load_data(self):
        df = pd.read_csv(self.input_file)

        df = df[["input_text", "label_coarse"]].dropna().copy()
        df["label_binary"] = df["label_coarse"].apply(
            lambda x: "脑系病" if x == "脑系病" else "非脑系病"
        )
        df["input_text"] = df["input_text"].apply(self.clean_text)

        X = df["input_text"].astype(str)
        y_text = df["label_binary"].astype(str)

        le = LabelEncoder()
        y = le.fit_transform(y_text)

        print("数据量：", len(df))
        print("类别分布：")
        print(y_text.value_counts())

        print("\n标签映射：")
        for i, cls in enumerate(le.classes_):
            print(f"{cls} -> {i}")

        return X, y, le

    def build_lr_pipeline(self):
        return Pipeline([
            (
                "tfidf",
                TfidfVectorizer(
                    tokenizer=self.chinese_tokenizer,
                    token_pattern=None,
                    ngram_range=(1, 2),
                    max_features=500,
                    min_df=2,
                    stop_words=self.stopwords
                )
            ),
            (
                "clf",
                LogisticRegression(
                    C=0.5,
                    class_weight="balanced",
                    max_iter=1000,
                    random_state=42
                )
            )
        ])

    def build_svm_pipeline(self):
        return Pipeline([
            ("tfidf", TfidfVectorizer(analyzer="char", ngram_range=(1, 2), min_df=1)),
            ("clf", LinearSVC(class_weight="balanced", random_state=42, C=2))
        ])

    def evaluate_model(self, name, pipeline, X, y, le, cv):
        acc_scores = cross_val_score(pipeline, X, y, cv=cv, scoring="accuracy")
        f1_scores = cross_val_score(pipeline, X, y, cv=cv, scoring="f1_macro")
        y_pred = cross_val_predict(pipeline, X, y, cv=cv)

        print(f"\n[{name}] 3折 accuracy: {acc_scores}")
        print(f"[{name}] 平均 accuracy: {acc_scores.mean():.4f}")
        print(f"[{name}] 3折 macro-f1: {f1_scores}")
        print(f"[{name}] 平均 macro-f1: {f1_scores.mean():.4f}")

        print(f"\n[{name}] classification report:")
        print(classification_report(y, y_pred, target_names=le.classes_))

        print(f"[{name}] confusion matrix:")
        print(confusion_matrix(y, y_pred))

        return {
            "name": name,
            "accuracy_mean": acc_scores.mean(),
            "f1_mean": f1_scores.mean()
        }

    def show_top_features(self, pipeline, X, y):
        pipeline.fit(X, y)

        vectorizer = pipeline.named_steps["tfidf"]
        clf = pipeline.named_steps["clf"]

        feature_names = np.array(vectorizer.get_feature_names_out())
        coefs = clf.coef_[0]

        top_pos_idx = np.argsort(coefs)[-15:][::-1]
        top_neg_idx = np.argsort(coefs)[:15]

        print("\n类别：脑系病")
        print("Top 15 特征：")
        for idx in top_pos_idx:
            print(f"{feature_names[idx]} -> {coefs[idx]:.4f}")

        print("\n类别：非脑系病")
        print("Top 15 特征：")
        for idx in top_neg_idx:
            print(f"{feature_names[idx]} -> {coefs[idx]:.4f}")

    def train(self):
        X, y, le = self.load_data()
        cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)

        lr_pipeline = self.build_lr_pipeline()
        svm_pipeline = self.build_svm_pipeline()

        print("\n===== 逻辑回归结果 =====")
        lr_result = self.evaluate_model("LogisticRegression", lr_pipeline, X, y, le, cv)

        print("\n===== LinearSVC结果 =====")
        svm_result = self.evaluate_model("LinearSVC", svm_pipeline, X, y, le, cv)

        print("\n===== 模型对比 =====")
        print(lr_result)
        print(svm_result)

        print("\n===== 逻辑回归特征解释 =====")
        self.show_top_features(lr_pipeline, X, y)

